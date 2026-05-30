using System.ComponentModel.DataAnnotations;
using SA.Models.Dto.Common;

namespace SA.Models.Dto.Jobs;

public sealed class ProcessingJobQueryRequest : PagedRequest
{
    public Guid? VideoId { get; set; }
    public Guid? RequestedByUserId { get; set; }
    public string? JobType { get; set; }
    public string? Status { get; set; }
    public DateTime? CreatedFrom { get; set; }
    public DateTime? CreatedTo { get; set; }
}

public sealed class CreateProcessingJobRequest
{
    [Required]
    public Guid VideoId { get; set; }

    [Required]
    public string JobType { get; set; } = string.Empty;

    [MaxLength(120)]
    public string? ModelName { get; set; }

    [Required]
    [MaxLength(500)]
    public string InputPath { get; set; } = string.Empty;
}

public sealed class UpdateProcessingJobStatusRequest
{
    [Required]
    public string Status { get; set; } = string.Empty;

    [Range(0, 100)]
    public int? ProgressPercent { get; set; }

    public int? FrameCount { get; set; }
    public int? ObjectCount { get; set; }
    public string? OutputPath { get; set; }
    public string? ErrorMessage { get; set; }
}

public sealed class ProcessingJobResponse
{
    public Guid Id { get; set; }
    public Guid VideoId { get; set; }
    public string VideoTitle { get; set; } = string.Empty;
    public Guid? RequestedByUserId { get; set; }
    public string? RequestedBy { get; set; }
    public string JobType { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string? ModelName { get; set; }
    public string InputPath { get; set; } = string.Empty;
    public string? OutputPath { get; set; }
    public int ProgressPercent { get; set; }
    public int? FrameCount { get; set; }
    public int? ObjectCount { get; set; }
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public string? ErrorMessage { get; set; }
    public string? MetadataJson { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}

public sealed class CreateJobStatisticRequest
{
    [Required]
    [MaxLength(120)]
    public string ModuleName { get; set; } = string.Empty;

    [MaxLength(120)]
    public string? ModelName { get; set; }

    [Required]
    [MaxLength(80)]
    public string StatType { get; set; } = string.Empty;

    [Required]
    public string StatsJson { get; set; } = string.Empty;
}

public sealed class CreateJobStatisticsBatchRequest
{
    [Required]
    public List<CreateJobStatisticRequest> Statistics { get; set; } = [];
}

public sealed class JobStatisticQueryRequest : PagedRequest
{
    public Guid? ProcessingJobId { get; set; }
    public Guid? VideoId { get; set; }
    public string? ModuleName { get; set; }
    public string? StatType { get; set; }
}

public sealed class JobStatisticResponse
{
    public Guid Id { get; set; }
    public Guid ProcessingJobId { get; set; }
    public Guid VideoId { get; set; }
    public string ModuleName { get; set; } = string.Empty;
    public string? ModelName { get; set; }
    public string StatType { get; set; } = string.Empty;
    public string StatsJson { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}

public sealed class AiJobStatisticsIngestRequest
{
    [Required]
    public Guid JobId { get; set; }

    [MaxLength(180)]
    public string? ProjectName { get; set; }

    [Required]
    [MaxLength(255)]
    public string OriginalFilename { get; set; } = string.Empty;

    [MaxLength(180)]
    public string? Title { get; set; }

    [MaxLength(500)]
    public string? InputPath { get; set; }

    [MaxLength(500)]
    public string? OutputPath { get; set; }

    [MaxLength(500)]
    public string? CsvDir { get; set; }

    [MaxLength(30)]
    public string? JobType { get; set; }

    [MaxLength(20)]
    public string? Status { get; set; }

    [MaxLength(120)]
    public string? ModelName { get; set; }

    public int? FrameCount { get; set; }
    public int? ObjectCount { get; set; }
    public string? ErrorMessage { get; set; }

    [MaxLength(80)]
    public string? UploadBatchId { get; set; }

    [MaxLength(180)]
    public string? UploadBatchTitle { get; set; }

    [MaxLength(20)]
    public string? UploadBatchVideoCount { get; set; }

    [MaxLength(20)]
    public string? UploadBatchIndex { get; set; }

    [MaxLength(120)]
    public string? PlayerName { get; set; }

    public List<CreateJobStatisticRequest> Statistics { get; set; } = [];
    public List<AiResultFileIngestRequest> ResultFiles { get; set; } = [];
    public List<ActionPredictionIngestRequest> ActionPredictions { get; set; } = [];
}

public sealed class AiResultFileIngestRequest
{
    [Required]
    [MaxLength(80)]
    public string FileType { get; set; } = string.Empty;

    [Required]
    [MaxLength(120)]
    public string FileKey { get; set; } = string.Empty;

    [Required]
    [MaxLength(500)]
    public string StoragePath { get; set; } = string.Empty;

    [MaxLength(100)]
    public string? MimeType { get; set; }
}

public sealed class ActionPredictionIngestRequest
{
    [MaxLength(30)]
    public string GameTime { get; set; } = string.Empty;

    [Required]
    [MaxLength(80)]
    public string Label { get; set; } = string.Empty;

    [MaxLength(30)]
    public string? Team { get; set; }

    [MaxLength(80)]
    public string? Position { get; set; }

    public int? Half { get; set; }
    public decimal Confidence { get; set; }
    public int? Frame { get; set; }

    [MaxLength(120)]
    public string? ClassName { get; set; }

    public int Second { get; set; }
}
