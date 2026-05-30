namespace SA.Models.Dto.Common;

public class PagedRequest
{
    public int Page { get; set; } = 1;
    public int PageSize { get; set; } = 20;

    public int Skip => (NormalizePage(Page) - 1) * NormalizePageSize(PageSize);
    public int Take => NormalizePageSize(PageSize);

    private static int NormalizePage(int page) => page < 1 ? 1 : page;
    private static int NormalizePageSize(int pageSize) => pageSize switch
    {
        < 1 => 20,
        > 100 => 100,
        _ => pageSize
    };
}
