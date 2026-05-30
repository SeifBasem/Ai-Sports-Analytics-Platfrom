using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Detections;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class DetectionService : IDetectionService
{
    private const int MaxBatchSize = 5000;

    private readonly IDetectionRepository _detections;
    private readonly IProcessingJobRepository _jobs;
    private readonly IVideoRepository _videos;
    private readonly IAuditLogRepository _auditLogs;

    public DetectionService(
        IDetectionRepository detections,
        IProcessingJobRepository jobs,
        IVideoRepository videos,
        IAuditLogRepository auditLogs)
    {
        _detections = detections;
        _jobs = jobs;
        _videos = videos;
        _auditLogs = auditLogs;
    }

    public async Task<PagedResponse<DetectionResponse>> GetDetectionsAsync(DetectionQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var page = await _detections.SearchAsync(request, isAdmin, currentUserId, cancellationToken);
        return new PagedResponse<DetectionResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToDetectionResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<DetectionResponse> GetDetectionAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var detection = await _detections.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Detection was not found.");

        EnsureCanAccess(detection, currentUserId, isAdmin);
        return ServiceMapping.ToDetectionResponse(detection);
    }

    public async Task<DetectionResponse> CreateDetectionAsync(CreateDetectionRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var detection = await BuildDetectionAsync(request, currentUserId, isAdmin, cancellationToken);
        await _detections.AddAsync(detection, cancellationToken);
        await AddAuditLogAsync(currentUserId, AuditEntityType.Detection, detection.Id.ToString(), "Create", "Succeeded", cancellationToken);
        await _detections.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToDetectionResponse(detection);
    }

    public async Task<IReadOnlyList<DetectionResponse>> CreateDetectionsAsync(CreateDetectionBatchRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        if (request.Detections.Count == 0)
        {
            throw new ValidationException("At least one detection is required.");
        }

        if (request.Detections.Count > MaxBatchSize)
        {
            throw new ValidationException($"A detection batch cannot exceed {MaxBatchSize} rows.");
        }

        var rows = new List<Detection>(request.Detections.Count);
        foreach (var detectionRequest in request.Detections)
        {
            rows.Add(await BuildDetectionAsync(detectionRequest, currentUserId, isAdmin, cancellationToken));
        }

        await _detections.AddRangeAsync(rows, cancellationToken);
        await AddAuditLogAsync(currentUserId, AuditEntityType.Detection, rows[0].ProcessingJobId.ToString(), "CreateBatch", "Succeeded", cancellationToken);
        await _detections.SaveChangesAsync(cancellationToken);
        return rows.Select(ServiceMapping.ToDetectionResponse).ToList();
    }

    private async Task<Detection> BuildDetectionAsync(CreateDetectionRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken)
    {
        ValidateDetection(request);

        var job = await _jobs.GetByIdAsync(request.ProcessingJobId, cancellationToken)
            ?? throw new NotFoundException("Processing job was not found.");

        var video = await _videos.GetByIdAsync(request.VideoId, cancellationToken)
            ?? throw new NotFoundException("Video was not found.");

        if (job.VideoId != video.Id)
        {
            throw new ValidationException("Detection video must match the processing job video.");
        }

        EnsureCanAccess(job, video, currentUserId, isAdmin);

        return new Detection
        {
            ProcessingJobId = job.Id,
            VideoId = video.Id,
            FrameIndex = request.FrameIndex,
            TimestampSeconds = request.TimestampSeconds,
            Label = request.Label.Trim(),
            Confidence = request.Confidence,
            X1 = request.X1,
            Y1 = request.Y1,
            X2 = request.X2,
            Y2 = request.Y2,
            CreatedAt = DateTime.UtcNow
        };
    }

    private static void ValidateDetection(CreateDetectionRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Label))
        {
            throw new ValidationException("Detection label is required.");
        }

        if (request.X2 < request.X1 || request.Y2 < request.Y1)
        {
            throw new ValidationException("Detection bounding box coordinates are invalid.");
        }
    }

    private static void EnsureCanAccess(Detection detection, Guid currentUserId, bool isAdmin)
    {
        if (isAdmin)
        {
            return;
        }

        if (detection.Video?.UploadedByUserId == currentUserId || detection.ProcessingJob?.RequestedByUserId == currentUserId)
        {
            return;
        }

        throw new ForbiddenException("You do not have access to this detection.");
    }

    private static void EnsureCanAccess(ProcessingJob job, Video video, Guid currentUserId, bool isAdmin)
    {
        if (!isAdmin && video.UploadedByUserId != currentUserId && job.RequestedByUserId != currentUserId)
        {
            throw new ForbiddenException("You do not have access to this processing job.");
        }
    }

    private async Task AddAuditLogAsync(Guid actorUserId, AuditEntityType entityType, string entityId, string action, string status, CancellationToken cancellationToken)
    {
        await _auditLogs.AddAsync(new AuditLog
        {
            ActorUserId = actorUserId,
            EntityType = entityType,
            EntityId = entityId,
            Action = action,
            Status = status,
            CreatedAt = DateTime.UtcNow
        }, cancellationToken);
    }
}
