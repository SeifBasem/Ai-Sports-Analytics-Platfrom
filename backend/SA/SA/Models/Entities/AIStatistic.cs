namespace SA.Models.Entities;

public class AIStatistic
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid? ProjectId { get; set; }
    public Guid ProcessingJobId { get; set; }
    public Guid VideoId { get; set; }
    public Guid? UserId { get; set; }
    public string ModelModule { get; set; } = string.Empty;
    public string StatGroup { get; set; } = string.Empty;
    public string StatKey { get; set; } = string.Empty;
    public string? StatValue { get; set; }
    public decimal? NumericValue { get; set; }
    public string? JsonValue { get; set; }
    public string? TeamId { get; set; }
    public string? PlayerId { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public Project? Project { get; set; }
    public ProcessingJob? ProcessingJob { get; set; }
    public Video? Video { get; set; }
    public User? User { get; set; }
}
