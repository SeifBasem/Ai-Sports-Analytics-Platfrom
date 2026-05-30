namespace SA.Infrastructure;

public class ApiException : Exception
{
    public int StatusCode { get; }

    public ApiException(string message, int statusCode) : base(message)
    {
        StatusCode = statusCode;
    }
}

public sealed class NotFoundException : ApiException
{
    public NotFoundException(string message) : base(message, StatusCodes.Status404NotFound) { }
}

public sealed class ForbiddenException : ApiException
{
    public ForbiddenException(string message) : base(message, StatusCodes.Status403Forbidden) { }
}

public sealed class ConflictException : ApiException
{
    public ConflictException(string message) : base(message, StatusCodes.Status409Conflict) { }
}

public sealed class ValidationException : ApiException
{
    public ValidationException(string message) : base(message, StatusCodes.Status400BadRequest) { }
}
