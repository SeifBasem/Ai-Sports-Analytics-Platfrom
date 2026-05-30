using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SA.Models.Dto.Auth;
using SA.Services.Interfaces;

namespace SA.Controllers;

[ApiController]
[Route("api/auth")]
public sealed class AuthController : ControllerBase
{
    private readonly IAuthService _authService;

    public AuthController(IAuthService authService)
    {
        _authService = authService;
    }

    [HttpPost("register")]
    public async Task<ActionResult<AuthResponse>> Register(RegisterRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _authService.RegisterAsync(request, cancellationToken));
    }

    [HttpPost("login")]
    public async Task<ActionResult<AuthResponse>> Login(LoginRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _authService.LoginAsync(request, cancellationToken));
    }

    [HttpPost("refresh")]
    public async Task<ActionResult<AuthResponse>> Refresh(RefreshTokenRequest request, CancellationToken cancellationToken)
    {
        return Ok(await _authService.RefreshAsync(request, cancellationToken));
    }

    [HttpPost("logout")]
    public async Task<ActionResult<ApiMessageResponse>> Logout(LogoutRequest? request, CancellationToken cancellationToken)
    {
        await _authService.LogoutAsync(User, request, cancellationToken);
        return Ok(new ApiMessageResponse { Success = true, Message = "Logged out." });
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<ActionResult<UserResponse>> Me(CancellationToken cancellationToken)
    {
        return Ok(await _authService.GetCurrentUserAsync(User, cancellationToken));
    }
}
