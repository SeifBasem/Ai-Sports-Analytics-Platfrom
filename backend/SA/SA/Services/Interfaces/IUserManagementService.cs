using SA.Models.Dto.Auth;
using SA.Models.Dto.Common;
using SA.Models.Dto.Users;

namespace SA.Services.Interfaces;

public interface IUserManagementService
{
    Task<PagedResponse<UserResponse>> GetUsersAsync(UserQueryRequest request, CancellationToken cancellationToken = default);
    Task<UserResponse> GetUserAsync(Guid id, CancellationToken cancellationToken = default);
    Task<UserResponse> UpdateStatusAsync(Guid id, UpdateUserStatusRequest request, CancellationToken cancellationToken = default);
    Task<UserResponse> UpdateRoleAsync(Guid id, UpdateUserRoleRequest request, CancellationToken cancellationToken = default);
    Task<UserResponse> UpdateUserAsync(Guid id, UpdateUserProfileRequest request, CancellationToken cancellationToken = default);
    Task<UserResponse> UpdateProfileAsync(Guid currentUserId, UpdateUserProfileRequest request, CancellationToken cancellationToken = default);
}
