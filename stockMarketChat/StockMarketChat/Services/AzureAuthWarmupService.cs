namespace StockMarketChat.Services;

/// <summary>
/// Triggers Azure sign-in as soon as the web host starts (before the first chat).
/// </summary>
public sealed class AzureAuthWarmupService : IHostedService
{
    private readonly IServiceProvider _services;
    private readonly IConfiguration _config;
    private readonly ILogger<AzureAuthWarmupService> _logger;
    private readonly IHostApplicationLifetime _lifetime;

    public AzureAuthWarmupService(
        IServiceProvider services,
        IConfiguration config,
        ILogger<AzureAuthWarmupService> logger,
        IHostApplicationLifetime lifetime)
    {
        _services = services;
        _config = config;
        _logger = logger;
        _lifetime = lifetime;
    }

    public Task StartAsync(CancellationToken cancellationToken)
    {
        if (!ShouldWarmup())
        {
            _logger.LogInformation("Azure auth warmup skipped (provider is not Foundry/Auto or endpoint missing).");
            return Task.CompletedTask;
        }

        // Run after the host is listening so startup is not blocked, but immediately on launch.
        _ = Task.Run(async () =>
        {
            try
            {
                // Brief delay so "Now listening on..." is printed first, then login UI appears.
                await Task.Delay(TimeSpan.FromMilliseconds(400), _lifetime.ApplicationStopping);
                var auth = _services.GetRequiredService<AzureAuthService>();
                await auth.GetAccessTokenAsync(_lifetime.ApplicationStopping);
            }
            catch (OperationCanceledException) when (_lifetime.ApplicationStopping.IsCancellationRequested)
            {
                // App shutting down during login — ignore.
            }
            catch (Exception ex)
            {
                _logger.LogWarning(
                    ex,
                    "Azure auth warmup did not complete. Chat will retry on first Foundry message. " +
                    "If no browser opened, check network/tenant or set Chat:Foundry:TenantId.");
            }
        }, CancellationToken.None);

        return Task.CompletedTask;
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    private bool ShouldWarmup()
    {
        var provider = (_config["Chat:Provider"] ?? "Auto").Trim();
        var hasEndpoint = !string.IsNullOrWhiteSpace(_config["Chat:Foundry:ProjectEndpoint"]);
        if (!hasEndpoint)
        {
            return false;
        }

        return provider.Equals("Foundry", StringComparison.OrdinalIgnoreCase)
               || provider.Equals("Auto", StringComparison.OrdinalIgnoreCase);
    }
}
