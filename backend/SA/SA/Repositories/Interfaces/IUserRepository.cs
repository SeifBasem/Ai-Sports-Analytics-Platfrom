using SA.Models.Dto.Common;
using SA.Models.Dto.Users;
using SA.Models.Entities;

namespace SA.Repositories.Interfaces;

public interface IUserRepository
{
    Task<User?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<User?> GetByIdentifierAsync(string identifier, CancellationToken cancellationToken = default);
    Task<User?> GetByRefreshTokenHashAsync(string refreshTokenHash, CancellationToken cancellationToken = default);
    Task<bool> ExistsByUsernameOrEmailAsync(string username, string email, Guid? excludingUserId = null, CancellationToken cancellationToken = default);
    Task<PagedResponse<User>> SearchAsync(UserQueryRequest request, CancellationToken cancellationToken = default);
    Task<int> CountAsync(CancellationToken cancellationToken = default);
    Task<int> CountActiveAsync(CancellationToken cancellationToken = default);
    Task AddAsync(User user, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
