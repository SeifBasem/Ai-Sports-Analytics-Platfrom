using SA.Models.Dto.Analytics;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class AdminDashboardService : IAdminDashboardService
{
    private readonly IUserRepository _users;
    private readonly IVideoRepository _videos;
    private readonly IProcessingJobRepository _jobs;
    private readonly IReportRepository _reports;
    private readonly IMatchRepository _matches;
    private readonly IJobStatisticRepository _statistics;

    public AdminDashboardService(
        IUserRepository users,
        IVideoRepository videos,
        IProcessingJobRepository jobs,
        IReportRepository reports,
        IMatchRepository matches,
        IJobStatisticRepository statistics)
    {
        _users = users;
        _videos = videos;
        _jobs = jobs;
        _reports = reports;
        _matches = matches;
        _statistics = statistics;
    }

    public async Task<AdminDashboardResponse> GetDashboardAsync(CancellationToken cancellationToken = default)
    {
        var jobStatuses = await _jobs.CountGroupedByStatusAsync(cancellationToken);
        var videoStatuses = await _videos.CountByStatusAsync(cancellationToken);

        return new AdminDashboardResponse
        {
            TotalUsers = await _users.CountAsync(cancellationToken),
            ActiveUsers = await _users.CountActiveAsync(cancellationToken),
            TotalVideos = await _videos.CountAsync(cancellationToken),
            ProcessingJobs = await _jobs.CountAsync(cancellationToken),
            CompletedJobs = await _jobs.CountByStatusAsync("Completed", cancellationToken),
            FailedJobs = await _jobs.CountByStatusAsync("Failed", cancellationToken),
            Reports = await _reports.CountAsync(cancellationToken),
            Matches = await _matches.CountAsync(cancellationToken),
            StoredStatistics = await _statistics.CountAsync(cancellationToken),
            JobStatusCounts = jobStatuses.Select(row => new StatusCountResponse { Status = row.Status, Count = row.Count }).ToList(),
            VideoStatusCounts = videoStatuses.Select(row => new StatusCountResponse { Status = row.Status, Count = row.Count }).ToList()
        };
    }
}
