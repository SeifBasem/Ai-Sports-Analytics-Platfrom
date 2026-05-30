using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.IdentityModel.Tokens;
using SA.Infrastructure;
using SA.Models.Entities;

namespace SA.Services.Auth;

public sealed record TokenPair(
    string AccessToken,
    string RefreshToken,
    DateTime ExpiresAt,
    DateTime RefreshTokenExpiresAt
);

public sealed class JwtTokenService
{
    private readonly JwtSettings _settings;

    public JwtTokenService(JwtSettings settings)
    {
        _settings = settings;
    }

    public TokenPair CreateTokenPair(User user)
    {
        var now = DateTime.UtcNow;
        var expiresAt = now.AddMinutes(Math.Max(1, _settings.AccessTokenMinutes));
        var refreshTokenExpiresAt = now.AddDays(Math.Max(1, _settings.RefreshTokenDays));
        var signingKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_settings.Secret));
        var credentials = new SigningCredentials(signingKey, SecurityAlgorithms.HmacSha256);
        var role = user.Role.ToString();

        var claims = new List<Claim>
        {
            new(JwtRegisteredClaimNames.Sub, user.Id.ToString()),
            new(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
            new(AppClaimTypes.NameIdentifier, user.Id.ToString()),
            new(AppClaimTypes.UserId, user.Id.ToString()),
            new(AppClaimTypes.Name, user.Username),
            new(AppClaimTypes.Username, user.Username),
            new(AppClaimTypes.Email, user.Email),
            new(AppClaimTypes.Role, role),
            new("role", role),
            new(AppClaimTypes.FullName, user.FullName),
            new(AppClaimTypes.TokenUse, AppClaimTypes.AccessTokenUse)
        };

        var token = new JwtSecurityToken(
            issuer: _settings.Issuer,
            audience: _settings.Audience,
            claims: claims,
            notBefore: now,
            expires: expiresAt,
            signingCredentials: credentials
        );

        return new TokenPair(
            new JwtSecurityTokenHandler().WriteToken(token),
            GenerateRefreshToken(),
            expiresAt,
            refreshTokenExpiresAt
        );
    }

    public string HashRefreshToken(string refreshToken)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(refreshToken));
        return Convert.ToBase64String(hash);
    }

    private static string GenerateRefreshToken()
    {
        return Convert.ToBase64String(RandomNumberGenerator.GetBytes(64));
    }
}
