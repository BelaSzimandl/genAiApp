using Azure.Core;
using Azure.Identity;

namespace StockMarketChat.Services;

/// <summary>
/// Shared Azure credential for Foundry calls. On first token request the
/// interactive browser sign-in runs if no CLI/VS/env credential is available.
/// </summary>
public sealed class AzureAuthService
{
    public static readonly string[] FoundryScopes = ["https://ai.azure.com/.default"];

    private readonly TokenCredential _credential;
    private readonly ILogger<AzureAuthService> _logger;
    private readonly object _gate = new();
    private AccessToken? _cached;
    private Task<AccessToken>? _inFlight;

    public AzureAuthService(IConfiguration config, ILogger<AzureAuthService> logger)
    {
        _logger = logger;

        var tenantId = config["Chat:Foundry:TenantId"];
        var enableInteractive = !string.Equals(
            config["Chat:Foundry:InteractiveLogin"],
            "false",
            StringComparison.OrdinalIgnoreCase);

        // Prefer silent sources first; fall through to browser / device-code login for local dev.
        // Short CLI timeout so we don't block for ~30s before interactive when az is missing.
        var cliOptions = CreateCliOptions(tenantId);
        cliOptions.ProcessTimeout = TimeSpan.FromSeconds(5);

        var chain = new List<TokenCredential>
        {
            new EnvironmentCredential(),
            new AzureCliCredential(cliOptions),
            new VisualStudioCredential(CreateVsOptions(tenantId)),
            new AzurePowerShellCredential(),
            new AzureDeveloperCliCredential()
        };

        if (enableInteractive)
        {
            var browserOptions = new InteractiveBrowserCredentialOptions
            {
                // Persist tokens so the browser does not open on every restart.
                TokenCachePersistenceOptions = new TokenCachePersistenceOptions
                {
                    Name = "StockMarketChat.Foundry"
                },
                AdditionallyAllowedTenants = { "*" }
            };

            if (!string.IsNullOrWhiteSpace(tenantId))
            {
                browserOptions.TenantId = tenantId;
            }

            chain.Add(new InteractiveBrowserCredential(browserOptions));

            // Console device-code fallback when browser cannot open (headless / restricted).
            var deviceOptions = new DeviceCodeCredentialOptions
            {
                AdditionallyAllowedTenants = { "*" },
                DeviceCodeCallback = (code, _) =>
                {
                    _logger.LogWarning(
                        "Azure device login required. Open {Url} and enter code {Code}",
                        code.VerificationUri,
                        code.UserCode);
                    Console.WriteLine();
                    Console.WriteLine("=== Azure sign-in required ===");
                    Console.WriteLine($"Open: {code.VerificationUri}");
                    Console.WriteLine($"Code: {code.UserCode}");
                    Console.WriteLine("==============================");
                    Console.WriteLine();
                    return Task.CompletedTask;
                }
            };
            if (!string.IsNullOrWhiteSpace(tenantId))
            {
                deviceOptions.TenantId = tenantId;
            }

            chain.Add(new DeviceCodeCredential(deviceOptions));

            _logger.LogInformation(
                "Azure auth: interactive browser + device-code enabled (browser only if CLI/VS has no session).");
        }

        _credential = new ChainedTokenCredential(chain.ToArray());
    }

    public bool IsAuthenticated =>
        _cached is { } token && token.ExpiresOn > DateTimeOffset.UtcNow.AddMinutes(2);

    public DateTimeOffset? TokenExpiresOn => _cached?.ExpiresOn;

    public string? LastError { get; private set; }

    /// <summary>
    /// Acquire (or refresh) a Foundry-scoped access token. May open a browser once.
    /// </summary>
    public Task<AccessToken> GetAccessTokenAsync(CancellationToken cancellationToken = default)
    {
        lock (_gate)
        {
            if (_cached is { } cached && cached.ExpiresOn > DateTimeOffset.UtcNow.AddMinutes(2))
            {
                return Task.FromResult(cached);
            }

            if (_inFlight is not null)
            {
                return _inFlight;
            }

            _inFlight = AcquireCoreAsync(cancellationToken);
            return _inFlight;
        }
    }

    private async Task<AccessToken> AcquireCoreAsync(CancellationToken cancellationToken)
    {
        try
        {
            _logger.LogInformation(
                "Azure auth: acquiring token for Foundry ({Scope}). A browser window may open for sign-in.",
                FoundryScopes[0]);

            var token = await _credential.GetTokenAsync(
                new TokenRequestContext(FoundryScopes),
                cancellationToken);

            lock (_gate)
            {
                _cached = token;
                _inFlight = null;
                LastError = null;
            }

            _logger.LogInformation(
                "Azure auth: signed in successfully. Token expires at {ExpiresOn:u}.",
                token.ExpiresOn);
            return token;
        }
        catch (Exception ex)
        {
            lock (_gate)
            {
                _inFlight = null;
                LastError = ex.Message;
            }

            _logger.LogError(ex, "Azure auth: failed to acquire token");
            throw;
        }
    }

    private static AzureCliCredentialOptions CreateCliOptions(string? tenantId)
    {
        var options = new AzureCliCredentialOptions { AdditionallyAllowedTenants = { "*" } };
        if (!string.IsNullOrWhiteSpace(tenantId))
        {
            options.TenantId = tenantId;
        }

        return options;
    }

    private static VisualStudioCredentialOptions CreateVsOptions(string? tenantId)
    {
        var options = new VisualStudioCredentialOptions { AdditionallyAllowedTenants = { "*" } };
        if (!string.IsNullOrWhiteSpace(tenantId))
        {
            options.TenantId = tenantId;
        }

        return options;
    }
}
