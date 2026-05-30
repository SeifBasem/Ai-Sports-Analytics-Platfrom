using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Models.Entities;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class JobStatisticRepository : IJobStatisticRepository
{
    private readonly AppDbContext _db;

    public JobStatisticRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<JobStatistic?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return _db.JobStatistics
            .Include(s => s.ProcessingJob)
            .Include(s => s.Video)
            .FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
    }

    public Task<PagedResponse<JobStatistic>> SearchAsync(JobStatisticQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        var query = _db.JobStatistics
            .AsNoTracking()
            .Include(s => s.Video)
            .AsQueryable();

        if (!includeAllUsers)
        {
            query = query.Where(s => s.Video != null && s.Video.UploadedByUserId == currentUserId);
        }

        if (request.ProcessingJobId.HasValue)
        {
            query = query.Where(s => s.ProcessingJobId == request.ProcessingJobId.Value);
        }

        if (request.VideoId.HasValue)
        {
            query = query.Where(s => s.VideoId == request.VideoId.Value);
        }

        if (!string.IsNullOrWhiteSpace(request.ModuleName))
        {
            var moduleName = request.ModuleName.Trim().ToLowerInvariant();
            query = query.Where(s => s.ModuleName.ToLower() == moduleName);
        }

        if (!string.IsNullOrWhiteSpace(request.StatType))
        {
            var statType = request.StatType.Trim().ToLowerInvariant();
            query = query.Where(s => s.StatType.ToLower() == statType);
        }

        return query
            .OrderByDescending(s => s.CreatedAt)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public Task<int> CountAsync(CancellationToken cancellationToken = default)
    {
        return _db.JobStatistics.CountAsync(cancellationToken);
    }

    public async Task AddAsync(JobStatistic statistic, CancellationToken cancellationToken = default)
    {
        await _db.JobStatistics.AddAsync(statistic, cancellationToken);
    }

    public async Task AddRangeAsync(IEnumerable<JobStatistic> statistics, CancellationToken cancellationToken = default)
    {
        await _db.JobStatistics.AddRangeAsync(statistics, cancellationToken);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
