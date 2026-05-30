using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Models.Dto.Audit;
using SA.Models.Dto.Common;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/admin/audit-logs")]
[Authorize(Roles = "Admin")]
public sealed class AdminAuditLogsController : ControllerBase
{
    private readonly IAuditLogService _auditLogs;

    public AdminAuditLogsController(IAuditLogService auditLogs)
    {
        _auditLogs = auditLogs;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<AuditLogResponse>>> GetAuditLogs([FromQuery] AuditLogQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _auditLogs.GetAuditLogsAsync(request, cancellationToken));
    }
}
