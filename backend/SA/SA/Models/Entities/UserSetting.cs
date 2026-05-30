namespace SA.Models.Entities;

public class UserSetting
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public string ThemeMode { get; set; } = "dark";
    public string StartPage { get; set; } = "/dashboard";
    public int ConfidenceThreshold { get; set; } = 80;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    public User User { get; set; } = null!;
}
