namespace SA.Models.Entities;

public class Detection
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProcessingJobId { get; set; }
    public Guid VideoId { get; set; }
    public int? FrameIndex { get; set; }
    public decimal? TimestampSeconds { get; set; }
    public string Label { get; set; } = string.Empty;
    public decimal Confidence { get; set; }
    public decimal X1 { get; set; }
    public decimal Y1 { get; set; }
    public decimal X2 { get; set; }
    public decimal Y2 { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ProcessingJob? ProcessingJob { get; set; }
    public Video? Video { get; set; }
}
