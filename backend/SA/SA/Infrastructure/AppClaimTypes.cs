using System.Security.Claims;

namespace SA.Infrastructure;

public static class AppClaimTypes
{
    public const string UserId = "user_id";
    public const string Username = "username";
    public const string FullName = "full_name";
    public const string TokenUse = "token_use";
    public const string AccessTokenUse = "access";

    public const string NameIdentifier = ClaimTypes.NameIdentifier;
    public const string Name = ClaimTypes.Name;
    public const string Email = ClaimTypes.Email;
    public const string Role = ClaimTypes.Role;
}
