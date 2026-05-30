namespace SA.Models.Entities;

public class Heatmap
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid? ProjectId { get; set; }
    public Guid ProcessingJobId { get; set; }
    public string TargetType { get; set; } = string.Empty;
    public string TargetId { get; set; } = string.Empty;
    public string ImagePath { get; set; } = string.Empty;
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public Project? Project { get; set; }
    public ProcessingJob? ProcessingJob { get; set; }
}
