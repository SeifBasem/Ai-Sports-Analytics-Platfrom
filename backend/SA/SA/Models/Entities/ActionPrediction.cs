namespace SA.Models.Entities;

public class ActionPrediction
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProcessingJobId { get; set; }
    public string GameTime { get; set; } = string.Empty;
    public string Label { get; set; } = string.Empty;
    public string? Team { get; set; }
    public string? Position { get; set; }
    public int? Half { get; set; }
    public decimal Confidence { get; set; }
    public int? Frame { get; set; }
    public string? ClassName { get; set; }
    public int Second { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ProcessingJob? ProcessingJob { get; set; }
}
