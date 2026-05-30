using System.ComponentModel.DataAnnotations;
using SA.Models.Entities;

namespace SA.Models.Dto.Auth;

public sealed class LoginRequest
{
    [Required]
    [MaxLength(255)]
    public string Username { get; set; } = string.Empty;

    [Required]
    [MinLength(3)]
    [MaxLength(128)]
    public string Password { get; set; } = string.Empty;
}

public sealed class RegisterRequest
{
    [Required]
    [MinLength(3)]
    [MaxLength(50)]
    public string Username { get; set; } = string.Empty;

    [Required]
    [EmailAddress]
    [MaxLength(255)]
    public string Email { get; set; } = string.Empty;

    [Required]
    [MinLength(6)]
    [MaxLength(128)]
    public string Password { get; set; } = string.Empty;

    [Required]
    [MaxLength(120)]
    public string FullName { get; set; } = string.Empty;
}

public sealed class RefreshTokenRequest
{
    [Required]
    public string RefreshToken { get; set; } = string.Empty;
}

public sealed class LogoutRequest
{
    public string? RefreshToken { get; set; }
}

public sealed class AuthResponse
{
    public bool Success { get; set; } = true;
    public string Message { get; set; } = string.Empty;
    public string AccessToken { get; set; } = string.Empty;
    public string RefreshToken { get; set; } = string.Empty;
    public DateTime ExpiresAt { get; set; }
    public UserResponse User { get; set; } = new();
}

public sealed class UserResponse
{
    public Guid Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }

    public static UserResponse FromUser(User user)
    {
        return new UserResponse
        {
            Id = user.Id,
            Username = user.Username,
            Email = user.Email,
            FullName = user.FullName,
            Role = user.Role.ToString(),
            IsActive = user.IsActive,
            CreatedAt = user.CreatedAt
        };
    }
}

public sealed class ApiMessageResponse
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
}
