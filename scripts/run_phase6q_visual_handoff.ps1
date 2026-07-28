param(
    [int]$WebPort = 0,
    [int]$ApiPort = 0,
    [switch]$KeepServers
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$startedProcessIds = @()

function Test-AvailablePort {
    param([int]$Port)
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    }
    catch { return $false }
    finally { if ($null -ne $listener) { $listener.Stop() } }
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
    foreach ($child in $children) { Stop-ProcessTree -TargetProcessId ([int]$child.ProcessId) }
    Stop-Process -Id $TargetProcessId -Force -ErrorAction SilentlyContinue
}

Push-Location $repoRoot
try {
    if (-not (Test-Path -LiteralPath "apps/web/.next/BUILD_ID")) {
        throw "Production web build is missing. Run npm --prefix apps/web run build first."
    }
    if ($WebPort -le 0) { $WebPort = Find-AvailablePort -Start 3367 }
    elseif (-not (Test-AvailablePort -Port $WebPort)) { throw "Requested web port $WebPort is occupied." }
    if ($ApiPort -le 0) { $ApiPort = Find-AvailablePort -Start 8367 }
    elseif (-not (Test-AvailablePort -Port $ApiPort)) { throw "Requested API port $ApiPort is occupied." }

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
    catch { if ($startupExitCode -eq 0) { throw "Local product startup returned invalid JSON." } }
    if ($startupExitCode -ne 0) { throw "Local product startup failed with exit code $startupExitCode" }

    $web = Invoke-WebRequest -Uri "$baseUrl/?view=alert-manager&mode=fixture&tab=schedule" -UseBasicParsing -TimeoutSec 15
    $api = Invoke-WebRequest -Uri "$apiUrl/api/runtime-health" -UseBasicParsing -TimeoutSec 15
    if ($web.StatusCode -ne 200 -or $api.StatusCode -ne 200) { throw "Phase 6Q visual preflight failed: web=$($web.StatusCode), api=$($api.StatusCode)" }

    $env:GT_BASE_URL = $baseUrl
    npm --prefix apps/web run visual:phase6q
    if ($LASTEXITCODE -ne 0) { throw "Phase 6Q capture harness failed with exit code $LASTEXITCODE" }
    npm --prefix apps/web run visual:verify:phase6q
    if ($LASTEXITCODE -ne 0) { throw "Phase 6Q summary verification failed with exit code $LASTEXITCODE" }

    Write-Output "Phase 6Q visual evidence verified."
    Write-Output "Runtime: $baseUrl"
    Write-Output "Summary: review_workspace/phase6q_visual/summary.json"
    Write-Output "Captures: review_workspace/phase6q_visual/*.png"
}
finally {
    if (-not $KeepServers) {
        foreach ($processId in @($startedProcessIds | Sort-Object -Descending)) { Stop-ProcessTree -TargetProcessId $processId }
    }
    Remove-Item Env:GT_BASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}
