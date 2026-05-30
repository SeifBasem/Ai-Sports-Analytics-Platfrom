using SA.Infrastructure;
using SA.Models.Dto.Common;
using SA.Models.Dto.Matches;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class MatchAnalyticsService : IMatchAnalyticsService
{
    private readonly IMatchRepository _matches;

    public MatchAnalyticsService(IMatchRepository matches)
    {
        _matches = matches;
    }

    public async Task<PagedResponse<MatchResponse>> GetMatchesAsync(MatchQueryRequest request, CancellationToken cancellationToken = default)
    {
        var page = await _matches.SearchAsync(request, cancellationToken);
        var annotationCounts = await _matches.CountAnnotationsByMatchIdsAsync(page.Items.Select(match => match.Id), cancellationToken);

        return new PagedResponse<MatchResponse>
        {
            Items = page.Items
                .Select(match => ServiceMapping.ToMatchResponse(
                    match,
                    annotationCounts.TryGetValue(match.Id, out var count) ? count : 0))
                .ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<MatchResponse> GetMatchAsync(int id, CancellationToken cancellationToken = default)
    {
        var match = await _matches.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Match was not found.");

        var counts = await _matches.CountAnnotationsByMatchIdsAsync([match.Id], cancellationToken);
        return ServiceMapping.ToMatchResponse(match, counts.TryGetValue(match.Id, out var count) ? count : 0);
    }

    public async Task<PagedResponse<MatchAnnotationResponse>> GetAnnotationsAsync(int matchId, MatchAnnotationQueryRequest request, CancellationToken cancellationToken = default)
    {
        _ = await _matches.GetByIdAsync(matchId, cancellationToken)
            ?? throw new NotFoundException("Match was not found.");

        var page = await _matches.SearchAnnotationsAsync(matchId, request, cancellationToken);
        return new PagedResponse<MatchAnnotationResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToMatchAnnotationResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<MatchStatSummaryResponse> GetMatchSummaryAsync(int matchId, CancellationToken cancellationToken = default)
    {
        var match = await _matches.GetByIdAsync(matchId, cancellationToken)
            ?? throw new NotFoundException("Match was not found.");

        return new MatchStatSummaryResponse
        {
            MatchId = match.Id,
            HomeTeam = match.HomeTeam,
            AwayTeam = match.AwayTeam,
            Actions = await _matches.GetActionSummaryAsync(matchId, cancellationToken)
        };
    }
}
