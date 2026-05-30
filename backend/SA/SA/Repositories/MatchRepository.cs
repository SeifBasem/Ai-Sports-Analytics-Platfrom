using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Matches;
using SA.Models.Entities;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class MatchRepository : IMatchRepository
{
    private readonly AppDbContext _db;

    public MatchRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<Match?> GetByIdAsync(int id, CancellationToken cancellationToken = default)
    {
        return _db.Matches
            .FirstOrDefaultAsync(m => m.Id == id, cancellationToken);
    }

    public Task<MatchAnnotation?> GetAnnotationByIdAsync(int matchId, int annotationId, CancellationToken cancellationToken = default)
    {
        return _db.MatchAnnotations
            .FirstOrDefaultAsync(a => a.MatchId == matchId && a.Id == annotationId, cancellationToken);
    }

    public Task<bool> ExistsByUrlLocalAsync(string urlLocal, int? excludingId = null, CancellationToken cancellationToken = default)
    {
        var normalized = urlLocal.Trim().ToLowerInvariant();
        return _db.Matches.AnyAsync(
            m => m.UrlLocal.ToLower() == normalized && (!excludingId.HasValue || m.Id != excludingId.Value),
            cancellationToken);
    }

    public Task<PagedResponse<Match>> SearchAsync(MatchQueryRequest request, CancellationToken cancellationToken = default)
    {
        var query = _db.Matches.AsNoTracking().AsQueryable();

        if (!string.IsNullOrWhiteSpace(request.Search))
        {
            var search = request.Search.Trim().ToLowerInvariant();
            query = query.Where(m =>
                m.HomeTeam.ToLower().Contains(search) ||
                m.AwayTeam.ToLower().Contains(search) ||
                m.Competition.ToLower().Contains(search) ||
                m.Season.ToLower().Contains(search));
        }

        if (!string.IsNullOrWhiteSpace(request.Competition))
        {
            var competition = request.Competition.Trim().ToLowerInvariant();
            query = query.Where(m => m.Competition.ToLower() == competition);
        }

        if (!string.IsNullOrWhiteSpace(request.Season))
        {
            var season = request.Season.Trim().ToLowerInvariant();
            query = query.Where(m => m.Season.ToLower() == season);
        }

        if (request.FromDate.HasValue)
        {
            query = query.Where(m => m.MatchDate >= request.FromDate.Value);
        }

        if (request.ToDate.HasValue)
        {
            query = query.Where(m => m.MatchDate <= request.ToDate.Value);
        }

        return query
            .OrderByDescending(m => m.MatchDate)
            .ThenBy(m => m.HomeTeam)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public Task<PagedResponse<MatchAnnotation>> SearchAnnotationsAsync(int matchId, MatchAnnotationQueryRequest request, CancellationToken cancellationToken = default)
    {
        var query = _db.MatchAnnotations
            .AsNoTracking()
            .Where(a => a.MatchId == matchId);

        if (!string.IsNullOrWhiteSpace(request.Label))
        {
            var label = request.Label.Trim().ToLowerInvariant();
            query = query.Where(a => a.Label.ToLower() == label);
        }

        if (!string.IsNullOrWhiteSpace(request.Team))
        {
            var team = request.Team.Trim().ToLowerInvariant();
            query = query.Where(a => a.Team.ToLower() == team);
        }

        if (request.Half.HasValue)
        {
            query = query.Where(a => a.Half == request.Half.Value);
        }

        return query
            .OrderBy(a => a.Half)
            .ThenBy(a => a.GameTimeSeconds)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public async Task<IReadOnlyList<ActionCountResponse>> GetActionSummaryAsync(int matchId, CancellationToken cancellationToken = default)
    {
        var rows = await _db.MatchAnnotations
            .AsNoTracking()
            .Where(a => a.MatchId == matchId)
            .GroupBy(a => a.Label)
            .Select(g => new
            {
                Label = g.Key,
                HomeCount = g.Count(a => a.Team == "left"),
                AwayCount = g.Count(a => a.Team == "right"),
                TotalCount = g.Count()
            })
            .OrderByDescending(a => a.TotalCount)
            .ToListAsync(cancellationToken);

        return rows.Select(row => new ActionCountResponse
        {
            Label = row.Label,
            HomeCount = row.HomeCount,
            AwayCount = row.AwayCount
        }).ToList();
    }

    public async Task<IReadOnlyDictionary<int, int>> CountAnnotationsByMatchIdsAsync(IEnumerable<int> matchIds, CancellationToken cancellationToken = default)
    {
        var ids = matchIds.Distinct().ToList();
        if (ids.Count == 0)
        {
            return new Dictionary<int, int>();
        }

        var rows = await _db.MatchAnnotations
            .AsNoTracking()
            .Where(a => ids.Contains(a.MatchId))
            .GroupBy(a => a.MatchId)
            .Select(g => new { MatchId = g.Key, Count = g.Count() })
            .ToListAsync(cancellationToken);

        return rows.ToDictionary(row => row.MatchId, row => row.Count);
    }

    public Task<int> CountAsync(CancellationToken cancellationToken = default)
    {
        return _db.Matches.CountAsync(cancellationToken);
    }

    public async Task AddAsync(Match match, CancellationToken cancellationToken = default)
    {
        await _db.Matches.AddAsync(match, cancellationToken);
    }

    public async Task AddAnnotationAsync(MatchAnnotation annotation, CancellationToken cancellationToken = default)
    {
        await _db.MatchAnnotations.AddAsync(annotation, cancellationToken);
    }

    public void Remove(Match match)
    {
        _db.Matches.Remove(match);
    }

    public void RemoveAnnotation(MatchAnnotation annotation)
    {
        _db.MatchAnnotations.Remove(annotation);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
