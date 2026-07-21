using StockMarketChat.Client.Models;
using StockMarketChat.Client.Pages;
using StockMarketChat.Components;
using StockMarketChat.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorComponents()
    .AddInteractiveWebAssemblyComponents();

builder.Services.AddMemoryCache();

builder.Services.AddHttpClient(nameof(ChatService), client =>
{
    // Agent + OpenAPI tool round-trips can exceed 60s under rate limits.
    client.Timeout = TimeSpan.FromMinutes(3);
});

builder.Services.AddHttpClient(nameof(MarketDataService), client =>
{
    client.Timeout = TimeSpan.FromSeconds(30);
});

// Shared Azure credential + automatic sign-in when the host starts.
builder.Services.AddSingleton<AzureAuthService>();
builder.Services.AddHostedService<AzureAuthWarmupService>();
builder.Services.AddScoped<ChatService>();
builder.Services.AddSingleton<MarketDataService>();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseWebAssemblyDebugging();
}
else
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);
app.UseHttpsRedirection();

app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(StockMarketChat.Client._Imports).Assembly);

app.MapPost("/api/chat", async (ChatRequest request, ChatService chat, CancellationToken ct) =>
{
    var result = await chat.SendAsync(request, ct);
    return Results.Ok(result);
}).DisableAntiforgery();

app.MapGet("/api/health", (IConfiguration config, AzureAuthService auth) =>
{
    var provider = config["Chat:Provider"] ?? "Auto";
    return Results.Ok(new
    {
        status = "ok",
        app = "StockMarketChat",
        provider,
        foundryConfigured = !string.IsNullOrWhiteSpace(config["Chat:Foundry:ProjectEndpoint"]),
        spaceXaiConfigured = !string.IsNullOrWhiteSpace(
            config["Chat:SpaceXAI:ApiKey"] ?? Environment.GetEnvironmentVariable("XAI_API_KEY")),
        azureAuthenticated = auth.IsAuthenticated,
        azureTokenExpiresOn = auth.TokenExpiresOn,
        azureAuthError = auth.LastError
    });
});

// Cosmos-backed quotes (via stock-query-api), cached in-memory for 24h.
app.MapGet("/api/ticker", async (MarketDataService market, CancellationToken ct) =>
{
    try
    {
        var ticker = await market.GetTickerAsync(ct);
        return Results.Ok(ticker);
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            title: "Failed to load ticker quotes from Cosmos stock API",
            statusCode: StatusCodes.Status502BadGateway);
    }
});

app.Run();
