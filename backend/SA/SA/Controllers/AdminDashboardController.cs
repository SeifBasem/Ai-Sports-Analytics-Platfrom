using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Models.Dto.Analytics;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/admin/dashboard")]
[Authorize(Roles = "Admin")]
public sealed class AdminDashboardController : ControllerBase
{
    private readonly IAdminDashboardService _dashboard;

    public AdminDashboardController(IAdminDashboardService dashboard)
    {
        _dashboard = dashboard;
    }

    [HttpGet]
    public async Task<ActionResult<AdminDashboardResponse>> GetDashboard(CancellationToken cancellationToken)
    {
        return Ok(await _dashboard.GetDashboardAsync(cancellationToken));
    }
}
