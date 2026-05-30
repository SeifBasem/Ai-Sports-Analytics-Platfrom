using SA.Models.Dto.Auth;
using SA.Models.Dto.Audit;
using SA.Models.Dto.Detections;
using SA.Models.Dto.Jobs;
using SA.Models.Dto.Matches;
using SA.Models.Dto.Reports;
using SA.Models.Dto.Videos;
using SA.Models.Entities;

namespace SA.Services;

internal static class ServiceMapping
{
    public static VideoResponse ToVideoResponse(Video video)
    {
        return new VideoResponse
        {
            Id = video.Id,
            UploadedByUserId = video.UploadedByUserId,
            UploadedBy = video.UploadedByUser?.FullName ?? video.UploadedByUser?.Username ?? string.Empty,
            Title = video.Title,
            OriginalFilename = video.OriginalFilename,
            StoredFilename = video.StoredFilename,
            MimeType = video.MimeType,
            StoragePath = video.StoragePath,
            AnnotatedOutputPath = video.AnnotatedOutputPath,
            SizeBytes = video.SizeBytes,
            DurationSeconds = video.DurationSeconds,
            Status = video.Status.ToString(),
            ErrorMessage = video.ErrorMessage,
            UploadedAt = video.UploadedAt,
            UpdatedAt = video.UpdatedAt
        };
    }

    public static ProcessingJobResponse ToProcessingJobResponse(ProcessingJob job)
    {
        return new ProcessingJobResponse
        {
            Id = job.Id,
            VideoId = job.VideoId,
            VideoTitle = job.Video?.Title ?? string.Empty,
            RequestedByUserId = job.RequestedByUserId,
            RequestedBy = job.RequestedByUser?.FullName ?? job.RequestedByUser?.Username,
            JobType = job.JobType.ToString(),
            Status = job.Status.ToString(),
            ModelName = job.ModelName,
            InputPath = job.InputPath,
            OutputPath = job.OutputPath,
            ProgressPercent = job.ProgressPercent,
            FrameCount = job.FrameCount,
            ObjectCount = job.ObjectCount,
            StartedAt = job.StartedAt,
            CompletedAt = job.CompletedAt,
            ErrorMessage = job.ErrorMessage,
            MetadataJson = job.MetadataJson,
            CreatedAt = job.CreatedAt,
            UpdatedAt = job.UpdatedAt
        };
    }

    public static JobStatisticResponse ToJobStatisticResponse(JobStatistic statistic)
    {
        return new JobStatisticResponse
        {
            Id = statistic.Id,
            ProcessingJobId = statistic.ProcessingJobId,
            VideoId = statistic.VideoId,
            ModuleName = statistic.ModuleName,
            ModelName = statistic.ModelName,
            StatType = statistic.StatType,
            StatsJson = statistic.StatsJson,
            CreatedAt = statistic.CreatedAt
        };
    }

    public static ReportResponse ToReportResponse(Report report)
    {
        return new ReportResponse
        {
            Id = report.Id,
            CreatedByUserId = report.CreatedByUserId,
            CreatedBy = report.CreatedByUser?.FullName ?? report.CreatedByUser?.Username ?? string.Empty,
            VideoId = report.VideoId,
            VideoTitle = report.Video?.Title,
            ProcessingJobId = report.ProcessingJobId,
            Title = report.Title,
            Description = report.Description,
            ReportType = report.ReportType.ToString(),
            Format = report.Format.ToString(),
            Status = report.Status.ToString(),
            FilePath = report.FilePath,
            GeneratedAt = report.GeneratedAt,
            CreatedAt = report.CreatedAt,
            UpdatedAt = report.UpdatedAt
        };
    }

    public static MatchResponse ToMatchResponse(Match match)
    {
        return ToMatchResponse(match, match.Annotations.Count);
    }

    public static MatchResponse ToMatchResponse(Match match, int annotationCount)
    {
        return new MatchResponse
        {
            Id = match.Id,
            UrlLocal = match.UrlLocal,
            UrlYoutube = match.UrlYoutube,
            Halftime = match.Halftime,
            HalfNumber = match.HalfNumber,
            HalftimeMinutes = match.HalftimeMinutes,
            HomeTeam = match.HomeTeam,
            AwayTeam = match.AwayTeam,
            Competition = match.Competition,
            Season = match.Season,
            MatchDate = match.MatchDate,
            ImportedAt = match.ImportedAt,
            AnnotationCount = annotationCount
        };
    }

    public static MatchAnnotationResponse ToMatchAnnotationResponse(MatchAnnotation annotation)
    {
        return new MatchAnnotationResponse
        {
            Id = annotation.Id,
            MatchId = annotation.MatchId,
            GameTime = annotation.GameTime,
            Half = annotation.Half,
            GameTimeSeconds = annotation.GameTimeSeconds,
            Label = annotation.Label,
            Team = annotation.Team,
            Position = annotation.Position,
            Visibility = annotation.Visibility.ToString()
        };
    }

    public static UserResponse ToUserResponse(User user)
    {
        return UserResponse.FromUser(user);
    }

    public static DetectionResponse ToDetectionResponse(Detection detection)
    {
        return new DetectionResponse
        {
            Id = detection.Id,
            ProcessingJobId = detection.ProcessingJobId,
            VideoId = detection.VideoId,
            FrameIndex = detection.FrameIndex,
            TimestampSeconds = detection.TimestampSeconds,
            Label = detection.Label,
            Confidence = detection.Confidence,
            X1 = detection.X1,
            Y1 = detection.Y1,
            X2 = detection.X2,
            Y2 = detection.Y2,
            CreatedAt = detection.CreatedAt
        };
    }

    public static AuditLogResponse ToAuditLogResponse(AuditLog auditLog)
    {
        return new AuditLogResponse
        {
            Id = auditLog.Id,
            ActorUserId = auditLog.ActorUserId,
            ActorName = auditLog.ActorUser?.FullName ?? auditLog.ActorUser?.Username,
            EntityType = auditLog.EntityType.ToString(),
            EntityId = auditLog.EntityId,
            Action = auditLog.Action,
            Status = auditLog.Status,
            Message = auditLog.Message,
            MetadataJson = auditLog.MetadataJson,
            IpAddress = auditLog.IpAddress,
            CreatedAt = auditLog.CreatedAt
        };
    }
}
