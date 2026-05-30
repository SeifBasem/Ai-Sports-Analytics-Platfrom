using System.ComponentModel.DataAnnotations;

namespace SA.Models.Dto.Heatmaps;

public sealed class IngestHeatmapRequest
{
    [Required]
    public Guid ProcessingJobId { get; set; }

    [Required]
    [MaxLength(40)]
    public string TargetType { get; set; } = string.Empty;

    [Required]
    [MaxLength(80)]
    public string TargetId { get; set; } = string.Empty;

    [Required]
    [MaxLength(500)]
    public string ImagePath { get; set; } = string.Empty;
}

public sealed class HeatmapResponse
{
    public Guid Id { get; set; }
    public Guid? ProjectId { get; set; }
    public Guid ProcessingJobId { get; set; }
    public string TargetType { get; set; } = string.Empty;
    public string TargetId { get; set; } = string.Empty;
    public string ImagePath { get; set; } = string.Empty;
    public DateTime GeneratedAt { get; set; }
}
