using System.Security.Claims;

namespace SA.Infrastructure;

public static class ClaimsPrincipalExtensions
{
    public static Guid GetRequiredUserId(this ClaimsPrincipal user)
    {
        var idValue = user.FindFirstValue(AppClaimTypes.NameIdentifier)
            ?? user.FindFirstValue(AppClaimTypes.UserId);
        if (!Guid.TryParse(idValue, out var userId))
        {
            throw new ApiException("Authenticated user id is missing.", StatusCodes.Status401Unauthorized);
        }

        return userId;
    }

    public static bool IsAdmin(this ClaimsPrincipal user)
    {
        return user.IsInRole("Admin");
    }
}
