using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Videos;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class VideoService : IVideoService
{
    private readonly IVideoRepository _videos;

    public VideoService(IVideoRepository videos)
    {
        _videos = videos;
    }

    public async Task<PagedResponse<VideoResponse>> GetVideosAsync(VideoQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var page = await _videos.SearchAsync(request, isAdmin, currentUserId, cancellationToken);
        return new PagedResponse<VideoResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToVideoResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<VideoResponse> GetVideoAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var video = await _videos.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Video was not found.");

        EnsureCanAccess(video, currentUserId, isAdmin);
        return ServiceMapping.ToVideoResponse(video);
    }

    public async Task<VideoResponse> CreateVideoAsync(CreateVideoRecordRequest request, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        var video = new Video
        {
            UploadedByUserId = currentUserId,
            Title = request.Title.Trim(),
            OriginalFilename = request.OriginalFilename.Trim(),
            StoredFilename = request.StoredFilename.Trim(),
            MimeType = request.MimeType.Trim(),
            StoragePath = request.StoragePath.Trim(),
            SizeBytes = request.SizeBytes,
            DurationSeconds = request.DurationSeconds,
            Status = VideoStatus.Uploaded,
            UploadedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _videos.AddAsync(video, cancellationToken);
        await _videos.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToVideoResponse(video);
    }

    public async Task<VideoResponse> UpdateVideoAsync(Guid id, UpdateVideoRecordRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var video = await _videos.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Video was not found.");

        EnsureCanAccess(video, currentUserId, isAdmin);

        if (!string.IsNullOrWhiteSpace(request.Status))
        {
            if (!Enum.TryParse<VideoStatus>(request.Status, true, out var status))
            {
                throw new ValidationException("Invalid video status.");
            }

            video.Status = status;
        }

        video.Title = request.Title.Trim();
        video.AnnotatedOutputPath = string.IsNullOrWhiteSpace(request.AnnotatedOutputPath)
            ? null
            : request.AnnotatedOutputPath.Trim();
        video.ErrorMessage = request.ErrorMessage;
        video.UpdatedAt = DateTime.UtcNow;
        await _videos.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToVideoResponse(video);
    }

    public async Task DeleteVideoAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var video = await _videos.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Video was not found.");

        EnsureCanAccess(video, currentUserId, isAdmin);
        _videos.Remove(video);
        await _videos.SaveChangesAsync(cancellationToken);
    }

    private static void EnsureCanAccess(Video video, Guid currentUserId, bool isAdmin)
    {
        if (!isAdmin && video.UploadedByUserId != currentUserId)
        {
            throw new ForbiddenException("You do not have access to this video.");
        }
    }
}
