using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Audit;
using SA.Models.Dto.Common;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class AuditLogRepository : IAuditLogRepository
{
    private readonly AppDbContext _db;

    public AuditLogRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<PagedResponse<AuditLog>> SearchAsync(AuditLogQueryRequest request, CancellationToken cancellationToken = default)
    {
        var query = _db.AuditLogs
            .AsNoTracking()
            .Include(log => log.ActorUser)
            .AsQueryable();

        if (!string.IsNullOrWhiteSpace(request.EntityType) &&
            Enum.TryParse<AuditEntityType>(request.EntityType, true, out var entityType))
        {
            query = query.Where(log => log.EntityType == entityType);
        }

        if (!string.IsNullOrWhiteSpace(request.EntityId))
        {
            var entityId = request.EntityId.Trim();
            query = query.Where(log => log.EntityId == entityId);
        }

        if (request.ActorUserId.HasValue)
        {
            query = query.Where(log => log.ActorUserId == request.ActorUserId.Value);
        }

        if (request.CreatedFrom.HasValue)
        {
            query = query.Where(log => log.CreatedAt >= request.CreatedFrom.Value);
        }

        if (request.CreatedTo.HasValue)
        {
            query = query.Where(log => log.CreatedAt <= request.CreatedTo.Value);
        }

        return query
            .OrderByDescending(log => log.CreatedAt)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public async Task AddAsync(AuditLog auditLog, CancellationToken cancellationToken = default)
    {
        await _db.AuditLogs.AddAsync(auditLog, cancellationToken);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
