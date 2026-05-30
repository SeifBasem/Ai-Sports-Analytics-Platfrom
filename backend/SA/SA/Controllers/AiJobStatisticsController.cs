using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Jobs;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/ai/job-statistics")]
[Authorize]
public sealed class AiJobStatisticsController : ControllerBase
{
    private readonly IJobStatisticService _statistics;

    public AiJobStatisticsController(IJobStatisticService statistics)
    {
        _statistics = statistics;
    }

    [HttpPost("ingest")]
    public async Task<ActionResult<ProcessingJobResponse>> Ingest(AiJobStatisticsIngestRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _statistics.IngestAiJobStatisticsAsync(request, User.GetRequiredUserId(), cancellationToken));
    }
}
