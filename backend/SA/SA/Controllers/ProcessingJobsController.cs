using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Jobs;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/processing-jobs")]
[Authorize]
public sealed class ProcessingJobsController : ControllerBase
{
    private readonly IProcessingJobService _jobs;
    private readonly IJobStatisticService _statistics;

    public ProcessingJobsController(IProcessingJobService jobs, IJobStatisticService statistics)
    {
        _jobs = jobs;
        _statistics = statistics;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<ProcessingJobResponse>>> GetJobs([FromQuery] ProcessingJobQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _jobs.GetJobsAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<ProcessingJobResponse>> GetJob(Guid id, CancellationToken cancellationToken)
    {
        return Ok(await _jobs.GetJobAsync(id, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpPost]
    public async Task<ActionResult<ProcessingJobResponse>> CreateJob(CreateProcessingJobRequest request, CancellationToken cancellationToken)
    {
        var created = await _jobs.CreateJobAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken);
        return CreatedAtAction(nameof(GetJob), new { id = created.Id }, created);
    }

    [HttpPatch("{id:guid}/status")]
    public async Task<ActionResult<ProcessingJobResponse>> UpdateStatus(Guid id, UpdateProcessingJobStatusRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _jobs.UpdateStatusAsync(id, request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpPost("{id:guid}/statistics")]
    public async Task<ActionResult<JobStatisticResponse>> AddStatistic(Guid id, CreateJobStatisticRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _statistics.AddStatisticAsync(id, request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpPost("{id:guid}/statistics/batch")]
    public async Task<ActionResult<IReadOnlyList<JobStatisticResponse>>> AddStatistics(Guid id, CreateJobStatisticsBatchRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _statistics.AddStatisticsAsync(id, request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }
}
