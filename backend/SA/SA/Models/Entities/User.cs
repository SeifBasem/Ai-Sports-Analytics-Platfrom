using SA.Models.Enums;

namespace SA.Models.Entities;

public class User
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Username { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public UserRole Role { get; set; } = UserRole.User;
    public bool IsActive { get; set; } = true;
    public string? RefreshTokenHash { get; set; }
    public DateTime? RefreshTokenExpiresAt { get; set; }
    public DateTime? LastLoginAt { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ICollection<Video> UploadedVideos { get; set; } = [];
    public ICollection<ProcessingJob> RequestedJobs { get; set; } = [];
    public ICollection<Report> CreatedReports { get; set; } = [];
    public ICollection<AuditLog> AuditLogs { get; set; } = [];
    public ICollection<Project> Projects { get; set; } = [];
    public ICollection<AIStatistic> AIStatistics { get; set; } = [];
    public UserSetting? Settings { get; set; }
}
