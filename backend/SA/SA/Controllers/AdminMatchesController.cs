using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Matches;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/admin/matches")]
[Authorize(Roles = "Admin")]
public sealed class AdminMatchesController : ControllerBase
{
    private readonly IMatchAnalyticsService _analytics;
    private readonly IMatchManagementService _management;

    public AdminMatchesController(IMatchAnalyticsService analytics, IMatchManagementService management)
    {
        _analytics = analytics;
        _management = management;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<MatchResponse>>> GetMatches([FromQuery] MatchQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _analytics.GetMatchesAsync(request, cancellationToken));
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<MatchResponse>> GetMatch(int id, CancellationToken cancellationToken)
    {
        return Ok(await _analytics.GetMatchAsync(id, cancellationToken));
    }

    [HttpPost]
    public async Task<ActionResult<MatchResponse>> CreateMatch(CreateMatchRequest request, CancellationToken cancellationToken)
    {
        var created = await _management.CreateMatchAsync(request, User.GetRequiredUserId(), cancellationToken);
        return CreatedAtAction(nameof(GetMatch), new { id = created.Id }, created);
    }

    [HttpPut("{id:int}")]
    public async Task<ActionResult<MatchResponse>> UpdateMatch(int id, UpdateMatchRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _management.UpdateMatchAsync(id, request, User.GetRequiredUserId(), cancellationToken));
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteMatch(int id, CancellationToken cancellationToken)
    {
        await _management.DeleteMatchAsync(id, User.GetRequiredUserId(), cancellationToken);
        return NoContent();
    }

    [HttpGet("{id:int}/annotations")]
    public async Task<ActionResult<PagedResponse<MatchAnnotationResponse>>> GetAnnotations(int id, [FromQuery] MatchAnnotationQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _analytics.GetAnnotationsAsync(id, request, cancellationToken));
    }

    [HttpPost("{id:int}/annotations")]
    public async Task<ActionResult<MatchAnnotationResponse>> AddAnnotation(int id, CreateMatchAnnotationRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _management.AddAnnotationAsync(id, request, User.GetRequiredUserId(), cancellationToken));
    }

    [HttpPut("{matchId:int}/annotations/{annotationId:int}")]
    public async Task<ActionResult<MatchAnnotationResponse>> UpdateAnnotation(int matchId, int annotationId, UpdateMatchAnnotationRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _management.UpdateAnnotationAsync(matchId, annotationId, request, User.GetRequiredUserId(), cancellationToken));
    }

    [HttpDelete("{matchId:int}/annotations/{annotationId:int}")]
    public async Task<IActionResult> DeleteAnnotation(int matchId, int annotationId, CancellationToken cancellationToken)
    {
        await _management.DeleteAnnotationAsync(matchId, annotationId, User.GetRequiredUserId(), cancellationToken);
        return NoContent();
    }
}
