using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Models.Dto.Common;
using SA.Models.Dto.Matches;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/matches")]
[Authorize]
public sealed class MatchesController : ControllerBase
{
    private readonly IMatchAnalyticsService _matches;

    public MatchesController(IMatchAnalyticsService matches)
    {
        _matches = matches;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<MatchResponse>>> GetMatches([FromQuery] MatchQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _matches.GetMatchesAsync(request, cancellationToken));
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<MatchResponse>> GetMatch(int id, CancellationToken cancellationToken)
    {
        return Ok(await _matches.GetMatchAsync(id, cancellationToken));
    }

    [HttpGet("{id:int}/annotations")]
    public async Task<ActionResult<PagedResponse<MatchAnnotationResponse>>> GetAnnotations(int id, [FromQuery] MatchAnnotationQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _matches.GetAnnotationsAsync(id, request, cancellationToken));
    }

    [HttpGet("{id:int}/summary")]
    public async Task<ActionResult<MatchStatSummaryResponse>> GetSummary(int id, CancellationToken cancellationToken)
    {
        return Ok(await _matches.GetMatchSummaryAsync(id, cancellationToken));
    }
}
