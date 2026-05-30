using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using SA.Infrastructure;
using SA.Models.Dto.Auth;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Auth;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class AuthService : IAuthService
{
    private readonly IUserRepository _users;
    private readonly PasswordHashingService _passwordHasher;
    private readonly JwtTokenService _tokenService;

    public AuthService(
        IUserRepository users,
        PasswordHashingService passwordHasher,
        JwtTokenService tokenService)
    {
        _users = users;
        _passwordHasher = passwordHasher;
        _tokenService = tokenService;
    }

    public async Task<AuthResponse> RegisterAsync(RegisterRequest request, CancellationToken cancellationToken = default)
    {
        var username = request.Username.Trim();
        var email = request.Email.Trim().ToLowerInvariant();

        if (await _users.ExistsByUsernameOrEmailAsync(username, email, cancellationToken: cancellationToken))
        {
            throw new ConflictException("Username or email is already registered.");
        }

        var user = new User
        {
            Username = username,
            Email = email,
            FullName = request.FullName.Trim(),
            Role = UserRole.User,
            PasswordHash = _passwordHasher.HashPassword(request.Password),
            IsActive = true,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _users.AddAsync(user, cancellationToken);
        return await IssueTokensAsync(user, "Registration successful.", cancellationToken);
    }

    public async Task<AuthResponse> LoginAsync(LoginRequest request, CancellationToken cancellationToken = default)
    {
        var user = await _users.GetByIdentifierAsync(request.Username, cancellationToken);

        if (user is null || !user.IsActive || !_passwordHasher.VerifyPassword(request.Password, user.PasswordHash))
        {
            throw new ApiException("Invalid username/email or password.", StatusCodes.Status401Unauthorized);
        }

        user.LastLoginAt = DateTime.UtcNow;
        return await IssueTokensAsync(user, "Login successful.", cancellationToken);
    }

    public async Task<AuthResponse> RefreshAsync(RefreshTokenRequest request, CancellationToken cancellationToken = default)
    {
        var refreshTokenHash = _tokenService.HashRefreshToken(request.RefreshToken);
        var user = await _users.GetByRefreshTokenHashAsync(refreshTokenHash, cancellationToken);

        if (user is null)
        {
            throw new ApiException("Invalid or expired refresh token.", StatusCodes.Status401Unauthorized);
        }

        return await IssueTokensAsync(user, "Token refreshed.", cancellationToken);
    }

    public async Task LogoutAsync(ClaimsPrincipal principal, LogoutRequest? request, CancellationToken cancellationToken = default)
    {
        var user = await FindCurrentUserAsync(principal, cancellationToken);

        if (user is null && !string.IsNullOrWhiteSpace(request?.RefreshToken))
        {
            var refreshTokenHash = _tokenService.HashRefreshToken(request.RefreshToken);
            user = await _users.GetByRefreshTokenHashAsync(refreshTokenHash, cancellationToken);
        }

        if (user is not null)
        {
            user.RefreshTokenHash = null;
            user.RefreshTokenExpiresAt = null;
            user.UpdatedAt = DateTime.UtcNow;
            await _users.SaveChangesAsync(cancellationToken);
        }
    }

    public async Task<UserResponse> GetCurrentUserAsync(ClaimsPrincipal principal, CancellationToken cancellationToken = default)
    {
        var user = await FindCurrentUserAsync(principal, cancellationToken);
        if (user is null || !user.IsActive)
        {
            throw new ApiException("Authentication is required.", StatusCodes.Status401Unauthorized);
        }

        return ServiceMapping.ToUserResponse(user);
    }

    private async Task<AuthResponse> IssueTokensAsync(User user, string message, CancellationToken cancellationToken)
    {
        var tokens = _tokenService.CreateTokenPair(user);

        user.RefreshTokenHash = _tokenService.HashRefreshToken(tokens.RefreshToken);
        user.RefreshTokenExpiresAt = tokens.RefreshTokenExpiresAt;
        user.UpdatedAt = DateTime.UtcNow;

        await _users.SaveChangesAsync(cancellationToken);

        return new AuthResponse
        {
            Success = true,
            Message = message,
            AccessToken = tokens.AccessToken,
            RefreshToken = tokens.RefreshToken,
            ExpiresAt = tokens.ExpiresAt,
            User = ServiceMapping.ToUserResponse(user)
        };
    }

    private async Task<User?> FindCurrentUserAsync(ClaimsPrincipal principal, CancellationToken cancellationToken)
    {
        var idValue = principal.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? principal.FindFirstValue(JwtRegisteredClaimNames.Sub);

        return Guid.TryParse(idValue, out var userId)
            ? await _users.GetByIdAsync(userId, cancellationToken)
            : null;
    }
}
