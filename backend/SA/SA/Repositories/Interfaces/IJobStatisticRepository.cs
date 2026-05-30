using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IJobStatisticRepository
{
    Task<JobStatistic?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<PagedResponse<JobStatistic>> SearchAsync(JobStatisticQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default);
    Task<int> CountAsync(CancellationToken cancellationToken = default);
    Task AddAsync(JobStatistic statistic, CancellationToken cancellationToken = default);
    Task AddRangeAsync(IEnumerable<JobStatistic> statistics, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
