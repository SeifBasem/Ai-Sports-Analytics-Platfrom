using SA.Models.Dto.Common;
using SA.Models.Dto.Detections;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IDetectionRepository
{
    Task<Detection?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<PagedResponse<Detection>> SearchAsync(DetectionQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default);
    Task AddAsync(Detection detection, CancellationToken cancellationToken = default);
    Task AddRangeAsync(IEnumerable<Detection> detections, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
