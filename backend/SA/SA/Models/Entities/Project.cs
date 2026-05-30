namespace SA.Models.Entities;

public class Project
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid OwnerUserId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public User? OwnerUser { get; set; }
    public ICollection<Video> Videos { get; set; } = [];
    public ICollection<ProcessingJob> ProcessingJobs { get; set; } = [];
    public ICollection<AIStatistic> AIStatistics { get; set; } = [];
    public ICollection<Heatmap> Heatmaps { get; set; } = [];
}
