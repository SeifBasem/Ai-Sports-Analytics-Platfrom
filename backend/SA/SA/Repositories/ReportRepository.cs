using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Reports;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class ReportRepository : IReportRepository
{
    private readonly AppDbContext _db;

    public ReportRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<Report?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return _db.Reports
            .Include(r => r.CreatedByUser)
            .Include(r => r.Video)
            .Include(r => r.ProcessingJob)
            .FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
    }

    public Task<PagedResponse<Report>> SearchAsync(ReportQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        var query = _db.Reports
            .AsNoTracking()
            .Include(r => r.CreatedByUser)
            .Include(r => r.Video)
            .Include(r => r.ProcessingJob)
            .AsQueryable();

        if (!includeAllUsers)
        {
            query = query.Where(r => r.CreatedByUserId == currentUserId);
        }

        if (request.VideoId.HasValue)
        {
            query = query.Where(r => r.VideoId == request.VideoId.Value);
        }

        if (request.ProcessingJobId.HasValue)
        {
            query = query.Where(r => r.ProcessingJobId == request.ProcessingJobId.Value);
        }

        if (request.CreatedByUserId.HasValue)
        {
            query = query.Where(r => r.CreatedByUserId == request.CreatedByUserId.Value);
        }

        if (!string.IsNullOrWhiteSpace(request.ReportType) &&
            Enum.TryParse<ReportType>(request.ReportType, true, out var reportType))
        {
            query = query.Where(r => r.ReportType == reportType);
        }

        if (!string.IsNullOrWhiteSpace(request.Status) &&
            Enum.TryParse<ReportStatus>(request.Status, true, out var status))
        {
            query = query.Where(r => r.Status == status);
        }

        return query
            .OrderByDescending(r => r.CreatedAt)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public Task<int> CountAsync(CancellationToken cancellationToken = default)
    {
        return _db.Reports.CountAsync(cancellationToken);
    }

    public async Task AddAsync(Report report, CancellationToken cancellationToken = default)
    {
        await _db.Reports.AddAsync(report, cancellationToken);
    }

    public void Remove(Report report)
    {
        _db.Reports.Remove(report);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
