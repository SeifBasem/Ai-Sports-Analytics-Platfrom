using System.ComponentModel.DataAnnotations;
using SA.Models.Dto.Common;

namespace SA.Models.Dto.Detections;

public sealed class DetectionQueryRequest : PagedRequest
{
    public Guid? ProcessingJobId { get; set; }
    public Guid? VideoId { get; set; }
    public string? Label { get; set; }
}

public sealed class CreateDetectionRequest
{
    [Required]
    public Guid ProcessingJobId { get; set; }

    [Required]
    public Guid VideoId { get; set; }

    public int? FrameIndex { get; set; }
    public decimal? TimestampSeconds { get; set; }

    [Required]
    [MaxLength(100)]
    public string Label { get; set; } = string.Empty;

    [Range(0, 1)]
    public decimal Confidence { get; set; }

    public decimal X1 { get; set; }
    public decimal Y1 { get; set; }
    public decimal X2 { get; set; }
    public decimal Y2 { get; set; }
}

public sealed class CreateDetectionBatchRequest
{
    [Required]
    public List<CreateDetectionRequest> Detections { get; set; } = [];
}

public sealed class DetectionResponse
{
    public Guid Id { get; set; }
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
    public DateTime CreatedAt { get; set; }
}
