using SA.Models.Dto.Common;
using SA.Models.Dto.Videos;

namespace SA.Services.Interfaces;

public interface IVideoService
{
    Task<PagedResponse<VideoResponse>> GetVideosAsync(VideoQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<VideoResponse> GetVideoAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<VideoResponse> CreateVideoAsync(CreateVideoRecordRequest request, Guid currentUserId, CancellationToken cancellationToken = default);
    Task<VideoResponse> UpdateVideoAsync(Guid id, UpdateVideoRecordRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task DeleteVideoAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
}
