using SA.Models.Dto.Audit;
using SA.Models.Dto.Common;

namespace SA.Services.Interfaces;

public interface IAuditLogService
{
    Task<PagedResponse<AuditLogResponse>> GetAuditLogsAsync(AuditLogQueryRequest request, CancellationToken cancellationToken = default);
}
