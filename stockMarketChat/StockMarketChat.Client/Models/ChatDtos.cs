namespace StockMarketChat.Client.Models;

public sealed class ChatMessageDto
{
    public string Role { get; set; } = "user";
    public string Content { get; set; } = string.Empty;
    public DateTimeOffset Timestamp { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class ChatRequest
{
    public string Message { get; set; } = string.Empty;
    public List<ChatMessageDto> History { get; set; } = [];
}

public sealed class ChatResponse
{
    public string Reply { get; set; } = string.Empty;
    public string Provider { get; set; } = "demo";
    public bool Success { get; set; } = true;
    public string? Error { get; set; }
}
