namespace SA.Models.Entities;

public class AIResultFile
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProcessingJobId { get; set; }
    public string FileType { get; set; } = string.Empty;
    public string FileKey { get; set; } = string.Empty;
    public string StoragePath { get; set; } = string.Empty;
    public string? MimeType { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ProcessingJob? ProcessingJob { get; set; }
}
