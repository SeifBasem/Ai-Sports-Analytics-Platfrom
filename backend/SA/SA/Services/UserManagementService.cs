using SA.Infrastructure;
using SA.Models.Dto.Auth;
using SA.Models.Dto.Common;
using SA.Models.Dto.Users;
using SA.Models.Enums;
using SA.Repositories.Interfaces;
using SA.Services.Interfaces;

namespace SA.Services;

public sealed class UserManagementService : IUserManagementService
{
    private static readonly HashSet<UserRole> AssignableRoles = [UserRole.Admin, UserRole.User];
    private readonly IUserRepository _users;

    public UserManagementService(IUserRepository users)
    {
        _users = users;
    }

    public async Task<PagedResponse<UserResponse>> GetUsersAsync(UserQueryRequest request, CancellationToken cancellationToken = default)
    {
        var page = await _users.SearchAsync(request, cancellationToken);
        return new PagedResponse<UserResponse>
        {
            Items = page.Items.Select(ServiceMapping.ToUserResponse).ToList(),
            Page = page.Page,
            PageSize = page.PageSize,
            TotalCount = page.TotalCount
        };
    }

    public async Task<UserResponse> GetUserAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var user = await _users.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        return ServiceMapping.ToUserResponse(user);
    }

    public async Task<UserResponse> UpdateStatusAsync(Guid id, UpdateUserStatusRequest request, CancellationToken cancellationToken = default)
    {
        var user = await _users.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        user.IsActive = request.IsActive;
        user.UpdatedAt = DateTime.UtcNow;
        await _users.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToUserResponse(user);
    }

    public async Task<UserResponse> UpdateRoleAsync(Guid id, UpdateUserRoleRequest request, CancellationToken cancellationToken = default)
    {
        if (!Enum.TryParse<UserRole>(request.Role, true, out var role) || !AssignableRoles.Contains(role))
        {
            throw new ValidationException("Role must be Admin or User.");
        }

        var user = await _users.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        user.Role = role;
        user.UpdatedAt = DateTime.UtcNow;
        await _users.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToUserResponse(user);
    }

    public async Task<UserResponse> UpdateUserAsync(Guid id, UpdateUserProfileRequest request, CancellationToken cancellationToken = default)
    {
        var user = await _users.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        var email = request.Email.Trim().ToLowerInvariant();
        if (await _users.ExistsByUsernameOrEmailAsync(user.Username, email, id, cancellationToken))
        {
            throw new ConflictException("Email is already in use.");
        }

        user.Email = email;
        user.FullName = request.FullName.Trim();
        user.UpdatedAt = DateTime.UtcNow;
        await _users.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToUserResponse(user);
    }

    public async Task<UserResponse> UpdateProfileAsync(Guid currentUserId, UpdateUserProfileRequest request, CancellationToken cancellationToken = default)
    {
        var user = await _users.GetByIdAsync(currentUserId, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        var email = request.Email.Trim().ToLowerInvariant();
        if (await _users.ExistsByUsernameOrEmailAsync(user.Username, email, currentUserId, cancellationToken))
        {
            throw new ConflictException("Email is already in use.");
        }

        user.Email = email;
        user.FullName = request.FullName.Trim();
        user.UpdatedAt = DateTime.UtcNow;
        await _users.SaveChangesAsync(cancellationToken);
        return ServiceMapping.ToUserResponse(user);
    }
}
