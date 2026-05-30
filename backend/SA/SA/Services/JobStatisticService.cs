using System.Globalization;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class JobStatisticService : IJobStatisticService
{
    private readonly IJobStatisticRepository _statistics;
    private readonly IProcessingJobRepository _jobs;
    private readonly IVideoRepository _videos;
    private readonly IAuditLogRepository _auditLogs;
    private readonly AppDbContext _db;

    public JobStatisticService(
        IJobStatisticRepository statistics,
        IProcessingJobRepository jobs,
        IVideoRepository videos,
        IAuditLogRepository auditLogs,
        AppDbContext db)
    {
        _statistics = statistics;
        _jobs = jobs;
        _videos = videos;
        _auditLogs = auditLogs;
        _db = db;
    }

    public async Task<PagedResponse<JobStatisticResponse>> GetStatisticsAsync(JobStatisticQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var page = await _statistics.SearchAsync(request, isAdmin, currentUserId, cancellationToken);
        return new PagedResponse<JobStatisticResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToJobStatisticResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<JobStatisticResponse> AddStatisticAsync(Guid processingJobId, CreateJobStatisticRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var job = await GetAuthorizedJobAsync(processingJobId, currentUserId, isAdmin, cancellationToken);
        var statistic = BuildStatistic(job, request);
        await _statistics.AddAsync(statistic, cancellationToken);
        await AddAuditLogAsync(currentUserId, AuditEntityType.JobStatistic, processingJobId.ToString(), "Create", "Succeeded", cancellationToken);
        await _statistics.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToJobStatisticResponse(statistic);
    }

    public async Task<IReadOnlyList<JobStatisticResponse>> AddStatisticsAsync(Guid processingJobId, CreateJobStatisticsBatchRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default)
    {
        var job = await GetAuthorizedJobAsync(processingJobId, currentUserId, isAdmin, cancellationToken);

        if (request.Statistics.Count == 0)
        {
            throw new ValidationException("At least one statistic is required.");
        }

        var rows = request.Statistics.Select(stat => BuildStatistic(job, stat)).ToList();
        await _statistics.AddRangeAsync(rows, cancellationToken);
        await AddAuditLogAsync(currentUserId, AuditEntityType.JobStatistic, processingJobId.ToString(), "CreateBatch", "Succeeded", cancellationToken);
        await _statistics.SaveChangesAsync(cancellationToken);
        return rows.Select(ServiceMapping.ToJobStatisticResponse).ToList();
    }

    public async Task<ProcessingJobResponse> IngestAiJobStatisticsAsync(AiJobStatisticsIngestRequest request, Guid currentUserId, CancellationToken cancellationToken = default)
    {
        if (request.Statistics.Count == 0)
        {
            throw new ValidationException("At least one statistic is required.");
        }

        var project = await GetOrCreateProjectAsync(request.ProjectName ?? request.Title, currentUserId, cancellationToken);
        var job = await _jobs.GetByIdAsync(request.JobId, cancellationToken);
        Video? video;

        if (job is null)
        {
            video = new Video
            {
                ProjectId = project?.Id,
                UploadedByUserId = currentUserId,
                Title = string.IsNullOrWhiteSpace(request.Title)
                    ? Path.GetFileNameWithoutExtension(request.OriginalFilename)
                    : request.Title.Trim(),
                OriginalFilename = request.OriginalFilename.Trim(),
                StoredFilename = Path.GetFileName(request.InputPath ?? request.OriginalFilename),
                MimeType = "video/mp4",
                StoragePath = request.InputPath ?? string.Empty,
                AnnotatedOutputPath = request.OutputPath,
                SizeBytes = GetFileSizeBytes(request.InputPath),
                Status = ParseVideoStatus(request.Status),
                ErrorMessage = request.ErrorMessage,
                UploadedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            };

            await _videos.AddAsync(video, cancellationToken);

            job = new ProcessingJob
            {
                Id = request.JobId,
                Video = video,
                VideoId = video.Id,
                RequestedByUserId = currentUserId,
                JobType = ParseJobType(request.JobType),
                Status = ParseJobStatus(request.Status),
                ModelName = request.ModelName?.Trim(),
                InputPath = request.InputPath ?? string.Empty,
                OutputPath = request.OutputPath,
                CsvDir = request.CsvDir,
                ProgressPercent = ParseJobStatus(request.Status) == JobStatus.Completed ? 100 : 0,
                FrameCount = request.FrameCount,
                ObjectCount = request.ObjectCount,
                MetadataJson = BuildMetadataJson(request),
                StartedAt = DateTime.UtcNow,
                CompletedAt = DateTime.UtcNow,
                ErrorMessage = request.ErrorMessage,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            };
            if (project is not null)
            {
                job.ProjectId = project.Id;
                job.Project = project;
            }

            await _jobs.AddAsync(job, cancellationToken);
        }
        else
        {
            EnsureCanAccess(job, currentUserId, isAdmin: false);
            video = job.Video ?? await _videos.GetByIdAsync(job.VideoId, cancellationToken)
                ?? throw new NotFoundException("Video for processing job was not found.");

            job.Status = ParseJobStatus(request.Status);
            job.ModelName = request.ModelName?.Trim() ?? job.ModelName;
            job.OutputPath = request.OutputPath ?? job.OutputPath;
            job.CsvDir = request.CsvDir ?? job.CsvDir;
            job.FrameCount = request.FrameCount ?? job.FrameCount;
            job.ObjectCount = request.ObjectCount ?? job.ObjectCount;
            job.MetadataJson = BuildMetadataJson(request) ?? job.MetadataJson;
            job.ErrorMessage = request.ErrorMessage;
            job.ProgressPercent = job.Status == JobStatus.Completed ? 100 : job.ProgressPercent;
            job.CompletedAt ??= DateTime.UtcNow;
            job.UpdatedAt = DateTime.UtcNow;

            video.Status = ParseVideoStatus(request.Status);
            video.ProjectId = project?.Id ?? video.ProjectId;
            video.AnnotatedOutputPath = request.OutputPath ?? video.AnnotatedOutputPath;
            video.ErrorMessage = request.ErrorMessage;
            video.UpdatedAt = DateTime.UtcNow;
            job.Video = video;
            job.ProjectId = project?.Id ?? job.ProjectId;
            job.Project = project ?? job.Project;
        }

        var stats = request.Statistics.Select(stat => BuildStatistic(job, stat)).ToList();
        await _statistics.AddRangeAsync(stats, cancellationToken);
        await AddNormalizedAiRowsAsync(job, video, project, request, currentUserId, cancellationToken);
        await AddAuditLogAsync(currentUserId, AuditEntityType.JobStatistic, job.Id.ToString(), "IngestAiStatistics", "Succeeded", cancellationToken);
        await _statistics.SaveChangesAsync(cancellationToken);

        return ServiceMapping.ToProcessingJobResponse(job);
    }

    private static string? BuildMetadataJson(AiJobStatisticsIngestRequest request)
    {
        var values = new Dictionary<string, string>();

        AddIfPresent("uploadBatchId", request.UploadBatchId);
        AddIfPresent("uploadBatchTitle", request.UploadBatchTitle);
        AddIfPresent("uploadBatchVideoCount", request.UploadBatchVideoCount);
        AddIfPresent("uploadBatchIndex", request.UploadBatchIndex);
        AddIfPresent("playerName", request.PlayerName);

        return values.Count == 0 ? null : JsonSerializer.Serialize(values);

        void AddIfPresent(string key, string? value)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                values[key] = value.Trim();
            }
        }
    }

    private async Task<Project?> GetOrCreateProjectAsync(string? projectName, Guid currentUserId, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(projectName))
        {
            return null;
        }

        var name = projectName.Trim();
        var project = await _db.Projects
            .FirstOrDefaultAsync(p => p.OwnerUserId == currentUserId && p.Name == name, cancellationToken);

        if (project is not null)
        {
            project.UpdatedAt = DateTime.UtcNow;
            return project;
        }

        project = new Project
        {
            OwnerUserId = currentUserId,
            Name = name,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _db.Projects.AddAsync(project, cancellationToken);
        return project;
    }

    private async Task AddNormalizedAiRowsAsync(
        ProcessingJob job,
        Video video,
        Project? project,
        AiJobStatisticsIngestRequest request,
        Guid currentUserId,
        CancellationToken cancellationToken)
    {
        var createdAt = DateTime.UtcNow;

        if (request.Statistics.Count > 0)
        {
            var aiStats = request.Statistics.Select(stat => new AIStatistic
            {
                ProjectId = project?.Id ?? job.ProjectId,
                ProcessingJobId = job.Id,
                VideoId = video.Id,
                UserId = currentUserId,
                ModelModule = stat.ModuleName.Trim(),
                StatGroup = NormalizeStatGroup(stat.StatType),
                StatKey = stat.StatType.Trim(),
                JsonValue = stat.StatsJson,
                CreatedAt = createdAt
            }).ToList();

            await _db.AIStatistics.AddRangeAsync(aiStats, cancellationToken);
        }

        if (request.ResultFiles.Count > 0)
        {
            var existingKeys = await _db.AIResultFiles
                .Where(f => f.ProcessingJobId == job.Id)
                .Select(f => f.FileKey)
                .ToListAsync(cancellationToken);
            var existing = existingKeys.ToHashSet(StringComparer.OrdinalIgnoreCase);

            var files = request.ResultFiles
                .Where(file => !existing.Contains(file.FileKey.Trim()))
                .Select(file => new AIResultFile
                {
                    ProcessingJobId = job.Id,
                    FileType = file.FileType.Trim(),
                    FileKey = file.FileKey.Trim(),
                    StoragePath = file.StoragePath.Trim(),
                    MimeType = string.IsNullOrWhiteSpace(file.MimeType) ? null : file.MimeType.Trim(),
                    CreatedAt = createdAt
                })
                .ToList();

            await _db.AIResultFiles.AddRangeAsync(files, cancellationToken);
        }

        if (request.ActionPredictions.Count > 0)
        {
            var oldPredictions = _db.ActionPredictions.Where(p => p.ProcessingJobId == job.Id);
            _db.ActionPredictions.RemoveRange(oldPredictions);

            var predictions = request.ActionPredictions.Select(prediction => new ActionPrediction
            {
                ProcessingJobId = job.Id,
                GameTime = prediction.GameTime?.Trim() ?? string.Empty,
                Label = prediction.Label.Trim(),
                Team = string.IsNullOrWhiteSpace(prediction.Team) ? null : prediction.Team.Trim(),
                Position = string.IsNullOrWhiteSpace(prediction.Position) ? null : prediction.Position.Trim(),
                Half = prediction.Half,
                Confidence = prediction.Confidence,
                Frame = prediction.Frame,
                ClassName = string.IsNullOrWhiteSpace(prediction.ClassName) ? null : prediction.ClassName.Trim(),
                Second = prediction.Second,
                CreatedAt = createdAt
            }).ToList();

            await _db.ActionPredictions.AddRangeAsync(predictions, cancellationToken);
        }

        await ImportDetectionsCsvAsync(job, video, request.ResultFiles, cancellationToken);
    }

    private async Task ImportDetectionsCsvAsync(
        ProcessingJob job,
        Video video,
        IReadOnlyCollection<AiResultFileIngestRequest> resultFiles,
        CancellationToken cancellationToken)
    {
        if (await _db.Detections.AnyAsync(d => d.ProcessingJobId == job.Id, cancellationToken))
        {
            return;
        }

        var detectionsPath = resultFiles
            .FirstOrDefault(f => f.FileKey.Equals("detections", StringComparison.OrdinalIgnoreCase))
            ?.StoragePath;

        if (string.IsNullOrWhiteSpace(detectionsPath) || !File.Exists(detectionsPath))
        {
            return;
        }

        var rows = new List<Detection>();
        foreach (var line in File.ReadLines(detectionsPath).Skip(1))
        {
            var parts = line.Split(',');
            if (parts.Length < 8)
            {
                continue;
            }

            if (!int.TryParse(parts[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out var frameIndex))
            {
                continue;
            }

            rows.Add(new Detection
            {
                ProcessingJobId = job.Id,
                VideoId = video.Id,
                FrameIndex = frameIndex,
                X1 = ParseDecimal(parts[1]),
                Y1 = ParseDecimal(parts[2]),
                X2 = ParseDecimal(parts[3]),
                Y2 = ParseDecimal(parts[4]),
                Confidence = ParseDecimal(parts[5]),
                Label = $"class_{parts[6].Trim()}",
                CreatedAt = DateTime.UtcNow
            });
        }

        if (rows.Count > 0)
        {
            await _db.Detections.AddRangeAsync(rows, cancellationToken);
        }
    }

    private static decimal ParseDecimal(string value)
    {
        return decimal.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : 0m;
    }

    private static string NormalizeStatGroup(string statType)
    {
        var value = statType.Trim().ToLowerInvariant();
        if (value.Contains("action"))
        {
            return "action_spotting";
        }
        if (value.Contains("csv") || value.Contains("position") || value.Contains("pass"))
        {
            return "tracking";
        }
        return "analysis";
    }

    private async Task<ProcessingJob> GetAuthorizedJobAsync(Guid processingJobId, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken)
    {
        var job = await _jobs.GetByIdAsync(processingJobId, cancellationToken)
            ?? throw new NotFoundException("Processing job was not found.");

        EnsureCanAccess(job, currentUserId, isAdmin);
        return job;
    }

    private static JobStatistic BuildStatistic(ProcessingJob job, CreateJobStatisticRequest request)
    {
        ValidateJson(request.StatsJson);

        return new JobStatistic
        {
            ProcessingJobId = job.Id,
            VideoId = job.VideoId,
            ModuleName = request.ModuleName.Trim(),
            ModelName = string.IsNullOrWhiteSpace(request.ModelName) ? null : request.ModelName.Trim(),
            StatType = request.StatType.Trim(),
            StatsJson = request.StatsJson,
            CreatedAt = DateTime.UtcNow
        };
    }

    private static void ValidateJson(string value)
    {
        try
        {
            JsonDocument.Parse(value);
        }
        catch (JsonException)
        {
            throw new ValidationException("StatsJson must be valid JSON.");
        }
    }

    private static void EnsureCanAccess(ProcessingJob job, Guid currentUserId, bool isAdmin)
    {
        if (!isAdmin && job.Video?.UploadedByUserId != currentUserId && job.RequestedByUserId != currentUserId)
        {
            throw new ForbiddenException("You do not have access to this processing job.");
        }
    }

    private static JobType ParseJobType(string? value)
    {
        return Enum.TryParse<JobType>(value, true, out var parsed)
            ? parsed
            : JobType.VideoDetection;
    }

    private static JobStatus ParseJobStatus(string? value)
    {
        return Enum.TryParse<JobStatus>(value, true, out var parsed)
            ? parsed
            : JobStatus.Completed;
    }

    private static VideoStatus ParseVideoStatus(string? value)
    {
        return ParseJobStatus(value) switch
        {
            JobStatus.Queued => VideoStatus.Queued,
            JobStatus.Running => VideoStatus.Processing,
            JobStatus.Completed => VideoStatus.Ready,
            JobStatus.Failed => VideoStatus.Failed,
            JobStatus.Cancelled => VideoStatus.Uploaded,
            _ => VideoStatus.Uploaded
        };
    }

    private static long GetFileSizeBytes(string? path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return 0;
        }

        try
        {
            var file = new FileInfo(path);
            return file.Exists ? file.Length : 0;
        }
        catch
        {
            return 0;
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
