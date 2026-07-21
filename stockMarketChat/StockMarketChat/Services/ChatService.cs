using System.ClientModel;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
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
    private readonly AzureAuthService _azureAuth;
    private readonly ILogger<ChatService> _logger;

    public ChatService(
        IConfiguration config,
        IHttpClientFactory httpClientFactory,
        AzureAuthService azureAuth,
        ILogger<ChatService> logger)
    {
        _config = config;
        _httpClientFactory = httpClientFactory;
        _azureAuth = azureAuth;
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
            // Foundry is the primary path whenever the project endpoint is configured.
            if (IsProvider(provider, "Foundry") || (IsProvider(provider, "Auto") && HasFoundryConfig()))
            {
                var reply = await InvokeFoundryAgentAsync(message, history, cancellationToken);
                return new ChatResponse { Reply = reply, Provider = "foundry", Success = true };
            }

            if (IsProvider(provider, "SpaceXAI") || (IsProvider(provider, "Auto") && HasSpaceXaiKey()))
            {
                var reply = await InvokeSpaceXaiAsync(message, history, cancellationToken);
                return new ChatResponse { Reply = reply, Provider = "spacexai", Success = true };
            }

            if (IsProvider(provider, "Demo"))
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
        var token = await _azureAuth.GetAccessTokenAsync(cancellationToken);
        var client = _httpClientFactory.CreateClient(nameof(ChatService));

        // Nudge the agent to call tools in the same turn (gpt-5-mini sometimes only promises to fetch).
        var inputText =
            BuildConversationInput(history, message)
            + "\n\n[System reminder: For any price/list/mover/exchange question you MUST call the stock tools "
            + "in this turn and return concrete quote data. Do not only say you will call the API.]";

        var first = await PostFoundryResponseAsync(
            client,
            endpoint,
            token.Token,
            model,
            agentName,
            input: inputText,
            previousResponseId: null,
            cancellationToken);

        var result = AnalyzeFoundryBody(first.Body);
        _logger.LogInformation(
            "Foundry turn 1: status={Status}, tools={ToolCount}, deferred={Deferred}, replyLen={Len}",
            result.Status,
            result.ToolCallCount,
            result.LooksDeferred,
            result.Text.Length);

        // If the model finished with "Calling API..." and never invoked tools, force a continuation.
        if (result.LooksDeferred || (result.ToolCallCount == 0 && IsMarketDataQuestion(message) && IsThinAnswer(result.Text)))
        {
            _logger.LogWarning("Foundry agent deferred tool use; requesting forced continuation.");
            var continueInput =
                "Continue the previous request now. Call the OpenAPI stock tools (listStocks / getStock / getMovers / listExchanges) "
                + "with the correct filters and return the actual table of quotes. "
                + "Do not reply with only 'Calling API' or 'I will fetch'.";

            var second = await PostFoundryResponseAsync(
                client,
                endpoint,
                token.Token,
                model,
                agentName,
                input: continueInput,
                previousResponseId: first.ResponseId,
                cancellationToken);

            var continued = AnalyzeFoundryBody(second.Body);
            _logger.LogInformation(
                "Foundry turn 2: status={Status}, tools={ToolCount}, deferred={Deferred}, replyLen={Len}",
                continued.Status,
                continued.ToolCallCount,
                continued.LooksDeferred,
                continued.Text.Length);

            if (!continued.LooksDeferred && !string.IsNullOrWhiteSpace(continued.Text) && !IsThinAnswer(continued.Text))
            {
                return continued.Text;
            }

            // Last resort: serve live stock API data so the UI never hangs on a promise-only reply.
            var fallback = await TryStockApiFallbackAsync(message, cancellationToken);
            if (!string.IsNullOrWhiteSpace(fallback))
            {
                return fallback;
            }

            return string.IsNullOrWhiteSpace(continued.Text) ? result.Text : continued.Text;
        }

        if (string.IsNullOrWhiteSpace(result.Text))
        {
            var fallback = await TryStockApiFallbackAsync(message, cancellationToken);
            if (!string.IsNullOrWhiteSpace(fallback))
            {
                return fallback;
            }
        }

        return result.Text;
    }

    private async Task<(string Body, string? ResponseId)> PostFoundryResponseAsync(
        HttpClient client,
        string endpoint,
        string accessToken,
        string model,
        string agentName,
        string input,
        string? previousResponseId,
        CancellationToken cancellationToken)
    {
        var payload = new Dictionary<string, object?>
        {
            ["model"] = model,
            ["input"] = input,
            ["agent_reference"] = new Dictionary<string, string>
            {
                ["name"] = agentName,
                ["type"] = "agent_reference"
            }
        };

        if (!string.IsNullOrWhiteSpace(previousResponseId))
        {
            payload["previous_response_id"] = previousResponseId;
        }

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, $"{endpoint.TrimEnd('/')}/openai/v1/responses");
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
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

        string? responseId = null;
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("id", out var idEl) && idEl.ValueKind == JsonValueKind.String)
            {
                responseId = idEl.GetString();
            }
        }
        catch
        {
            // ignore parse errors for id
        }

        return (body, responseId);
    }

    private static string BuildConversationInput(IReadOnlyList<ChatMessageDto> history, string message)
    {
        if (history.Count == 0)
        {
            return message;
        }

        var sb = new StringBuilder();
        sb.AppendLine("Conversation so far:");
        foreach (var item in history.TakeLast(12))
        {
            if (string.IsNullOrWhiteSpace(item.Content))
            {
                continue;
            }

            var role = item.Role.Equals("assistant", StringComparison.OrdinalIgnoreCase) ? "Assistant" : "User";
            sb.Append(role).Append(": ").AppendLine(item.Content.Trim());
        }

        sb.Append("User: ").Append(message);
        return sb.ToString();
    }

    private sealed record FoundryAnalysis(string Status, string Text, int ToolCallCount, bool LooksDeferred);

    private static FoundryAnalysis AnalyzeFoundryBody(string body)
    {
        using var doc = JsonDocument.Parse(body);
        var root = doc.RootElement;
        var status = root.TryGetProperty("status", out var statusEl) ? statusEl.GetString() ?? "" : "";
        var text = ExtractResponseText(body);
        var toolCount = 0;

        if (root.TryGetProperty("output", out var output) && output.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in output.EnumerateArray())
            {
                var type = item.TryGetProperty("type", out var t) ? t.GetString() : null;
                if (type is "openapi_call" or "openapi_call_output" or "function_call" or "function_call_output")
                {
                    toolCount++;
                }
            }
        }

        var deferred = toolCount == 0 && LooksLikeDeferredToolPromise(text);
        return new FoundryAnalysis(status, text, toolCount, deferred);
    }

    private static bool LooksLikeDeferredToolPromise(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return true;
        }

        var lower = text.ToLowerInvariant();
        string[] markers =
        [
            "calling api",
            "i'll fetch",
            "i will fetch",
            "let me fetch",
            "let me pull",
            "i'll pull",
            "i will pull",
            "one moment",
            "from the database now",
            "looking that up",
            "querying the",
            "i'll get",
            "i will get",
            "hang tight",
            "please wait"
        ];

        if (markers.Any(m => lower.Contains(m)))
        {
            // If the message already contains a price table / symbols with numbers, treat as complete.
            if (lower.Contains("usd") || lower.Contains("change") || lower.Contains("|") || lower.Contains("price"))
            {
                return false;
            }

            return true;
        }

        return false;
    }

    private static bool IsThinAnswer(string text) =>
        string.IsNullOrWhiteSpace(text) || text.Trim().Length < 80;

    private static bool IsMarketDataQuestion(string message)
    {
        var lower = message.ToLowerInvariant();
        return lower.Contains("stock")
               || lower.Contains("nasdaq")
               || lower.Contains("nyse")
               || lower.Contains("price")
               || lower.Contains("gainer")
               || lower.Contains("loser")
               || lower.Contains("exchange")
               || lower.Contains("sector")
               || lower.Contains("ticker")
               || lower.Contains("mover");
    }

    private async Task<string?> TryStockApiFallbackAsync(string message, CancellationToken cancellationToken)
    {
        var stockApi = (_config["Chat:StockQueryApiBaseUrl"]
                        ?? "https://stock-query-api-bsz.azurewebsites.net").TrimEnd('/');
        var client = _httpClientFactory.CreateClient(nameof(ChatService));
        var lower = message.ToLowerInvariant();

        try
        {
            string path;
            if (lower.Contains("gainer") || (lower.Contains("top") && lower.Contains("gain")))
            {
                path = "/movers?direction=gainers&limit=10";
            }
            else if (lower.Contains("loser"))
            {
                path = "/movers?direction=losers&limit=10";
            }
            else if (lower.Contains("exchange") && (lower.Contains("list") || lower.StartsWith("list")))
            {
                path = "/exchanges";
            }
            else
            {
                var qs = new List<string> { "limit=15" };
                if (lower.Contains("nasdaq")) qs.Add("exchange=NASDAQ");
                if (lower.Contains("nyse") && !lower.Contains("nysearca")) qs.Add("exchange=NYSE");
                if (lower.Contains("technolog")) qs.Add("sector=Technology");
                if (lower.Contains("energy")) qs.Add("sector=Energy");
                if (lower.Contains("financ")) qs.Add("sector=Financials");
                path = "/stocks?" + string.Join('&', qs);

                var symbol = ExtractSymbol(message);
                if (symbol is not null && (lower.Contains("price") || lower.Contains("quote") || message.Trim().Length <= 8))
                {
                    path = $"/stocks/{symbol}";
                }
            }

            var json = await client.GetStringAsync($"{stockApi}{path}", cancellationToken);
            return
                "**Market data** (direct stock API fallback — agent tool turn was incomplete):\n\n"
                + "```json\n"
                + PrettyJson(Truncate(json, 3500))
                + "\n```";
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Stock API fallback failed");
            return null;
        }
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
                // Prefer final assistant message items (skip reasoning / tool call noise).
                var itemType = item.TryGetProperty("type", out var typeProp) ? typeProp.GetString() : null;
                if (itemType is "reasoning" or "openapi_call" or "openapi_call_output" or "function_call" or "function_call_output")
                {
                    continue;
                }

                if (item.TryGetProperty("content", out var content) && content.ValueKind == JsonValueKind.Array)
                {
                    foreach (var part in content.EnumerateArray())
                    {
                        if (part.TryGetProperty("text", out var textEl) && textEl.ValueKind == JsonValueKind.String)
                        {
                            sb.AppendLine(textEl.GetString());
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
