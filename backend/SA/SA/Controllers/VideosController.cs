using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Videos;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/videos")]
[Authorize]
public sealed class VideosController : ControllerBase
{
    private readonly IVideoService _videos;

    public VideosController(IVideoService videos)
    {
        _videos = videos;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResponse<VideoResponse>>> GetVideos([FromQuery] VideoQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _videos.GetVideosAsync(request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<VideoResponse>> GetVideo(Guid id, CancellationToken cancellationToken)
    {
        return Ok(await _videos.GetVideoAsync(id, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpPost]
    public async Task<ActionResult<VideoResponse>> CreateVideo(CreateVideoRecordRequest request, CancellationToken cancellationToken)
    {
        var created = await _videos.CreateVideoAsync(request, User.GetRequiredUserId(), cancellationToken);
        return CreatedAtAction(nameof(GetVideo), new { id = created.Id }, created);
    }

    [HttpPut("{id:guid}")]
    public async Task<ActionResult<VideoResponse>> UpdateVideo(Guid id, UpdateVideoRecordRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _videos.UpdateVideoAsync(id, request, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken));
    }

    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> DeleteVideo(Guid id, CancellationToken cancellationToken)
    {
        await _videos.DeleteVideoAsync(id, User.GetRequiredUserId(), User.IsAdmin(), cancellationToken);
        return NoContent();
    }
}
