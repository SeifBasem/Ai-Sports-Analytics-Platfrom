namespace SA.Models.Entities;

public class JobStatistic
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProcessingJobId { get; set; }
    public Guid VideoId { get; set; }
    public string ModuleName { get; set; } = string.Empty;
    public string? ModelName { get; set; }
    public string StatType { get; set; } = string.Empty;
    public string StatsJson { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ProcessingJob? ProcessingJob { get; set; }
    public Video? Video { get; set; }
}
