using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Models.Dto.Common;
using SA.Models.Dto.Users;
using SA.Models.Entities;
using SA.Models.Enums;
using SA.Repositories.Interfaces;

namespace SA.Repositories;

public sealed class UserRepository : IUserRepository
{
    private readonly AppDbContext _db;

    public UserRepository(AppDbContext db)
    {
        _db = db;
    }

    public Task<User?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return _db.Users.FirstOrDefaultAsync(u => u.Id == id, cancellationToken);
    }

    public Task<User?> GetByIdentifierAsync(string identifier, CancellationToken cancellationToken = default)
    {
        var normalized = identifier.Trim().ToLowerInvariant();
        return _db.Users.FirstOrDefaultAsync(
            u => u.Username.ToLower() == normalized || u.Email.ToLower() == normalized,
            cancellationToken);
    }

    public Task<User?> GetByRefreshTokenHashAsync(string refreshTokenHash, CancellationToken cancellationToken = default)
    {
        return _db.Users.FirstOrDefaultAsync(
            u => u.RefreshTokenHash == refreshTokenHash &&
                 u.RefreshTokenExpiresAt > DateTime.UtcNow &&
                 u.IsActive,
            cancellationToken);
    }

    public Task<bool> ExistsByUsernameOrEmailAsync(string username, string email, Guid? excludingUserId = null, CancellationToken cancellationToken = default)
    {
        var normalizedUsername = username.Trim().ToLowerInvariant();
        var normalizedEmail = email.Trim().ToLowerInvariant();

        return _db.Users.AnyAsync(u =>
            (!excludingUserId.HasValue || u.Id != excludingUserId.Value) &&
            (u.Username.ToLower() == normalizedUsername || u.Email.ToLower() == normalizedEmail),
            cancellationToken);
    }

    public Task<PagedResponse<User>> SearchAsync(UserQueryRequest request, CancellationToken cancellationToken = default)
    {
        var query = _db.Users.AsNoTracking().AsQueryable();

        if (!string.IsNullOrWhiteSpace(request.Search))
        {
            var search = request.Search.Trim().ToLowerInvariant();
            query = query.Where(u =>
                u.Username.ToLower().Contains(search) ||
                u.Email.ToLower().Contains(search) ||
                u.FullName.ToLower().Contains(search));
        }

        if (request.IsActive.HasValue)
        {
            query = query.Where(u => u.IsActive == request.IsActive.Value);
        }

        if (!string.IsNullOrWhiteSpace(request.Role) &&
            Enum.TryParse<UserRole>(request.Role, true, out var role))
        {
            query = query.Where(u => u.Role == role);
        }

        return query
            .OrderByDescending(u => u.CreatedAt)
            .ToPagedResponseAsync(request, cancellationToken);
    }

    public Task<int> CountAsync(CancellationToken cancellationToken = default)
    {
        return _db.Users.CountAsync(cancellationToken);
    }

    public Task<int> CountActiveAsync(CancellationToken cancellationToken = default)
    {
        return _db.Users.CountAsync(u => u.IsActive, cancellationToken);
    }

    public async Task AddAsync(User user, CancellationToken cancellationToken = default)
    {
        await _db.Users.AddAsync(user, cancellationToken);
    }

    public Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        return _db.SaveChangesAsync(cancellationToken);
    }
}
