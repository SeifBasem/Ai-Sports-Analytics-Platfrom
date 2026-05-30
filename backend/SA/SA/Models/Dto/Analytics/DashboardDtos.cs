namespace SA.Models.Dto.Analytics;

public sealed class AdminDashboardResponse
{
    public int TotalUsers { get; set; }
    public int ActiveUsers { get; set; }
    public int TotalVideos { get; set; }
    public int ProcessingJobs { get; set; }
    public int CompletedJobs { get; set; }
    public int FailedJobs { get; set; }
    public int Reports { get; set; }
    public int Matches { get; set; }
    public int StoredStatistics { get; set; }
    public IReadOnlyList<StatusCountResponse> JobStatusCounts { get; set; } = [];
    public IReadOnlyList<StatusCountResponse> VideoStatusCounts { get; set; } = [];
}

public sealed class StatusCountResponse
{
    public string Status { get; set; } = string.Empty;
    public int Count { get; set; }
}
