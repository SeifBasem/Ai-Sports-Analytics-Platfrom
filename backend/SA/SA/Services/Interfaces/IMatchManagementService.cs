using SA.Models.Dto.Matches;

namespace SA.Services.Interfaces;

public interface IMatchManagementService
{
    Task<MatchResponse> CreateMatchAsync(CreateMatchRequest request, Guid actorUserId, CancellationToken cancellationToken = default);
    Task<MatchResponse> UpdateMatchAsync(int id, UpdateMatchRequest request, Guid actorUserId, CancellationToken cancellationToken = default);
    Task DeleteMatchAsync(int id, Guid actorUserId, CancellationToken cancellationToken = default);
    Task<MatchAnnotationResponse> AddAnnotationAsync(int matchId, CreateMatchAnnotationRequest request, Guid actorUserId, CancellationToken cancellationToken = default);
    Task<MatchAnnotationResponse> UpdateAnnotationAsync(int matchId, int annotationId, UpdateMatchAnnotationRequest request, Guid actorUserId, CancellationToken cancellationToken = default);
    Task DeleteAnnotationAsync(int matchId, int annotationId, Guid actorUserId, CancellationToken cancellationToken = default);
}
