using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Videos;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class VideoRepository : IVideoRepository
{
    private readonly AppDbContext _db;

    public VideoRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<Video?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return _db.Videos
            .Include(v => v.UploadedByUser)
            .FirstOrDefaultAsync(v => v.Id == id, cancellationToken);
    }

    public Task<PagedResponse<Video>> SearchAsync(VideoQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        var query = _db.Videos
            .AsNoTracking()
            .Include(v => v.UploadedByUser)
            .AsQueryable();

        if (!includeAllUsers)
        {
            query = query.Where(v => v.UploadedByUserId == currentUserId);
        }
        else if (request.UploadedByUserId.HasValue)
        {
            query = query.Where(v => v.UploadedByUserId == request.UploadedByUserId.Value);
        }

        if (!string.IsNullOrWhiteSpace(request.Search))
        {
            var search = request.Search.Trim().ToLowerInvariant();
            query = query.Where(v =>
                v.Title.ToLower().Contains(search) ||
                v.OriginalFilename.ToLower().Contains(search));
        }

        if (!string.IsNullOrWhiteSpace(request.Status) &&
            Enum.TryParse<VideoStatus>(request.Status, true, out var status))
        {
            query = query.Where(v => v.Status == status);
        }

        return query
            .OrderByDescending(v => v.UploadedAt)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public Task<int> CountAsync(CancellationToken cancellationToken = default)
    {
        return _db.Videos.CountAsync(cancellationToken);
    }

    public async Task<IReadOnlyList<(string Status, int Count)>> CountByStatusAsync(CancellationToken cancellationToken = default)
    {
        var rows = await _db.Videos
            .AsNoTracking()
            .GroupBy(v => v.Status)
            .Select(g => new { Status = g.Key.ToString(), Count = g.Count() })
            .ToListAsync(cancellationToken);

        return rows.Select(row => (row.Status, row.Count)).ToList();
    }

    public async Task AddAsync(Video video, CancellationToken cancellationToken = default)
    {
        await _db.Videos.AddAsync(video, cancellationToken);
    }

    public void Remove(Video video)
    {
        _db.Videos.Remove(video);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
