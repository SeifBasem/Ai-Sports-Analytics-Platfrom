using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class ProcessingJobRepository : IProcessingJobRepository
{
    private readonly AppDbContext _db;

    public ProcessingJobRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<ProcessingJob?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return _db.ProcessingJobs
            .Include(j => j.Video)
            .Include(j => j.RequestedByUser)
            .FirstOrDefaultAsync(j => j.Id == id, cancellationToken);
    }

    public Task<PagedResponse<ProcessingJob>> SearchAsync(ProcessingJobQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        var query = _db.ProcessingJobs
            .AsNoTracking()
            .Include(j => j.Video)
            .Include(j => j.RequestedByUser)
            .AsQueryable();

        if (!includeAllUsers)
        {
            query = query.Where(j => j.Video != null && j.Video.UploadedByUserId == currentUserId);
        }

        if (request.VideoId.HasValue)
        {
            query = query.Where(j => j.VideoId == request.VideoId.Value);
        }

        if (request.RequestedByUserId.HasValue)
        {
            query = query.Where(j => j.RequestedByUserId == request.RequestedByUserId.Value);
        }

        if (!string.IsNullOrWhiteSpace(request.JobType) &&
            Enum.TryParse<JobType>(request.JobType, true, out var jobType))
        {
            query = query.Where(j => j.JobType == jobType);
        }

        if (!string.IsNullOrWhiteSpace(request.Status) &&
            Enum.TryParse<JobStatus>(request.Status, true, out var status))
        {
            query = query.Where(j => j.Status == status);
        }

        if (request.CreatedFrom.HasValue)
        {
            query = query.Where(j => j.CreatedAt >= request.CreatedFrom.Value);
        }

        if (request.CreatedTo.HasValue)
        {
            query = query.Where(j => j.CreatedAt <= request.CreatedTo.Value);
        }

        return query
            .OrderByDescending(j => j.CreatedAt)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public Task<int> CountAsync(CancellationToken cancellationToken = default)
    {
        return _db.ProcessingJobs.CountAsync(cancellationToken);
    }

    public Task<int> CountByStatusAsync(string status, CancellationToken cancellationToken = default)
    {
        return Enum.TryParse<JobStatus>(status, true, out var parsed)
            ? _db.ProcessingJobs.CountAsync(j => j.Status == parsed, cancellationToken)
            : Task.FromResult(0);
    }

    public async Task<IReadOnlyList<(string Status, int Count)>> CountGroupedByStatusAsync(CancellationToken cancellationToken = default)
    {
        var rows = await _db.ProcessingJobs
            .AsNoTracking()
            .GroupBy(j => j.Status)
            .Select(g => new { Status = g.Key.ToString(), Count = g.Count() })
            .ToListAsync(cancellationToken);

        return rows.Select(row => (row.Status, row.Count)).ToList();
    }

    public async Task AddAsync(ProcessingJob job, CancellationToken cancellationToken = default)
    {
        await _db.ProcessingJobs.AddAsync(job, cancellationToken);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
