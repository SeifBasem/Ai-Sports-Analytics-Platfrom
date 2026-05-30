using SA.Models.Enums;

namespace SA.Models.Entities;

public class ProcessingJob
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid? ProjectId { get; set; }
    public Guid VideoId { get; set; }
    public Guid? RequestedByUserId { get; set; }
    public JobType JobType { get; set; }
    public JobStatus Status { get; set; } = JobStatus.Queued;
    public string? ModelName { get; set; }
    public string InputPath { get; set; } = string.Empty;
    public string? OutputPath { get; set; }
    public string? CsvDir { get; set; }
    public int ProgressPercent { get; set; } = 0;
    public int? FrameCount { get; set; }
    public int? ObjectCount { get; set; }
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public string? ErrorMessage { get; set; }
    public string? MetadataJson { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public Project? Project { get; set; }
    public Video? Video { get; set; }
    public User? RequestedByUser { get; set; }
    public ICollection<Detection> Detections { get; set; } = [];
    public ICollection<JobStatistic> Statistics { get; set; } = [];
    public ICollection<Report> Reports { get; set; } = [];
    public ICollection<AIStatistic> AIStatistics { get; set; } = [];
    public ICollection<AIResultFile> AIResultFiles { get; set; } = [];
    public ICollection<ActionPrediction> ActionPredictions { get; set; } = [];
    public ICollection<Heatmap> Heatmaps { get; set; } = [];
}
