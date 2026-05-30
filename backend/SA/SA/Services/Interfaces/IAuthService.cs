using System.Security.Claims;
using SA.Models.Dto.Auth;

namespace SA.Services.Interfaces;

public interface IAuthService
{
    Task<AuthResponse> RegisterAsync(RegisterRequest request, CancellationToken cancellationToken = default);
    Task<AuthResponse> LoginAsync(LoginRequest request, CancellationToken cancellationToken = default);
    Task<AuthResponse> RefreshAsync(RefreshTokenRequest request, CancellationToken cancellationToken = default);
    Task LogoutAsync(ClaimsPrincipal principal, LogoutRequest? request, CancellationToken cancellationToken = default);
    Task<UserResponse> GetCurrentUserAsync(ClaimsPrincipal principal, CancellationToken cancellationToken = default);
}
