using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class ProcessingJobService : IProcessingJobService
{
    private static readonly Dictionary<JobStatus, JobStatus[]> AllowedTransitions = new()
    {
        [JobStatus.Queued] = [JobStatus.Running, JobStatus.Cancelled, JobStatus.Failed],
        [JobStatus.Running] = [JobStatus.Completed, JobStatus.Failed, JobStatus.Cancelled],
        [JobStatus.Completed] = [],
        [JobStatus.Failed] = [],
        [JobStatus.Cancelled] = []
    };

    private readonly IProcessingJobRepository _jobs;
    private readonly IVideoRepository _videos;

    public ProcessingJobService(IProcessingJobRepository jobs, IVideoRepository videos)
    {
        _jobs = jobs;
        _videos = videos;
    }

    public async Task<PagedResponse<ProcessingJobResponse>> GetJobsAsync(ProcessingJobQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var page = await _jobs.SearchAsync(request, isAdmin, currentUserId, cancellationToken);
        return new PagedResponse<ProcessingJobResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToProcessingJobResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<ProcessingJobResponse> GetJobAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var job = await _jobs.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Processing job was not found.");

        EnsureCanAccess(job, currentUserId, isAdmin);
        return ServiceMapping.ToProcessingJobResponse(job);
    }

    public async Task<ProcessingJobResponse> CreateJobAsync(CreateProcessingJobRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var video = await _videos.GetByIdAsync(request.VideoId, cancellationToken)
            ?? throw new NotFoundException("Video was not found.");

        if (!isAdmin && video.UploadedByUserId != currentUserId)
        {
            throw new ForbiddenException("You cannot create a job for another user's video.");
        }

        if (!Enum.TryParse<JobType>(request.JobType, true, out var jobType))
        {
            throw new ValidationException("Invalid job type.");
        }

        var job = new ProcessingJob
        {
            VideoId = request.VideoId,
            RequestedByUserId = currentUserId,
            JobType = jobType,
            Status = JobStatus.Queued,
            ModelName = request.ModelName?.Trim(),
            InputPath = request.InputPath.Trim(),
            ProgressPercent = 0,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _jobs.AddAsync(job, cancellationToken);
        video.Status = VideoStatus.Queued;
        video.UpdatedAt = DateTime.UtcNow;
        await _jobs.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToProcessingJobResponse(job);
    }

    public async Task<ProcessingJobResponse> UpdateStatusAsync(Guid id, UpdateProcessingJobStatusRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var job = await _jobs.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Processing job was not found.");

        EnsureCanAccess(job, currentUserId, isAdmin);

        if (!Enum.TryParse<JobStatus>(request.Status, true, out var newStatus))
        {
            throw new ValidationException("Invalid job status.");
        }

        if (newStatus != job.Status && !AllowedTransitions[job.Status].Contains(newStatus))
        {
            throw new ValidationException($"Cannot move job from {job.Status} to {newStatus}.");
        }

        job.Status = newStatus;
        job.ProgressPercent = request.ProgressPercent ?? StatusProgress(newStatus);
        job.FrameCount = request.FrameCount ?? job.FrameCount;
        job.ObjectCount = request.ObjectCount ?? job.ObjectCount;
        job.OutputPath = string.IsNullOrWhiteSpace(request.OutputPath) ? job.OutputPath : request.OutputPath.Trim();
        job.ErrorMessage = request.ErrorMessage;
        job.UpdatedAt = DateTime.UtcNow;

        if (newStatus == JobStatus.Running && job.StartedAt is null)
        {
            job.StartedAt = DateTime.UtcNow;
        }

        if (newStatus is JobStatus.Completed or JobStatus.Failed or JobStatus.Cancelled)
        {
            job.CompletedAt = DateTime.UtcNow;
        }

        if (job.Video is not null)
        {
            job.Video.Status = newStatus switch
            {
                JobStatus.Queued => VideoStatus.Queued,
                JobStatus.Running => VideoStatus.Processing,
                JobStatus.Completed => VideoStatus.Ready,
                JobStatus.Failed => VideoStatus.Failed,
                JobStatus.Cancelled => VideoStatus.Uploaded,
                _ => job.Video.Status
            };
            job.Video.AnnotatedOutputPath = job.OutputPath ?? job.Video.AnnotatedOutputPath;
            job.Video.ErrorMessage = job.ErrorMessage;
            job.Video.UpdatedAt = DateTime.UtcNow;
        }

        await _jobs.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToProcessingJobResponse(job);
    }

    private static void EnsureCanAccess(ProcessingJob job, Guid currentUserId, bool isAdmin)
    {
        if (!isAdmin && job.Video?.UploadedByUserId != currentUserId && job.RequestedByUserId != currentUserId)
        {
            throw new ForbiddenException("You do not have access to this processing job.");
        }
    }

    private static int StatusProgress(JobStatus status)
    {
        return status switch
        {
            JobStatus.Queued => 0,
            JobStatus.Running => 50,
            JobStatus.Completed => 100,
            JobStatus.Failed => 100,
            JobStatus.Cancelled => 100,
            _ => 0
        };
    }
}
