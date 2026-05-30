using System.ComponentModel.DataAnnotations;

namespace SA.Models.Dto.Settings;

public sealed class UserSettingsResponse
{
    public string FullName { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public string ThemeMode { get; set; } = "dark";
    public string StartPage { get; set; } = "/dashboard";
    public int ConfidenceThreshold { get; set; } = 80;
    public DateTime UpdatedAt { get; set; }
}

public sealed class UpdateUserSettingsRequest
{
    [Required]
    [MaxLength(120)]
    public string FullName { get; set; } = string.Empty;

    [Required]
    [EmailAddress]
    [MaxLength(255)]
    public string Email { get; set; } = string.Empty;

    [Required]
    [RegularExpression("^(light|dark)$", ErrorMessage = "ThemeMode must be light or dark.")]
    public string ThemeMode { get; set; } = "dark";

    [Required]
    [RegularExpression("^/(dashboard|upload|heatmap|ball-action|analytics|action-recognition|player-action-analytics|analytics-history)$", ErrorMessage = "StartPage is not supported.")]
    public string StartPage { get; set; } = "/dashboard";

    [Range(50, 99)]
    public int ConfidenceThreshold { get; set; } = 80;
}
