using SA.Models.Dto.Common;
using SA.Models.Dto.Videos;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IVideoRepository
{
    Task<Video?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<PagedResponse<Video>> SearchAsync(VideoQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default);
    Task<int> CountAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<(string Status, int Count)>> CountByStatusAsync(CancellationToken cancellationToken = default);
    Task AddAsync(Video video, CancellationToken cancellationToken = default);
    void Remove(Video video);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
