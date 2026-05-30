using SA.Infrastructure;
using SA.Models.Dto.Matches;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class MatchManagementService : IMatchManagementService
{
    private readonly IMatchRepository _matches;
    private readonly IAuditLogRepository _auditLogs;

    public MatchManagementService(IMatchRepository matches, IAuditLogRepository auditLogs)
    {
        _matches = matches;
        _auditLogs = auditLogs;
    }

    public async Task<MatchResponse> CreateMatchAsync(CreateMatchRequest request, Guid actorUserId, CancellationToken cancellationToken = default)
    {
        await EnsureUrlLocalIsUniqueAsync(request.UrlLocal, excludingId: null, cancellationToken);

        var match = new Match
        {
            UrlLocal = request.UrlLocal.Trim(),
            UrlYoutube = NormalizeNullable(request.UrlYoutube),
            Halftime = request.Halftime.Trim(),
            HalfNumber = request.HalfNumber,
            HalftimeMinutes = request.HalftimeMinutes,
            HomeTeam = request.HomeTeam.Trim(),
            AwayTeam = request.AwayTeam.Trim(),
            Competition = request.Competition.Trim(),
            Season = request.Season.Trim(),
            MatchDate = request.MatchDate,
            ImportedAt = DateTime.UtcNow
        };

        await _matches.AddAsync(match, cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
        await AddAuditLogAsync(actorUserId, AuditEntityType.Match, match.Id.ToString(), "Create", "Succeeded", cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToMatchResponse(match, 0);
    }

    public async Task<MatchResponse> UpdateMatchAsync(int id, UpdateMatchRequest request, Guid actorUserId, CancellationToken cancellationToken = default)
    {
        var match = await _matches.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Match was not found.");

        await EnsureUrlLocalIsUniqueAsync(request.UrlLocal, id, cancellationToken);

        match.UrlLocal = request.UrlLocal.Trim();
        match.UrlYoutube = NormalizeNullable(request.UrlYoutube);
        match.Halftime = request.Halftime.Trim();
        match.HalfNumber = request.HalfNumber;
        match.HalftimeMinutes = request.HalftimeMinutes;
        match.HomeTeam = request.HomeTeam.Trim();
        match.AwayTeam = request.AwayTeam.Trim();
        match.Competition = request.Competition.Trim();
        match.Season = request.Season.Trim();
        match.MatchDate = request.MatchDate;

        await AddAuditLogAsync(actorUserId, AuditEntityType.Match, match.Id.ToString(), "Update", "Succeeded", cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
        var counts = await _matches.CountAnnotationsByMatchIdsAsync([match.Id], cancellationToken);
        return ServiceMapping.ToMatchResponse(match, counts.TryGetValue(match.Id, out var count) ? count : 0);
    }

    public async Task DeleteMatchAsync(int id, Guid actorUserId, CancellationToken cancellationToken = default)
    {
        var match = await _matches.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("Match was not found.");

        _matches.Remove(match);
        await AddAuditLogAsync(actorUserId, AuditEntityType.Match, match.Id.ToString(), "Delete", "Succeeded", cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
    }

    public async Task<MatchAnnotationResponse> AddAnnotationAsync(int matchId, CreateMatchAnnotationRequest request, Guid actorUserId, CancellationToken cancellationToken = default)
    {
        _ = await _matches.GetByIdAsync(matchId, cancellationToken)
            ?? throw new NotFoundException("Match was not found.");

        var annotation = BuildAnnotation(matchId, request);
        await _matches.AddAnnotationAsync(annotation, cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
        await AddAuditLogAsync(actorUserId, AuditEntityType.MatchAnnotation, annotation.Id.ToString(), "Create", "Succeeded", cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToMatchAnnotationResponse(annotation);
    }

    public async Task<MatchAnnotationResponse> UpdateAnnotationAsync(int matchId, int annotationId, UpdateMatchAnnotationRequest request, Guid actorUserId, CancellationToken cancellationToken = default)
    {
        var annotation = await _matches.GetAnnotationByIdAsync(matchId, annotationId, cancellationToken)
            ?? throw new NotFoundException("Match annotation was not found.");

        ApplyAnnotation(annotation, request);
        await AddAuditLogAsync(actorUserId, AuditEntityType.MatchAnnotation, annotation.Id.ToString(), "Update", "Succeeded", cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToMatchAnnotationResponse(annotation);
    }

    public async Task DeleteAnnotationAsync(int matchId, int annotationId, Guid actorUserId, CancellationToken cancellationToken = default)
    {
        var annotation = await _matches.GetAnnotationByIdAsync(matchId, annotationId, cancellationToken)
            ?? throw new NotFoundException("Match annotation was not found.");

        _matches.RemoveAnnotation(annotation);
        await AddAuditLogAsync(actorUserId, AuditEntityType.MatchAnnotation, annotation.Id.ToString(), "Delete", "Succeeded", cancellationToken);
        await _matches.SaveChangesAsync(cancellationToken);
    }

    private async Task EnsureUrlLocalIsUniqueAsync(string urlLocal, int? excludingId, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(urlLocal))
        {
            throw new ValidationException("UrlLocal is required.");
        }

        if (await _matches.ExistsByUrlLocalAsync(urlLocal, excludingId, cancellationToken))
        {
            throw new ConflictException("A match with the same UrlLocal already exists.");
        }
    }

    private static MatchAnnotation BuildAnnotation(int matchId, CreateMatchAnnotationRequest request)
    {
        var annotation = new MatchAnnotation
        {
            MatchId = matchId
        };

        ApplyAnnotation(annotation, request);
        return annotation;
    }

    private static void ApplyAnnotation(MatchAnnotation annotation, CreateMatchAnnotationRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Label))
        {
            throw new ValidationException("Annotation label is required.");
        }

        var team = request.Team.Trim().ToLowerInvariant();
        if (team is not ("left" or "right"))
        {
            throw new ValidationException("Annotation team must be left or right.");
        }

        if (!Enum.TryParse<AnnotationVisibility>(request.Visibility, true, out var visibility))
        {
            throw new ValidationException("Invalid annotation visibility.");
        }

        annotation.GameTime = request.GameTime.Trim();
        annotation.Half = request.Half;
        annotation.GameTimeSeconds = request.GameTimeSeconds;
        annotation.Label = request.Label.Trim();
        annotation.Team = team;
        annotation.Position = request.Position;
        annotation.Visibility = visibility;
    }

    private static string? NormalizeNullable(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    private async Task AddAuditLogAsync(Guid actorUserId, AuditEntityType entityType, string entityId, string action, string status, CancellationToken cancellationToken)
    {
        await _auditLogs.AddAsync(new AuditLog
        {
            ActorUserId = actorUserId,
            EntityType = entityType,
            EntityId = entityId,
            Action = action,
            Status = status,
            CreatedAt = DateTime.UtcNow
        }, cancellationToken);
    }
}
