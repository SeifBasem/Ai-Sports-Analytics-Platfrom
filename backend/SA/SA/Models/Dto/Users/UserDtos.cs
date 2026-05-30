using System.ComponentModel.DataAnnotations;
using SA.Models.Dto.Common;

namespace SA.Models.Dto.Users;

public sealed class UserQueryRequest : PagedRequest
{
    public string? Search { get; set; }
    public string? Role { get; set; }
    public bool? IsActive { get; set; }
}

public sealed class UpdateUserStatusRequest
{
    public bool IsActive { get; set; }
}

public sealed class UpdateUserRoleRequest
{
    [Required]
    public string Role { get; set; } = string.Empty;
}

public sealed class UpdateUserProfileRequest
{
    [Required]
    [MaxLength(120)]
    public string FullName { get; set; } = string.Empty;

    [Required]
    [EmailAddress]
    [MaxLength(255)]
    public string Email { get; set; } = string.Empty;
}
