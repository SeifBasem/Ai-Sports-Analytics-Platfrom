using System.ComponentModel.DataAnnotations;
using SA.Models.Dto.Common;

namespace SA.Models.Dto.Reports;

public sealed class ReportQueryRequest : PagedRequest
{
    public Guid? VideoId { get; set; }
    public Guid? ProcessingJobId { get; set; }
    public Guid? CreatedByUserId { get; set; }
    public string? ReportType { get; set; }
    public string? Status { get; set; }
}

public sealed class CreateReportRequest
{
    [Required]
    [MaxLength(180)]
    public string Title { get; set; } = string.Empty;

    public string? Description { get; set; }
    public Guid? VideoId { get; set; }
    public Guid? ProcessingJobId { get; set; }

    [Required]
    public string ReportType { get; set; } = string.Empty;

    [Required]
    public string Format { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? FilePath { get; set; }
}

public sealed class UpdateReportRequest
{
    [Required]
    [MaxLength(180)]
    public string Title { get; set; } = string.Empty;

    public string? Description { get; set; }
    public string? Status { get; set; }

    [MaxLength(500)]
    public string? FilePath { get; set; }
}

public sealed class ReportResponse
{
    public Guid Id { get; set; }
    public Guid CreatedByUserId { get; set; }
    public string CreatedBy { get; set; } = string.Empty;
    public Guid? VideoId { get; set; }
    public string? VideoTitle { get; set; }
    public Guid? ProcessingJobId { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string ReportType { get; set; } = string.Empty;
    public string Format { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string? FilePath { get; set; }
    public DateTime? GeneratedAt { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
