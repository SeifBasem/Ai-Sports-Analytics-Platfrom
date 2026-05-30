namespace SA.Services.Auth;

public sealed class JwtSettings
{
    public string Secret { get; set; } = string.Empty;
    public string Issuer { get; set; } = "AI Sports Analytics";
    public string Audience { get; set; } = "AI Sports Analytics Frontend";
    public int AccessTokenMinutes { get; set; } = 30;
    public int RefreshTokenDays { get; set; } = 7;
}
