using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SA.Data;
using SA.Infrastructure;
using SA.Models.Dto.Settings;
using SA.Models.Entities;

namespace SA.Controllers;

[ApiController]
[Route("api/settings")]
[Authorize]
public sealed class SettingsController : ControllerBase
{
    private readonly AppDbContext _db;

    public SettingsController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<ActionResult<UserSettingsResponse>> GetSettings(CancellationToken cancellationToken)
    {
        var userId = User.GetRequiredUserId();
        var user = await _db.Users
            .Include(u => u.Settings)
            .FirstOrDefaultAsync(u => u.Id == userId, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        var settings = await EnsureSettingsAsync(user, cancellationToken);
        await _db.SaveChangesAsync(cancellationToken);
        return Ok(ToResponse(user, settings));
    }

    [HttpPut]
    public async Task<ActionResult<UserSettingsResponse>> UpdateSettings(
        UpdateUserSettingsRequest request,
        CancellationToken cancellationToken)
    {
        var userId = User.GetRequiredUserId();
        var user = await _db.Users
            .Include(u => u.Settings)
            .FirstOrDefaultAsync(u => u.Id == userId, cancellationToken)
            ?? throw new NotFoundException("User was not found.");

        var email = request.Email.Trim().ToLowerInvariant();
        var emailInUse = await _db.Users.AnyAsync(
            u => u.Id != userId && u.Email == email,
            cancellationToken);
        if (emailInUse)
        {
            throw new ConflictException("Email is already in use.");
        }

        user.FullName = request.FullName.Trim();
        user.Email = email;
        user.UpdatedAt = DateTime.UtcNow;

        var settings = await EnsureSettingsAsync(user, cancellationToken);
        settings.ThemeMode = request.ThemeMode.Trim().ToLowerInvariant();
        settings.StartPage = request.StartPage.Trim();
        settings.ConfidenceThreshold = request.ConfidenceThreshold;
        settings.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(cancellationToken);
        return Ok(ToResponse(user, settings));
    }

    private async Task<UserSetting> EnsureSettingsAsync(User user, CancellationToken cancellationToken)
    {
        if (user.Settings is not null)
        {
            if (string.IsNullOrWhiteSpace(user.Settings.ThemeMode))
            {
                user.Settings.ThemeMode = "dark";
            }

            if (string.IsNullOrWhiteSpace(user.Settings.StartPage))
            {
                user.Settings.StartPage = "/dashboard";
            }

            return user.Settings;
        }

        var settings = new UserSetting
        {
            UserId = user.Id,
            User = user,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _db.UserSettings.AddAsync(settings, cancellationToken);
        user.Settings = settings;
        return settings;
    }

    private static UserSettingsResponse ToResponse(User user, UserSetting settings)
    {
        return new UserSettingsResponse
        {
            FullName = user.FullName,
            Email = user.Email,
            Username = user.Username,
            ThemeMode = string.IsNullOrWhiteSpace(settings.ThemeMode) ? "dark" : settings.ThemeMode,
            StartPage = string.IsNullOrWhiteSpace(settings.StartPage) ? "/dashboard" : settings.StartPage,
            ConfidenceThreshold = settings.ConfidenceThreshold,
            UpdatedAt = settings.UpdatedAt
        };
    }
}
