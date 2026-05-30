using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Infrastructure;
using SA.Models.Dto.Heatmaps;
using SA.Models.Entities;

namespace SA.Controllers;

[ApiController]
[Route("api/heatmaps")]
[Authorize]
public sealed class HeatmapsController : ControllerBase
{
    private readonly AppDbContext _db;

    public HeatmapsController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<ActionResult<IReadOnlyList<HeatmapResponse>>> GetHeatmaps(
        [FromQuery] Guid? processingJobId,
        CancellationToken cancellationToken)
    {
        var currentUserId = User.GetRequiredUserId();
        var isAdmin = User.IsAdmin();

        var query = _db.Heatmaps
            .AsNoTracking()
            .Include(h => h.ProcessingJob)
                .ThenInclude(j => j!.Video)
            .AsQueryable();

        if (processingJobId.HasValue)
        {
            query = query.Where(h => h.ProcessingJobId == processingJobId.Value);
        }

        if (!isAdmin)
        {
            query = query.Where(h =>
                h.ProcessingJob != null &&
                (h.ProcessingJob.RequestedByUserId == currentUserId ||
                 (h.ProcessingJob.Video != null && h.ProcessingJob.Video.UploadedByUserId == currentUserId)));
        }

        var rows = await query
            .OrderByDescending(h => h.GeneratedAt)
            .Take(100)
            .Select(h => ToResponse(h))
            .ToListAsync(cancellationToken);

        return Ok(rows);
    }

    [HttpPost("ingest")]
    public async Task<ActionResult<HeatmapResponse>> IngestHeatmap(
        IngestHeatmapRequest request,
        CancellationToken cancellationToken)
    {
        var currentUserId = User.GetRequiredUserId();
        var isAdmin = User.IsAdmin();

        var job = await _db.ProcessingJobs
            .Include(j => j.Video)
            .FirstOrDefaultAsync(j => j.Id == request.ProcessingJobId, cancellationToken)
            ?? throw new NotFoundException("Processing job was not found.");

        if (!isAdmin && job.RequestedByUserId != currentUserId && job.Video?.UploadedByUserId != currentUserId)
        {
            throw new ForbiddenException("You do not have access to this processing job.");
        }

        var heatmap = new Heatmap
        {
            ProjectId = job.ProjectId,
            ProcessingJobId = job.Id,
            TargetType = request.TargetType.Trim(),
            TargetId = request.TargetId.Trim(),
            ImagePath = request.ImagePath.Trim(),
            GeneratedAt = DateTime.UtcNow
        };

        await _db.Heatmaps.AddAsync(heatmap, cancellationToken);
        await _db.SaveChangesAsync(cancellationToken);

        return CreatedAtAction(nameof(GetHeatmaps), new { processingJobId = heatmap.ProcessingJobId }, ToResponse(heatmap));
    }

    private static HeatmapResponse ToResponse(Heatmap heatmap)
    {
        return new HeatmapResponse
        {
            Id = heatmap.Id,
            ProjectId = heatmap.ProjectId,
            ProcessingJobId = heatmap.ProcessingJobId,
            TargetType = heatmap.TargetType,
            TargetId = heatmap.TargetId,
            ImagePath = heatmap.ImagePath,
            GeneratedAt = heatmap.GeneratedAt
        };
    }
}
