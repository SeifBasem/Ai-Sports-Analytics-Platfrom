using SA.Models.Dto.Common;
using SA.Models.Dto.Reports;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IReportRepository
{
    Task<Report?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<PagedResponse<Report>> SearchAsync(ReportQueryRequest request, bool includeAllUsers, Guid currentUserId, CancellationToken cancellationToken = default);
    Task<int> CountAsync(CancellationToken cancellationToken = default);
    Task AddAsync(Report report, CancellationToken cancellationToken = default);
    void Remove(Report report);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
