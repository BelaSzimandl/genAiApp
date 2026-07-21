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

/// <summary>One tape line for the market ticker UI.</summary>
public sealed class TickerItemDto
{
    public string Symbol { get; set; } = string.Empty;
    public string Change { get; set; } = string.Empty;
    public bool Up { get; set; }
    public decimal? Price { get; set; }
    public decimal? ChangePct { get; set; }
}

public sealed class TickerResponse
{
    public List<TickerItemDto> Items { get; set; } = [];
    public DateTimeOffset CachedAt { get; set; }
    public DateTimeOffset ExpiresAt { get; set; }
    public bool FromCache { get; set; }
    public string Source { get; set; } = "cosmos";
}
