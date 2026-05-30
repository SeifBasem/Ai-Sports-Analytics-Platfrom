using SA.Models.Enums;

namespace SA.Models.Entities;

public class Report
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid CreatedByUserId { get; set; }
    public Guid? VideoId { get; set; }
    public Guid? ProcessingJobId { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public ReportType ReportType { get; set; }
    public ReportFormat Format { get; set; }
    public ReportStatus Status { get; set; } = ReportStatus.Draft;
    public string? FilePath { get; set; }
    public DateTime? GeneratedAt { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public User? CreatedByUser { get; set; }
    public Video? Video { get; set; }
    public ProcessingJob? ProcessingJob { get; set; }
}
