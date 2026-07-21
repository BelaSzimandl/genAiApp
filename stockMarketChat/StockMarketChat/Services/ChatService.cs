using System.ClientModel;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Azure.Core;
using Azure.Identity;
using OpenAI;
using OpenAI.Chat;
using StockMarketChat.Client.Models;

namespace StockMarketChat.Services;

public sealed class ChatService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    private readonly IConfiguration _config;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<ChatService> _logger;

    public ChatService(
        IConfiguration config,
        IHttpClientFactory httpClientFactory,
        ILogger<ChatService> logger)
    {
        _config = config;
        _httpClientFactory = httpClientFactory;
        _logger = logger;
    }

    public async Task<ChatResponse> SendAsync(ChatRequest request, CancellationToken cancellationToken = default)
    {
        var message = request.Message?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(message))
        {
            return new ChatResponse
            {
                Success = false,
                Error = "Message is required.",
                Reply = "Please enter a market question first."
            };
        }

        var provider = (_config["Chat:Provider"] ?? "Auto").Trim();
        var history = request.History ?? [];

        try
        {
            if (IsProvider(provider, "Foundry") || (IsProvider(provider, "Auto") && HasFoundryConfig()))
            {
                try
                {
                    var reply = await InvokeFoundryAgentAsync(message, history, cancellationToken);
                    return new ChatResponse { Reply = reply, Provider = "foundry", Success = true };
                }
                catch (Exception foundryEx) when (IsProvider(provider, "Auto"))
                {
                    _logger.LogWarning(foundryEx, "Foundry agent failed; falling back");
                    // Continue to SpaceXAI / demo in Auto mode.
                }
            }

            if (IsProvider(provider, "SpaceXAI") || (IsProvider(provider, "Auto") && HasSpaceXaiKey()))
            {
                var reply = await InvokeSpaceXaiAsync(message, history, cancellationToken);
                return new ChatResponse { Reply = reply, Provider = "spacexai", Success = true };
            }

            if (IsProvider(provider, "Demo") || IsProvider(provider, "Auto"))
            {
                var demo = await BuildDemoReplyAsync(message, cancellationToken);
                return new ChatResponse { Reply = demo, Provider = "demo", Success = true };
            }

            throw new InvalidOperationException(
                $"Chat provider '{provider}' is not available. Configure Foundry, SpaceXAI, or set Chat:Provider=Demo.");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Chat provider failed");
            return new ChatResponse
            {
                Success = false,
                Provider = provider.ToLowerInvariant(),
                Error = ex.Message,
                Reply = $"Markets closed temporarily — chat backend error: {ex.Message}"
            };
        }
    }

    private bool HasFoundryConfig() =>
        !string.IsNullOrWhiteSpace(_config["Chat:Foundry:ProjectEndpoint"]);

    private bool HasSpaceXaiKey() =>
        !string.IsNullOrWhiteSpace(
            _config["Chat:SpaceXAI:ApiKey"] ?? Environment.GetEnvironmentVariable("XAI_API_KEY"));

    private static bool IsProvider(string configured, string name) =>
        string.Equals(configured, name, StringComparison.OrdinalIgnoreCase);

    private async Task<string> InvokeFoundryAgentAsync(
        string message,
        IReadOnlyList<ChatMessageDto> history,
        CancellationToken cancellationToken)
    {
        var endpoint = _config["Chat:Foundry:ProjectEndpoint"]!.TrimEnd('/');
        var agentName = _config["Chat:Foundry:AgentName"] ?? "log-insights-chatbot";
        var model = _config["Chat:Foundry:Model"] ?? "gpt-5-mini";

        var credential = new DefaultAzureCredential();
        var token = await credential.GetTokenAsync(
            new TokenRequestContext(["https://ai.azure.com/.default"]),
            cancellationToken);

        // Build conversational input from recent history + current message.
        var inputItems = new List<object>();
        foreach (var item in history.TakeLast(12))
        {
            if (string.IsNullOrWhiteSpace(item.Content))
            {
                continue;
            }

            var role = item.Role.Equals("assistant", StringComparison.OrdinalIgnoreCase) ? "assistant" : "user";
            inputItems.Add(new
            {
                type = "message",
                role,
                content = item.Content
            });
        }

        inputItems.Add(new
        {
            type = "message",
            role = "user",
            content = message
        });

        var payload = new Dictionary<string, object?>
        {
            ["model"] = model,
            ["input"] = inputItems,
            ["agent"] = new Dictionary<string, string>
            {
                ["name"] = agentName,
                ["type"] = "agent_reference"
            }
        };

        var client = _httpClientFactory.CreateClient(nameof(ChatService));
        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, $"{endpoint}/openai/v1/responses");
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
        httpRequest.Content = new StringContent(
            JsonSerializer.Serialize(payload, JsonOptions),
            Encoding.UTF8,
            "application/json");

        using var response = await client.SendAsync(httpRequest, cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            _logger.LogWarning("Foundry responses API failed ({Status}): {Body}", (int)response.StatusCode, body);
            throw new InvalidOperationException($"Foundry agent call failed ({(int)response.StatusCode}): {Truncate(body, 400)}");
        }

        return ExtractResponseText(body);
    }

    private async Task<string> InvokeSpaceXaiAsync(
        string message,
        IReadOnlyList<ChatMessageDto> history,
        CancellationToken cancellationToken)
    {
        var apiKey = _config["Chat:SpaceXAI:ApiKey"]
            ?? Environment.GetEnvironmentVariable("XAI_API_KEY")
            ?? throw new InvalidOperationException("XAI_API_KEY / Chat:SpaceXAI:ApiKey is not configured.");

        var model = _config["Chat:SpaceXAI:Model"] ?? "grok-4.5";
        var baseUrl = _config["Chat:SpaceXAI:BaseUrl"] ?? "https://api.x.ai/v1";

        var openAi = new OpenAIClient(
            new ApiKeyCredential(apiKey),
            new OpenAIClientOptions { Endpoint = new Uri(baseUrl) });

        var chat = openAi.GetChatClient(model);
        var messages = new List<ChatMessage>
        {
            new SystemChatMessage(
                """
                You are MarketDesk AI, a stock market and exchange assistant.
                Answer only market-related questions: prices, sectors, exchanges, movers, trends.
                Be concise, professional, and use trading-desk language.
                Do not give personalized financial advice; frame insights as informational only.
                If the user goes off-topic, briefly redirect them to market examples.
                """)
        };

        foreach (var item in history.TakeLast(12))
        {
            if (string.IsNullOrWhiteSpace(item.Content))
            {
                continue;
            }

            if (item.Role.Equals("assistant", StringComparison.OrdinalIgnoreCase))
            {
                messages.Add(new AssistantChatMessage(item.Content));
            }
            else
            {
                messages.Add(new UserChatMessage(item.Content));
            }
        }

        messages.Add(new UserChatMessage(message));

        var completion = await chat.CompleteChatAsync(messages, cancellationToken: cancellationToken);
        return completion.Value.Content[0].Text;
    }

    private async Task<string> BuildDemoReplyAsync(string message, CancellationToken cancellationToken)
    {
        var stockApi = _config["Chat:StockQueryApiBaseUrl"]
            ?? "https://stock-query-api-bsz.azurewebsites.net";

        try
        {
            var client = _httpClientFactory.CreateClient(nameof(ChatService));
            var lower = message.ToLowerInvariant();

            // Simple symbol detection: e.g. "AAPL" or "price of MSFT"
            var symbol = ExtractSymbol(message);
            if (symbol is not null)
            {
                var quoteJson = await client.GetStringAsync($"{stockApi.TrimEnd('/')}/stocks/{symbol}", cancellationToken);
                return $"**Demo mode** (wire Foundry or SpaceXAI for the full agent)\n\nLive quote from stock API:\n```json\n{PrettyJson(quoteJson)}\n```\n\nTry: *What is the price of AAPL?* or *Top gainers* after configuring `Chat:Provider`.";
            }

            if (lower.Contains("gainer") || lower.Contains("top") || lower.Contains("nasdaq") || lower.Contains("list"))
            {
                var qs = lower.Contains("nasdaq") ? "?exchange=NASDAQ&limit=5" : "?limit=8";
                var listJson = await client.GetStringAsync($"{stockApi.TrimEnd('/')}/stocks{qs}", cancellationToken);
                return $"**Demo mode** — sample book from Cosmos-backed API:\n```json\n{PrettyJson(Truncate(listJson, 1800))}\n```\n\nConfigure **Foundry** (`log-insights-chatbot`) or **SpaceXAI** for natural-language answers.";
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Demo stock API lookup failed");
        }

        return
            """
            **MarketDesk AI — demo mode**

            The chat UI is live. Backend providers are not fully configured yet.

            Configure one of:
            1. **Foundry agent** (your `log-insights-chatbot`) — set `Chat:Provider` = `Foundry` and `Chat:Foundry:ProjectEndpoint`, then `az login`
            2. **SpaceXAI** — set `XAI_API_KEY` and `Chat:Provider` = `SpaceXAI`

            In-scope questions once connected:
            - What is the price of AAPL?
            - Show NASDAQ technology stocks
            - Top gainers
            - Energy stocks on NYSE
            """;
    }

    private static string? ExtractSymbol(string message)
    {
        var tokens = message.Split([' ', ',', '?', '!', '.', ':', ';', '\n', '\t'], StringSplitOptions.RemoveEmptyEntries);
        foreach (var token in tokens)
        {
            var t = token.Trim('$').ToUpperInvariant();
            if (t.Length is >= 1 and <= 6 && t.All(c => char.IsLetter(c) || c == '-'))
            {
                // Skip common English words that look like tickers.
                if (t is "A" or "I" or "THE" or "WHAT" or "PRICE" or "OF" or "SHOW" or "LIST" or "TOP" or "STOCK" or "STOCKS" or "FOR" or "AND" or "ON")
                {
                    continue;
                }

                return t;
            }
        }

        return null;
    }

    private static string ExtractResponseText(string body)
    {
        using var doc = JsonDocument.Parse(body);
        var root = doc.RootElement;

        if (root.TryGetProperty("output_text", out var outputText) && outputText.ValueKind == JsonValueKind.String)
        {
            var text = outputText.GetString();
            if (!string.IsNullOrWhiteSpace(text))
            {
                return text!;
            }
        }

        if (root.TryGetProperty("output", out var output) && output.ValueKind == JsonValueKind.Array)
        {
            var sb = new StringBuilder();
            foreach (var item in output.EnumerateArray())
            {
                if (item.TryGetProperty("content", out var content) && content.ValueKind == JsonValueKind.Array)
                {
                    foreach (var part in content.EnumerateArray())
                    {
                        if (part.TryGetProperty("text", out var textEl) && textEl.ValueKind == JsonValueKind.String)
                        {
                            sb.AppendLine(textEl.GetString());
                        }
                        else if (part.TryGetProperty("type", out var typeEl)
                                 && typeEl.GetString() is "output_text" or "text"
                                 && part.TryGetProperty("text", out var t2))
                        {
                            sb.AppendLine(t2.GetString());
                        }
                    }
                }
                else if (item.TryGetProperty("text", out var directText) && directText.ValueKind == JsonValueKind.String)
                {
                    sb.AppendLine(directText.GetString());
                }
            }

            var combined = sb.ToString().Trim();
            if (!string.IsNullOrWhiteSpace(combined))
            {
                return combined;
            }
        }

        if (root.TryGetProperty("choices", out var choices) && choices.ValueKind == JsonValueKind.Array && choices.GetArrayLength() > 0)
        {
            var first = choices[0];
            if (first.TryGetProperty("message", out var msg) && msg.TryGetProperty("content", out var content))
            {
                return content.GetString() ?? body;
            }
        }

        return Truncate(body, 2000);
    }

    private static string PrettyJson(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            return JsonSerializer.Serialize(doc.RootElement, new JsonSerializerOptions { WriteIndented = true });
        }
        catch
        {
            return json;
        }
    }

    private static string Truncate(string value, int max) =>
        value.Length <= max ? value : value[..max] + "…";
}
