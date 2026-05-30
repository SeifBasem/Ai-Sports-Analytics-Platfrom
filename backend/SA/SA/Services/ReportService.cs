using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Reports;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class ReportService : IReportService
{
    private readonly IReportRepository _reports;
    private readonly IVideoRepository _videos;
    private readonly IProcessingJobRepository _jobs;

    public ReportService(IReportRepository reports, IVideoRepository videos, IProcessingJobRepository jobs)
    {
        _reports = reports;
        _videos = videos;
        _jobs = jobs;
    }

    public async Task<PagedResponse<ReportResponse>> GetReportsAsync(ReportQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var page = await _reports.SearchAsync(request, isAdmin, currentUserId, cancellationToken);
        return new PagedResponse<ReportResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToReportResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<ReportResponse> GetReportAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var report = await _reports.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Report was not found.");

        EnsureCanAccess(report, currentUserId, isAdmin);
        return ServiceMapping.ToReportResponse(report);
    }

    public async Task<ReportResponse> CreateReportAsync(CreateReportRequest request, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        if (!Enum.TryParse<ReportType>(request.ReportType, true, out var reportType))
        {
            throw new ValidationException("Invalid report type.");
        }

        if (!Enum.TryParse<ReportFormat>(request.Format, true, out var format))
        {
            throw new ValidationException("Invalid report format.");
        }

        if (request.VideoId.HasValue)
        {
            var video = await _videos.GetByIdAsync(request.VideoId.Value, cancellationToken)
                ?? throw new NotFoundException("Video was not found.");
            if (video.UploadedByUserId != currentUserId)
            {
                throw new ForbiddenException("You cannot create a report for another user's video.");
            }
        }

        if (request.ProcessingJobId.HasValue)
        {
            var job = await _jobs.GetByIdAsync(request.ProcessingJobId.Value, cancellationToken)
                ?? throw new NotFoundException("Processing job was not found.");
            if (job.Video?.UploadedByUserId != currentUserId && job.RequestedByUserId != currentUserId)
            {
                throw new ForbiddenException("You cannot create a report for another user's processing job.");
            }
        }

        var report = new Report
        {
            CreatedByUserId = currentUserId,
            VideoId = request.VideoId,
            ProcessingJobId = request.ProcessingJobId,
            Title = request.Title.Trim(),
            Description = request.Description,
            ReportType = reportType,
            Format = format,
            Status = string.IsNullOrWhiteSpace(request.FilePath) ? ReportStatus.Draft : ReportStatus.Ready,
            FilePath = request.FilePath,
            GeneratedAt = string.IsNullOrWhiteSpace(request.FilePath) ? null : DateTime.UtcNow,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _reports.AddAsync(report, cancellationToken);
        await _reports.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToReportResponse(report);
    }

    public async Task<ReportResponse> UpdateReportAsync(Guid id, UpdateReportRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var report = await _reports.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Report was not found.");

        EnsureCanAccess(report, currentUserId, isAdmin);

        if (!string.IsNullOrWhiteSpace(request.Status))
        {
            if (!Enum.TryParse<ReportStatus>(request.Status, true, out var status))
            {
                throw new ValidationException("Invalid report status.");
            }

            report.Status = status;
            if (status == ReportStatus.Ready)
            {
                report.GeneratedAt ??= DateTime.UtcNow;
            }
        }

        report.Title = request.Title.Trim();
        report.Description = request.Description;
        report.FilePath = request.FilePath;
        report.UpdatedAt = DateTime.UtcNow;

        await _reports.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToReportResponse(report);
    }

    public async Task DeleteReportAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var report = await _reports.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Report was not found.");

        EnsureCanAccess(report, currentUserId, isAdmin);
        _reports.Remove(report);
        await _reports.SaveChangesAsync(cancellationToken);
    }

    private static void EnsureCanAccess(Report report, Guid currentUserId, bool isAdmin)
    {
        if (!isAdmin && report.CreatedByUserId != currentUserId)
        {
            throw new ForbiddenException("You do not have access to this report.");
        }
    }
}
