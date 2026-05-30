using SA.Models.Dto.Common;
using System.ComponentModel.DataAnnotations;

namespace SA.Models.Dto.Matches;

public sealed class MatchQueryRequest : PagedRequest
{
    public string? Search { get; set; }
    public string? Competition { get; set; }
    public string? Season { get; set; }
    public DateOnly? FromDate { get; set; }
    public DateOnly? ToDate { get; set; }
}

public sealed class MatchAnnotationQueryRequest : PagedRequest
{
    public string? Label { get; set; }
    public string? Team { get; set; }
    public int? Half { get; set; }
}

public class CreateMatchRequest
{
    [Required]
    [MaxLength(500)]
    public string UrlLocal { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? UrlYoutube { get; set; }

    [Required]
    [MaxLength(20)]
    public string Halftime { get; set; } = string.Empty;

    [Range(1, 2)]
    public int HalfNumber { get; set; }

    [Range(0, 200)]
    public int HalftimeMinutes { get; set; }

    [Required]
    [MaxLength(120)]
    public string HomeTeam { get; set; } = string.Empty;

    [Required]
    [MaxLength(120)]
    public string AwayTeam { get; set; } = string.Empty;

    [Required]
    [MaxLength(120)]
    public string Competition { get; set; } = string.Empty;

    [Required]
    [MaxLength(20)]
    public string Season { get; set; } = string.Empty;

    public DateOnly? MatchDate { get; set; }
}

public sealed class UpdateMatchRequest : CreateMatchRequest { }

public class CreateMatchAnnotationRequest
{
    [Required]
    [MaxLength(20)]
    public string GameTime { get; set; } = string.Empty;

    [Range(1, 2)]
    public int Half { get; set; }

    [Range(0, 7200)]
    public int GameTimeSeconds { get; set; }

    [Required]
    [MaxLength(60)]
    public string Label { get; set; } = string.Empty;

    [Required]
    [MaxLength(10)]
    public string Team { get; set; } = string.Empty;

    [Range(0, int.MaxValue)]
    public int Position { get; set; }

    public string Visibility { get; set; } = "Visible";
}

public sealed class UpdateMatchAnnotationRequest : CreateMatchAnnotationRequest { }

public sealed class MatchResponse
{
    public int Id { get; set; }
    public string UrlLocal { get; set; } = string.Empty;
    public string? UrlYoutube { get; set; }
    public string Halftime { get; set; } = string.Empty;
    public int HalfNumber { get; set; }
    public int HalftimeMinutes { get; set; }
    public string HomeTeam { get; set; } = string.Empty;
    public string AwayTeam { get; set; } = string.Empty;
    public string Competition { get; set; } = string.Empty;
    public string Season { get; set; } = string.Empty;
    public DateOnly? MatchDate { get; set; }
    public DateTime ImportedAt { get; set; }
    public int AnnotationCount { get; set; }
}

public sealed class MatchAnnotationResponse
{
    public int Id { get; set; }
    public int MatchId { get; set; }
    public string GameTime { get; set; } = string.Empty;
    public int Half { get; set; }
    public int GameTimeSeconds { get; set; }
    public string Label { get; set; } = string.Empty;
    public string Team { get; set; } = string.Empty;
    public int Position { get; set; }
    public string Visibility { get; set; } = string.Empty;
}

public sealed class MatchStatSummaryResponse
{
    public int MatchId { get; set; }
    public string HomeTeam { get; set; } = string.Empty;
    public string AwayTeam { get; set; } = string.Empty;
    public IReadOnlyList<ActionCountResponse> Actions { get; set; } = [];
}

public sealed class ActionCountResponse
{
    public string Label { get; set; } = string.Empty;
    public int HomeCount { get; set; }
    public int AwayCount { get; set; }
    public int TotalCount => HomeCount + AwayCount;
}
