using SA.Models.Dto.Common;
using SA.Models.Dto.Reports;

namespace SA.Services.Interfaces;

public interface IReportService
{
    Task<PagedResponse<ReportResponse>> GetReportsAsync(ReportQueryRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<ReportResponse> GetReportAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task<ReportResponse> CreateReportAsync(CreateReportRequest request, Guid currentUserId, CancellationToken cancellationToken = default);
    Task<ReportResponse> UpdateReportAsync(Guid id, UpdateReportRequest request, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
    Task DeleteReportAsync(Guid id, Guid currentUserId, bool isAdmin, CancellationToken cancellationToken = default);
}
