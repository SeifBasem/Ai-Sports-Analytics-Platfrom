using SA.Models.Dto.Common;
using SA.Models.Dto.Matches;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IMatchRepository
{
    Task<Match?> GetByIdAsync(int id, CancellationToken cancellationToken = default);
    Task<MatchAnnotation?> GetAnnotationByIdAsync(int matchId, int annotationId, CancellationToken cancellationToken = default);
    Task<bool> ExistsByUrlLocalAsync(string urlLocal, int? excludingId = null, CancellationToken cancellationToken = default);
    Task<PagedResponse<Match>> SearchAsync(MatchQueryRequest request, CancellationToken cancellationToken = default);
    Task<PagedResponse<MatchAnnotation>> SearchAnnotationsAsync(int matchId, MatchAnnotationQueryRequest request, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<ActionCountResponse>> GetActionSummaryAsync(int matchId, CancellationToken cancellationToken = default);
    Task<IReadOnlyDictionary<int, int>> CountAnnotationsByMatchIdsAsync(IEnumerable<int> matchIds, CancellationToken cancellationToken = default);
    Task<int> CountAsync(CancellationToken cancellationToken = default);
    Task AddAsync(Match match, CancellationToken cancellationToken = default);
    Task AddAnnotationAsync(MatchAnnotation annotation, CancellationToken cancellationToken = default);
    void Remove(Match match);
    void RemoveAnnotation(MatchAnnotation annotation);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
