using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IProcessingJobRepository
{
    Task<ProcessingJob?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<PagedResponse<ProcessingJob>> SearchAsync(ProcessingJobQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default);
    Task<int> CountAsync(CancellationToken cancellationToken = default);
    Task<int> CountByStatusAsync(string status, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<(string Status, int Count)>> CountGroupedByStatusAsync(CancellationToken cancellationToken = default);
    Task AddAsync(ProcessingJob job, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
