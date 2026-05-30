using SA.Infrastructure;
using SA.Models.Dto.Audit;
using SA.Models.Dto.Common;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class AuditLogService : IAuditLogService
{
    private readonly IAuditLogRepository _auditLogs;

    public AuditLogService(IAuditLogRepository auditLogs)
    {
        _auditLogs = auditLogs;
    }

    public async Task<PagedResponse<AuditLogResponse>> GetAuditLogsAsync(AuditLogQueryRequest request, CancellationToken cancellationToken = default)
    {
        if (!string.IsNullOrWhiteSpace(request.EntityType) &&
            !Enum.TryParse<AuditEntityType>(request.EntityType, true, out _))
        {
            throw new ValidationException("Invalid audit entity type.");
        }

        var page = await _auditLogs.SearchAsync(request, cancellationToken);
        return new PagedResponse<AuditLogResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToAuditLogResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }
}
