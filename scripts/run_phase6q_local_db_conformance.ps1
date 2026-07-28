$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$sqlPath = Join-Path $repoRoot "supabase/tests/phase6q_hosted_scheduler_rls.integration.sql"

if (-not (Test-Path -LiteralPath $sqlPath)) {
    throw "Phase 6Q local conformance SQL is missing."
}

$container = docker ps --format "{{.Names}}" | Where-Object { $_ -eq "supabase_db_Global_Terminal" } | Select-Object -First 1
if (-not $container) {
    throw "Local Supabase database is not running. Run supabase start first."
}

$output = Get-Content -LiteralPath $sqlPath -Raw | docker exec -i $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 2>&1
if ($LASTEXITCODE -ne 0) {
    $safeOutput = ($output | Out-String) -replace '(?i)(bearer\s+)[^\s]+', '$1[REDACTED]'
    throw "Phase 6Q local database conformance failed.`n$safeOutput"
}
if (($output | Out-String) -notmatch "PHASE6Q_LOCAL_CONFORMANCE_PASS") {
    throw "Phase 6Q local database conformance did not emit its completion marker."
}

Write-Output "Phase 6Q local database conformance passed."
Write-Output "Account A/B RLS, safe default, lease, overlap, idempotency, source/LKG, kill, and cleanup transitions were exercised in a rolled-back transaction."
