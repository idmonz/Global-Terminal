param(
    [int]$WebPort = 0,
    [int]$ApiPort = 0,
    [switch]$KeepServers
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$startedProcessIds = @()
$phase6pAccountDb = $null
$previousLocalAuth = [Environment]::GetEnvironmentVariable("GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED", "Process")
$previousAccountDb = [Environment]::GetEnvironmentVariable("GLOBAL_TERMINAL_ACCOUNT_DB_PATH", "Process")
$previousCookieSecure = [Environment]::GetEnvironmentVariable("GLOBAL_TERMINAL_COOKIE_SECURE", "Process")

function Test-AvailablePort {
    param([int]$Port)
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $listener) { $listener.Stop() }
    }
}

function Find-AvailablePort {
    param([int]$Start)
    for ($candidate = $Start; $candidate -lt ($Start + 200); $candidate += 1) {
        if (Test-AvailablePort -Port $candidate) { return $candidate }
    }
    throw "No available local port found from $Start."
}

function Stop-ProcessTree {
    param([int]$TargetProcessId)
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $TargetProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-ProcessTree -TargetProcessId ([int]$child.ProcessId)
    }
    Stop-Process -Id $TargetProcessId -Force -ErrorAction SilentlyContinue
}

function Restore-ProcessEnvironmentVariable {
    param([string]$Name, [AllowNull()][string]$Value)
    [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
}

Push-Location $repoRoot

try {
    if (-not (Test-Path -LiteralPath "apps/web/.next/BUILD_ID")) {
        throw "Production web build is missing. Run npm --prefix apps/web run build first."
    }

    $phase6pVisualRoot = Join-Path $repoRoot "review_workspace/phase6p_visual"
    New-Item -ItemType Directory -Path $phase6pVisualRoot -Force | Out-Null
    $phase6pAccountDb = Join-Path $phase6pVisualRoot "phase6p-account-$([guid]::NewGuid().ToString('N')).db"
    $env:GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED = "true"
    $env:GLOBAL_TERMINAL_ACCOUNT_DB_PATH = $phase6pAccountDb
    $env:GLOBAL_TERMINAL_COOKIE_SECURE = "false"

    if ($WebPort -le 0) {
        $WebPort = Find-AvailablePort -Start 3267
    }
    elseif (-not (Test-AvailablePort -Port $WebPort)) {
        throw "Requested web port $WebPort is already occupied. Use a free port or omit -WebPort."
    }

    if ($ApiPort -le 0) {
        $ApiPort = Find-AvailablePort -Start 8267
    }
    elseif (-not (Test-AvailablePort -Port $ApiPort)) {
        throw "Requested API port $ApiPort is already occupied. Use a free port or omit -ApiPort."
    }

    $baseUrl = "http://127.0.0.1:$WebPort"
    $apiUrl = "http://127.0.0.1:$ApiPort"
    $startupText = (& python scripts/start_local_product.py --production --api-port $ApiPort --web-port $WebPort --wait-seconds 120 2>&1 | Out-String).Trim()
    $startupExitCode = $LASTEXITCODE
    Write-Output $startupText

    $startup = $null
    try {
        $startup = $startupText | ConvertFrom-Json
        $startedProcessIds = @($startup.started | Where-Object { $_.status -eq "started" -and $null -ne $_.pid } | ForEach-Object { [int]$_.pid })
    }
    catch {
        if ($startupExitCode -eq 0) { throw "Local product startup returned invalid JSON." }
    }

    if ($startupExitCode -ne 0) {
        throw "Local product startup failed with exit code $startupExitCode"
    }

    $web = Invoke-WebRequest -Uri "$baseUrl/?view=watchlist-desk&mode=fixture" -UseBasicParsing -TimeoutSec 15
    $api = Invoke-WebRequest -Uri "$apiUrl/api/runtime-health" -UseBasicParsing -TimeoutSec 15
    if ($web.StatusCode -ne 200 -or $api.StatusCode -ne 200) {
        throw "Phase 6P visual preflight failed: web=$($web.StatusCode), api=$($api.StatusCode)"
    }

    $env:GT_BASE_URL = $baseUrl
    npm --prefix apps/web run visual:phase6p
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 6P capture harness failed with exit code $LASTEXITCODE"
    }

    npm --prefix apps/web run visual:verify:phase6p
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 6P summary verification failed with exit code $LASTEXITCODE"
    }

    Write-Output "Phase 6P visual evidence verified."
    Write-Output "Runtime: $baseUrl"
    Write-Output "Summary: review_workspace/phase6p_visual/summary.json"
    Write-Output "Captures: review_workspace/phase6p_visual/*.png"
}
finally {
    if (-not $KeepServers) {
        foreach ($processId in @($startedProcessIds | Sort-Object -Descending)) {
            Stop-ProcessTree -TargetProcessId $processId
        }
        if ($null -ne $phase6pAccountDb) {
            foreach ($accountArtifact in @($phase6pAccountDb, "$phase6pAccountDb-wal", "$phase6pAccountDb-shm")) {
                Remove-Item -LiteralPath $accountArtifact -Force -ErrorAction SilentlyContinue
            }
        }
    }
    Restore-ProcessEnvironmentVariable -Name "GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED" -Value $previousLocalAuth
    Restore-ProcessEnvironmentVariable -Name "GLOBAL_TERMINAL_ACCOUNT_DB_PATH" -Value $previousAccountDb
    Restore-ProcessEnvironmentVariable -Name "GLOBAL_TERMINAL_COOKIE_SECURE" -Value $previousCookieSecure
    Remove-Item Env:GT_BASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}
