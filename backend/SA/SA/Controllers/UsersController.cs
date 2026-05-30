using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Infrastructure;
using SA.Models.Dto.Auth;
using SA.Models.Dto.Common;
using SA.Models.Dto.Users;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/users")]
[Authorize]
public sealed class UsersController : ControllerBase
{
    private readonly IUserManagementService _users;

    public UsersController(IUserManagementService users)
    {
        _users = users;
    }

    [HttpGet]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<PagedResponse<UserResponse>>> GetUsers([FromQuery] UserQueryRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _users.GetUsersAsync(request, cancellationToken));
    }

    [HttpGet("{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<UserResponse>> GetUser(Guid id, CancellationToken cancellationToken)
    {
        return Ok(await _users.GetUserAsync(id, cancellationToken));
    }

    [HttpPatch("{id:guid}/status")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<UserResponse>> UpdateStatus(Guid id, UpdateUserStatusRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _users.UpdateStatusAsync(id, request, cancellationToken));
    }

    [HttpPatch("{id:guid}/role")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<UserResponse>> UpdateRole(Guid id, UpdateUserRoleRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _users.UpdateRoleAsync(id, request, cancellationToken));
    }

    [HttpPut("{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<UserResponse>> UpdateUser(Guid id, UpdateUserProfileRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _users.UpdateUserAsync(id, request, cancellationToken));
    }

    [HttpPatch("me")]
    public async Task<ActionResult<UserResponse>> UpdateProfile(UpdateUserProfileRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _users.UpdateProfileAsync(User.GetRequiredUserId(), request, cancellationToken));
    }
}
