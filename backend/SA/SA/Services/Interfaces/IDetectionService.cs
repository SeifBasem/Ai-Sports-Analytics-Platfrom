using SA.Models.Dto.Common;
using SA.Models.Dto.Detections;

namespace SA.Services.Interfaces;

public interface IDetectionService
{
    Task<PagedResponse<DetectionResponse>> GetDetectionsAsync(DetectionQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<DetectionResponse> GetDetectionAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<DetectionResponse> CreateDetectionAsync(CreateDetectionRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<DetectionResponse>> CreateDetectionsAsync(CreateDetectionBatchRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
}
