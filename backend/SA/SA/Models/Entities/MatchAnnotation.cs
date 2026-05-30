using SA.Models.Enums;

namespace SA.Models.Entities;

/// <summary>
/// One ball-action event from the annotations array in Labels-ball.json.
/// ~13,000 rows per match.
/// </summary>
public class MatchAnnotation
{
    public int Id { get; set; }
    public int MatchId { get; set; }

    /// <summary>Raw game time string from JSON, e.g. "1 - 00:34".</summary>
    public string GameTime { get; set; } = string.Empty;

    /// <summary>Parsed half number (1 or 2).</summary>
    public int Half { get; set; }

    /// <summary>Parsed offset within the half in total seconds.</summary>
    public int GameTimeSeconds { get; set; }

    /// <summary>
    /// Action label from JSON. Examples: PASS, DRIVE, SHOT, CROSS,
    /// HEADER, HIGH PASS, OUT, THROW IN, BALL PLAYER BLOCK,
    /// PLAYER SUCCESSFUL TACKLE, etc.
    /// </summary>
    public string Label { get; set; } = string.Empty;

    /// <summary>
    /// Which team performed the action. Values from JSON: "left" or "right".
    /// By convention home team = left, away team = right.
    /// </summary>
    public string Team { get; set; } = string.Empty;

    /// <summary>Raw frame position (milliseconds offset) from JSON.</summary>
    public int Position { get; set; }

    /// <summary>Visibility of the ball at this event.</summary>
    public AnnotationVisibility Visibility { get; set; } = AnnotationVisibility.Visible;

    // Navigation
    public Match? Match { get; set; }
}
