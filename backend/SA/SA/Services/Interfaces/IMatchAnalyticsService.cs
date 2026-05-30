using SA.Models.Dto.Common;
using SA.Models.Dto.Matches;

namespace SA.Services.Interfaces;

public interface IMatchAnalyticsService
{
    Task<PagedResponse<MatchResponse>> GetMatchesAsync(MatchQueryRequest request, CancellationToken cancellationToken = default);
    Task<MatchResponse> GetMatchAsync(int id, CancellationToken cancellationToken = default);
    Task<PagedResponse<MatchAnnotationResponse>> GetAnnotationsAsync(int matchId, MatchAnnotationQueryRequest request, CancellationToken cancellationToken = default);
    Task<MatchStatSummaryResponse> GetMatchSummaryAsync(int matchId, CancellationToken cancellationToken = default);
}
