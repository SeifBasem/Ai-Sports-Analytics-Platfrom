using System.ComponentModel.DataAnnotations;
using SA.Models.Dto.Common;

namespace SA.Models.Dto.Videos;

public sealed class VideoQueryRequest : PagedRequest
{
    public string? Search { get; set; }
    public string? Status { get; set; }
    public Guid? UploadedByUserId { get; set; }
}

public sealed class CreateVideoRecordRequest
{
    [Required]
    [MaxLength(180)]
    public string Title { get; set; } = string.Empty;

    [Required]
    [MaxLength(255)]
    public string OriginalFilename { get; set; } = string.Empty;

    [Required]
    [MaxLength(255)]
    public string StoredFilename { get; set; } = string.Empty;

    [Required]
    [MaxLength(100)]
    public string MimeType { get; set; } = string.Empty;

    [Required]
    [MaxLength(500)]
    public string StoragePath { get; set; } = string.Empty;

    [Range(0, long.MaxValue)]
    public long SizeBytes { get; set; }

    public int? DurationSeconds { get; set; }
}

public sealed class UpdateVideoRecordRequest
{
    [Required]
    [MaxLength(180)]
    public string Title { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? AnnotatedOutputPath { get; set; }

    public string? Status { get; set; }
    public string? ErrorMessage { get; set; }
}

public sealed class VideoResponse
{
    public Guid Id { get; set; }
    public Guid UploadedByUserId { get; set; }
    public string UploadedBy { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string OriginalFilename { get; set; } = string.Empty;
    public string StoredFilename { get; set; } = string.Empty;
    public string MimeType { get; set; } = string.Empty;
    public string StoragePath { get; set; } = string.Empty;
    public string? AnnotatedOutputPath { get; set; }
    public long SizeBytes { get; set; }
    public int? DurationSeconds { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? ErrorMessage { get; set; }
    public DateTime UploadedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
