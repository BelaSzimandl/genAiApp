namespace GenAiApp.Api.Models;

public sealed class DataRequest
{
    public required string Name { get; init; }

    public string? Message { get; init; }

    public Dictionary<string, string>? Metadata { get; init; }
}

public sealed class DataResponse
{
    public required string Id { get; init; }

    public required string Name { get; init; }

    public string? Message { get; init; }

    public Dictionary<string, string>? Metadata { get; init; }

    public required DateTimeOffset ReceivedAt { get; init; }
}
