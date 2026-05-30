using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Detections;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/detections")]
[Authorize]
public sealed class DetectionsController : ControllerBase
{
    private readonly IDetectionService _detections;

    public DetectionsController(IDetectionService detections)
    {
        _detections = detections;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<DetectionResponse>>> GetDetections([FromQuery] DetectionQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _detections.GetDetectionsAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<DetectionResponse>> GetDetection(Guid id, CancellationToken cancellationToken)
    {
        return Ok(await _detections.GetDetectionAsync(id, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpPost]
    public async Task<ActionResult<DetectionResponse>> CreateDetection(CreateDetectionRequest request, CancellationToken cancellationToken)
    {
        var created = await _detections.CreateDetectionAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken);
        return CreatedAtAction(nameof(GetDetection), new { id = created.Id }, created);
    }

    [HttpPost("batch")]
    public async Task<ActionResult<IReadOnlyList<DetectionResponse>>> CreateDetections(CreateDetectionBatchRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _detections.CreateDetectionsAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }
}
