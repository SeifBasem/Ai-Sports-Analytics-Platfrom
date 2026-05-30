using SA.Models.Dto.Analytics;

namespace SA.Services.Interfaces;

public interface IAdminDashboardService
{
    Task<AdminDashboardResponse> GetDashboardAsync(CancellationToken cancellationToken = default);
}
