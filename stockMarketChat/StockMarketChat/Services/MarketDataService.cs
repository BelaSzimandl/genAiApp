using System.Globalization;
using System.Text.Json;
using Microsoft.Extensions.Caching.Memory;
using StockMarketChat.Client.Models;

namespace StockMarketChat.Services;

/// <summary>
/// Loads stock quotes from the Cosmos-backed stock query API.
/// Cache layers (1 day TTL):
/// 1. In-process memory (fast)
/// 2. Durable JSON file under App_Data (survives app restarts)
/// Browser localStorage is an additional client-side layer (see Chat.razor).
/// </summary>
public sealed class MarketDataService
{
    public const string TickerCacheKey = "market:ticker:v1";
    private static readonly TimeSpan CacheDuration = TimeSpan.FromDays(1);
    private static readonly JsonSerializerOptions FileJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IMemoryCache _cache;
    private readonly IConfiguration _config;
    private readonly IHostEnvironment _env;
    private readonly ILogger<MarketDataService> _logger;
    private readonly SemaphoreSlim _fileGate = new(1, 1);

    public MarketDataService(
        IHttpClientFactory httpClientFactory,
        IMemoryCache cache,
        IConfiguration config,
        IHostEnvironment env,
        ILogger<MarketDataService> logger)
    {
        _httpClientFactory = httpClientFactory;
        _cache = cache;
        _config = config;
        _env = env;
        _logger = logger;
    }

    public async Task<TickerResponse> GetTickerAsync(CancellationToken cancellationToken = default)
    {
        // L1: memory
        if (_cache.TryGetValue(TickerCacheKey, out TickerResponse? memoryHit) && memoryHit is not null)
        {
            return CloneAsCacheHit(memoryHit, "memory");
        }

        // L2: durable file (survives restart)
        var fileHit = await TryReadFileCacheAsync(cancellationToken);
        if (fileHit is not null)
        {
            SetMemoryCache(fileHit);
            return CloneAsCacheHit(fileHit, "file");
        }

        // L3: Cosmos-backed stock API
        var fresh = await LoadFromCosmosApiAsync(cancellationToken);
        SetMemoryCache(fresh);
        await WriteFileCacheAsync(fresh, cancellationToken);
        return fresh;
    }

    private void SetMemoryCache(TickerResponse value)
    {
        var ttl = value.ExpiresAt - DateTimeOffset.UtcNow;
        if (ttl <= TimeSpan.Zero)
        {
            ttl = CacheDuration;
        }

        _cache.Set(
            TickerCacheKey,
            value,
            new MemoryCacheEntryOptions { AbsoluteExpirationRelativeToNow = ttl });
    }

    private static TickerResponse CloneAsCacheHit(TickerResponse source, string sourceLabel) =>
        new()
        {
            Items = source.Items,
            CachedAt = source.CachedAt,
            ExpiresAt = source.ExpiresAt,
            FromCache = true,
            Source = sourceLabel
        };

    private string GetCacheFilePath()
    {
        var configured = _config["Chat:Ticker:CacheFilePath"];
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return Path.GetFullPath(configured);
        }

        var dir = Path.Combine(_env.ContentRootPath, "App_Data");
        return Path.Combine(dir, "ticker-cache.json");
    }

    private async Task<TickerResponse?> TryReadFileCacheAsync(CancellationToken cancellationToken)
    {
        var path = GetCacheFilePath();
        if (!File.Exists(path))
        {
            return null;
        }

        await _fileGate.WaitAsync(cancellationToken);
        try
        {
            await using var stream = File.OpenRead(path);
            var stored = await JsonSerializer.DeserializeAsync<TickerResponse>(
                stream,
                FileJsonOptions,
                cancellationToken);

            if (stored is null || stored.Items.Count == 0)
            {
                return null;
            }

            if (stored.ExpiresAt <= DateTimeOffset.UtcNow)
            {
                _logger.LogInformation("Durable ticker cache expired at {ExpiresAt:u}; will refresh.", stored.ExpiresAt);
                return null;
            }

            _logger.LogInformation(
                "Loaded ticker from durable file cache ({Count} symbols, expires {ExpiresAt:u}).",
                stored.Items.Count,
                stored.ExpiresAt);
            return stored;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Could not read durable ticker cache at {Path}", path);
            return null;
        }
        finally
        {
            _fileGate.Release();
        }
    }

    private async Task WriteFileCacheAsync(TickerResponse value, CancellationToken cancellationToken)
    {
        var path = GetCacheFilePath();
        await _fileGate.WaitAsync(cancellationToken);
        try
        {
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrWhiteSpace(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var toStore = new TickerResponse
            {
                Items = value.Items,
                CachedAt = value.CachedAt,
                ExpiresAt = value.ExpiresAt,
                FromCache = true,
                Source = "file"
            };

            await using var stream = File.Create(path);
            await JsonSerializer.SerializeAsync(stream, toStore, FileJsonOptions, cancellationToken);
            _logger.LogInformation("Wrote durable ticker cache to {Path} (expires {ExpiresAt:u}).", path, value.ExpiresAt);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Could not write durable ticker cache to {Path}", path);
        }
        finally
        {
            _fileGate.Release();
        }
    }

    private async Task<TickerResponse> LoadFromCosmosApiAsync(CancellationToken cancellationToken)
    {
        var baseUrl = (_config["Chat:StockQueryApiBaseUrl"]
                       ?? "https://stock-query-api-bsz.azurewebsites.net").TrimEnd('/');
        var limit = _config.GetValue("Chat:Ticker:Limit", 20);
        var client = _httpClientFactory.CreateClient(nameof(MarketDataService));

        try
        {
            await using var stream = await client.GetStreamAsync(
                $"{baseUrl}/stocks?limit={limit}",
                cancellationToken);

            using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
            var items = ParseQuotes(doc.RootElement);
            var now = DateTimeOffset.UtcNow;

            if (items.Count == 0)
            {
                _logger.LogWarning("Stock API returned no quotes for ticker tape.");
            }
            else
            {
                _logger.LogInformation(
                    "Loaded {Count} quotes from Cosmos stock API for ticker tape (cache {Hours}h).",
                    items.Count,
                    CacheDuration.TotalHours);
            }

            return new TickerResponse
            {
                Items = items,
                CachedAt = now,
                ExpiresAt = now.Add(CacheDuration),
                FromCache = false,
                Source = "cosmos"
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load ticker quotes from stock API");

            // If Cosmos is down but we still have a stale file, prefer stale data over total failure.
            var stale = await TryReadStaleFileCacheAsync(cancellationToken);
            if (stale is not null)
            {
                _logger.LogWarning("Serving expired durable ticker cache because Cosmos API failed.");
                return CloneAsCacheHit(stale, "file-stale");
            }

            throw;
        }
    }

    private async Task<TickerResponse?> TryReadStaleFileCacheAsync(CancellationToken cancellationToken)
    {
        var path = GetCacheFilePath();
        if (!File.Exists(path))
        {
            return null;
        }

        try
        {
            await using var stream = File.OpenRead(path);
            return await JsonSerializer.DeserializeAsync<TickerResponse>(stream, FileJsonOptions, cancellationToken);
        }
        catch
        {
            return null;
        }
    }

    private static List<TickerItemDto> ParseQuotes(JsonElement root)
    {
        JsonElement quotesEl;
        if (root.ValueKind == JsonValueKind.Array)
        {
            quotesEl = root;
        }
        else if (root.TryGetProperty("quotes", out var q) && q.ValueKind == JsonValueKind.Array)
        {
            quotesEl = q;
        }
        else
        {
            return [];
        }

        var items = new List<TickerItemDto>();
        foreach (var row in quotesEl.EnumerateArray())
        {
            var symbol = row.TryGetProperty("symbol", out var sym) ? sym.GetString() : null;
            if (string.IsNullOrWhiteSpace(symbol))
            {
                continue;
            }

            decimal? changePct = null;
            if (row.TryGetProperty("change_pct", out var ch) && ch.ValueKind == JsonValueKind.Number)
            {
                changePct = ch.GetDecimal();
            }

            decimal? price = null;
            if (row.TryGetProperty("price", out var p) && p.ValueKind == JsonValueKind.Number)
            {
                price = p.GetDecimal();
            }

            var pct = changePct ?? 0m;
            var up = pct >= 0;
            // change_pct from Cosmos is already in percent points (e.g. 1.24 = +1.24%), not a fraction.
            var changeText = pct.ToString("+0.00;-0.00;0.00", CultureInfo.InvariantCulture) + "%";

            items.Add(new TickerItemDto
            {
                Symbol = symbol!,
                Change = changeText,
                Up = up,
                Price = price,
                ChangePct = changePct
            });
        }

        return items
            .OrderByDescending(i => Math.Abs(i.ChangePct ?? 0))
            .ThenBy(i => i.Symbol, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }
}
