using SA.Models.Enums;

namespace SA.Models.Entities;

public class Video
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid? ProjectId { get; set; }
    public Guid UploadedByUserId { get; set; }
    public string Title { get; set; } = string.Empty;
    public string OriginalFilename { get; set; } = string.Empty;
    public string StoredFilename { get; set; } = string.Empty;
    public string MimeType { get; set; } = string.Empty;
    public string StoragePath { get; set; } = string.Empty;
    public string? AnnotatedOutputPath { get; set; }
    public long SizeBytes { get; set; }
    public int? DurationSeconds { get; set; }
    public VideoStatus Status { get; set; } = VideoStatus.Uploaded;
    public string? ErrorMessage { get; set; }
    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public Project? Project { get; set; }
    public User? UploadedByUser { get; set; }
    public ICollection<ProcessingJob> ProcessingJobs { get; set; } = [];
    public ICollection<Detection> Detections { get; set; } = [];
    public ICollection<JobStatistic> Statistics { get; set; } = [];
    public ICollection<Report> Reports { get; set; } = [];
    public ICollection<AIStatistic> AIStatistics { get; set; } = [];
}
