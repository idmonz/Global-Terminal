$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "supabase\config.toml"
$sqlPath = Join-Path $repoRoot "supabase\tests\phase6o_alert_manager_rls.integration.sql"

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Supabase config not found: $configPath"
}
if (-not (Test-Path -LiteralPath $sqlPath)) {
    throw "Phase 6O integration SQL not found: $sqlPath"
}

$projectLine = Get-Content -LiteralPath $configPath |
    Where-Object { $_ -match '^\s*project_id\s*=' } |
    Select-Object -First 1
if (-not $projectLine -or $projectLine -notmatch '^\s*project_id\s*=\s*"([^"]+)"') {
    throw "Unable to read project_id from supabase/config.toml"
}

$containerName = "supabase_db_$($Matches[1])"
docker inspect $containerName *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Local Supabase database is not running. Run: supabase start"
}

Write-Host "Running Phase 6O local Alert Manager isolation checks..."
Get-Content -LiteralPath $sqlPath -Raw |
    docker exec -i $containerName psql -U postgres -d postgres -X
if ($LASTEXITCODE -ne 0) {
    throw "Phase 6O local Alert Manager isolation checks failed."
}

Write-Host "Phase 6O local Alert Manager isolation checks passed." -ForegroundColor Green
