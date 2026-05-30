using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Detections;
using SA.Models.Entities;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class DetectionRepository : IDetectionRepository
{
    private readonly AppDbContext _db;

    public DetectionRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<Detection?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return _db.Detections
            .Include(d => d.Video)
            .Include(d => d.ProcessingJob)
            .FirstOrDefaultAsync(d => d.Id == id, cancellationToken);
    }

    public Task<PagedResponse<Detection>> SearchAsync(DetectionQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        var query = _db.Detections
            .AsNoTracking()
            .Include(d => d.Video)
            .Include(d => d.ProcessingJob)
            .AsQueryable();

        if (!includeAllUsers)
        {
            query = query.Where(d => d.Video != null && d.Video.UploadedByUserId == currentUserId);
        }

        if (request.ProcessingJobId.HasValue)
        {
            query = query.Where(d => d.ProcessingJobId == request.ProcessingJobId.Value);
        }

        if (request.VideoId.HasValue)
        {
            query = query.Where(d => d.VideoId == request.VideoId.Value);
        }

        if (!string.IsNullOrWhiteSpace(request.Label))
        {
            var label = request.Label.Trim().ToLowerInvariant();
            query = query.Where(d => d.Label.ToLower() == label);
        }

        return query
            .OrderByDescending(d => d.CreatedAt)
            .ThenBy(d => d.FrameIndex)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public async Task AddAsync(Detection detection, CancellationToken cancellationToken = default)
    {
        await _db.Detections.AddAsync(detection, cancellationToken);
    }

    public async Task AddRangeAsync(IEnumerable<Detection> detections, CancellationToken cancellationToken = default)
    {
        await _db.Detections.AddRangeAsync(detections, cancellationToken);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
