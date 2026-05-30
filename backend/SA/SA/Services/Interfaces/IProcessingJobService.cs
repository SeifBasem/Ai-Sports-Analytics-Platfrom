using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;

namespace SA.Services.Interfaces;

public interface IProcessingJobService
{
    Task<PagedResponse<ProcessingJobResponse>> GetJobsAsync(ProcessingJobQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<ProcessingJobResponse> GetJobAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<ProcessingJobResponse> CreateJobAsync(CreateProcessingJobRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<ProcessingJobResponse> UpdateStatusAsync(Guid id, UpdateProcessingJobStatusRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
}
