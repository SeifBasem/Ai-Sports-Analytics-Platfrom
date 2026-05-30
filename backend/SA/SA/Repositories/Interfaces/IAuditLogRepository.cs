using SA.Models.Dto.Audit;
using SA.Models.Dto.Common;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IAuditLogRepository
{
    Task<PagedResponse<AuditLog>> SearchAsync(AuditLogQueryRequest request, CancellationToken cancellationToken = default);
    Task AddAsync(AuditLog auditLog, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
