using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;

namespace SA.Services.Interfaces;

public interface IJobStatisticService
{
    Task<PagedResponse<JobStatisticResponse>> GetStatisticsAsync(JobStatisticQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<JobStatisticResponse> AddStatisticAsync(Guid processingJobId, CreateJobStatisticRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<JobStatisticResponse>> AddStatisticsAsync(Guid processingJobId, CreateJobStatisticsBatchRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<ProcessingJobResponse> IngestAiJobStatisticsAsync(AiJobStatisticsIngestRequest request, Guid currentUserId, CancellationToken cancellationToken = default);
}
