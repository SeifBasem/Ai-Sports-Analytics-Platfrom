namespace SA.Models.Entities;

/// <summary>
/// Represents a football match sourced from Labels-ball.json.
/// One row per JSON file (UrlLocal acts as a natural unique key).
/// </summary>
public class Match
{
    public int Id { get; set; }

    /// <summary>
    /// Raw path from JSON: "england_efl/2019-2020/2019-10-01 - Blackburn Rovers - Nottingham Forest"
    /// </summary>
    public string UrlLocal { get; set; } = string.Empty;

    public string? UrlYoutube { get; set; }

    /// <summary>
    /// Raw halftime string from JSON, e.g. "1 - 46:04"
    /// </summary>
    public string Halftime { get; set; } = string.Empty;

    /// <summary>Parsed half number (1 or 2) from Halftime field.</summary>
    public int HalfNumber { get; set; }

    /// <summary>Parsed halftime cutoff in total minutes from Halftime field.</summary>
    public int HalftimeMinutes { get; set; }

    /// <summary>Home team name extracted from UrlLocal path segment.</summary>
    public string HomeTeam { get; set; } = string.Empty;

    /// <summary>Away team name extracted from UrlLocal path segment.</summary>
    public string AwayTeam { get; set; } = string.Empty;

    /// <summary>Competition name extracted from UrlLocal, e.g. "England EFL".</summary>
    public string Competition { get; set; } = string.Empty;

    /// <summary>Season string extracted from UrlLocal, e.g. "2019-2020".</summary>
    public string Season { get; set; } = string.Empty;

    /// <summary>Match date parsed from UrlLocal path, e.g. 2019-10-01.</summary>
    public DateOnly? MatchDate { get; set; }

    public DateTime ImportedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ICollection<MatchAnnotation> Annotations { get; set; } = [];
}
