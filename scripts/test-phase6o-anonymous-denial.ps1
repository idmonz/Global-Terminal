$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)

    $envPath = Join-Path (Get-Location) ".env"
    $escaped = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match "^\s*$escaped\s*=" } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    $value = ($line -split "=", 2)[1].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    return $value
}

$supabaseUrl = Get-DotEnvValue "SUPABASE_URL"
$publishableKey = Get-DotEnvValue "SUPABASE_PUBLISHABLE_KEY"
if ([string]::IsNullOrWhiteSpace($supabaseUrl) -or [string]::IsNullOrWhiteSpace($publishableKey)) {
    throw "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required in .env."
}

$tables = @(
    "global_terminal_watchlist_alert_rules",
    "global_terminal_watchlist_alert_evaluations",
    "global_terminal_watchlist_alert_triggers",
    "global_terminal_watchlist_alert_audit",
    "global_terminal_watchlist_alert_worker_state"
)

Write-Host "Checking Phase 6O anonymous denial. Keys and response bodies are not printed."
foreach ($table in $tables) {
    $statusCode = $null
    try {
        $response = Invoke-WebRequest `
            -Method Get `
            -Uri "$($supabaseUrl.TrimEnd('/'))/rest/v1/$table`?select=*&limit=1" `
            -Headers @{ apikey = $publishableKey } `
            -UseBasicParsing
        $statusCode = [int]$response.StatusCode
    }
    catch {
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        else {
            throw "Anonymous denial probe failed before an HTTP status was returned for $table."
        }
    }
    if ($statusCode -notin @(401, 403)) {
        throw "Anonymous access was not denied for $table (HTTP $statusCode)."
    }
    Write-Host "PASS: $table denies anonymous reads (HTTP $statusCode)" -ForegroundColor Green
}

$publishableKey = $null
Write-Host "Phase 6O anonymous denial passed." -ForegroundColor Green
