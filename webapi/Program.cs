using System.Text.Json;
using GenAiApp.Api.Models;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    options.SerializerOptions.PropertyNameCaseInsensitive = true;
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();

app.MapGet("/api/health", () => Results.Ok(new { status = "healthy" }))
    .WithName("HealthCheck");

app.MapPost("/api/data", (DataRequest request) =>
{
    var response = new DataResponse
    {
        Id = Guid.NewGuid().ToString("N"),
        Name = request.Name,
        Message = request.Message,
        Metadata = request.Metadata,
        ReceivedAt = DateTimeOffset.UtcNow
    };

    return Results.Created($"/api/data/{response.Id}", response);
})
.WithName("IngestStructuredData");

app.MapPost("/api/data/raw", (JsonElement payload) =>
{
    var response = new
    {
        id = Guid.NewGuid().ToString("N"),
        receivedAt = DateTimeOffset.UtcNow,
        payload
    };

    return Results.Created($"/api/data/{response.id}", response);
})
.WithName("IngestRawJson");

app.Run();
