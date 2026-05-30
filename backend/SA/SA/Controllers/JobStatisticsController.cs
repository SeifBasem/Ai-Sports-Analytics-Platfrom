using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/job-statistics")]
[Authorize]
public sealed class JobStatisticsController : ControllerBase
{
    private readonly IJobStatisticService _statistics;

    public JobStatisticsController(IJobStatisticService statistics)
    {
        _statistics = statistics;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<JobStatisticResponse>>> GetStatistics([FromQuery] JobStatisticQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _statistics.GetStatisticsAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }
}
