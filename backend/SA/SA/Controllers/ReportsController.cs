using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Reports;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/reports")]
[Authorize]
public sealed class ReportsController : ControllerBase
{
    private readonly IReportService _reports;

    public ReportsController(IReportService reports)
    {
        _reports = reports;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<ReportResponse>>> GetReports([FromQuery] ReportQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _reports.GetReportsAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<ReportResponse>> GetReport(Guid id, CancellationToken cancellationToken)
    {
        return Ok(await _reports.GetReportAsync(id, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpPost]
    public async Task<ActionResult<ReportResponse>> CreateReport(CreateReportRequest request, CancellationToken cancellationToken)
    {
        var created = await _reports.CreateReportAsync(request, User.GetRequiredUserId(), cancellationToken);
        return CreatedAtAction(nameof(GetReport), new { id = created.Id }, created);
    }

    [HttpPut("{id:guid}")]
    public async Task<ActionResult<ReportResponse>> UpdateReport(Guid id, UpdateReportRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _reports.UpdateReportAsync(id, request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> DeleteReport(Guid id, CancellationToken cancellationToken)
    {
        await _reports.DeleteReportAsync(id, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken);
        return NoContent();
    }
}
