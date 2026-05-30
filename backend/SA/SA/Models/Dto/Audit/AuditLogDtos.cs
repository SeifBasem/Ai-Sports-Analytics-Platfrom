using SA.Models.Dto.Common;

namespace SA.Models.Dto.Audit;

public sealed class AuditLogQueryRequest : PagedRequest
{
    public string? EntityType { get; set; }
    public string? EntityId { get; set; }
    public Guid? ActorUserId { get; set; }
    public DateTime? CreatedFrom { get; set; }
    public DateTime? CreatedTo { get; set; }
}

public sealed class AuditLogResponse
{
    public Guid Id { get; set; }
    public Guid? ActorUserId { get; set; }
    public string? ActorName { get; set; }
    public string EntityType { get; set; } = string.Empty;
    public string EntityId { get; set; } = string.Empty;
    public string Action { get; set; } = string.Empty;
    public string? Status { get; set; }
    public string? Message { get; set; }
    public string? MetadataJson { get; set; }
    public string? IpAddress { get; set; }
    public DateTime CreatedAt { get; set; }
}
