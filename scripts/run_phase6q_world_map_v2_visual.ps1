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
    if ($WebPort -le 0) { $WebPort = Find-AvailablePort -Start 3467 }
    if ($ApiPort -le 0) { $ApiPort = Find-AvailablePort -Start 8467 }
    $baseUrl = "http://127.0.0.1:$WebPort"
    $startupText = (& python scripts/start_local_product.py --production --api-port $ApiPort --web-port $WebPort --wait-seconds 120 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Local product startup failed with exit code $LASTEXITCODE" }
    $startup = $startupText | ConvertFrom-Json
    $startedProcessIds = @($startup.started | Where-Object { $_.status -eq "started" -and $null -ne $_.pid } | ForEach-Object { [int]$_.pid })
    Write-Output $startupText

    $env:GT_BASE_URL = $baseUrl
    npm --prefix apps/web run visual:phase6q:world-map-v2
    if ($LASTEXITCODE -ne 0) { throw "World map capture failed with exit code $LASTEXITCODE" }
    npm --prefix apps/web run visual:verify:phase6q:world-map-v2
    if ($LASTEXITCODE -ne 0) { throw "World map visual verification failed with exit code $LASTEXITCODE" }

    Write-Output "World map v2 visual evidence verified."
    Write-Output "Runtime: $baseUrl"
    Write-Output "Summary: review_workspace/phase6q_world_map_v2_visual/summary.json"
}
finally {
    if (-not $KeepServers) {
        foreach ($processId in @($startedProcessIds | Sort-Object -Descending)) { Stop-ProcessTree -TargetProcessId $processId }
    }
    Remove-Item Env:GT_BASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}
