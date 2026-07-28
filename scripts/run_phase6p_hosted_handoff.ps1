param(
    [ValidateRange(5, 50)][int]$LatencySampleCount = 10,
    [switch]$PreflightOnly,
    [switch]$ResumeRecovery
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$accountAPassword = $null
$accountBPassword = $null

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)
    $line = Get-Content -LiteralPath (Join-Path $repoRoot ".env") |
        Where-Object { $_ -match ("^\s*" + [regex]::Escape($Name) + "\s*=") } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return (($line -split "=", 2)[1].Trim()).Trim('"').Trim("'")
}

function Read-RedactedSummary {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$ExpectedEvidenceVersion,
        [Parameter(Mandatory = $true)][string[]]$ForbiddenValues,
        [string[]]$RequiredTrueFields = @(),
        [Nullable[DateTime]]$NotBeforeUtc = $null
    )
    $path = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path)) { throw "Expected redacted summary is missing: $RelativePath" }
    $raw = Get-Content -LiteralPath $path -Raw
    $summary = $raw | ConvertFrom-Json
    if ($summary.evidence_version -ne $ExpectedEvidenceVersion) {
        throw "Unexpected evidence version in ${RelativePath}: $($summary.evidence_version)"
    }
    if ($summary.passed -ne $true) { throw "Hosted evidence did not pass: $RelativePath" }
    foreach ($field in $RequiredTrueFields) {
        $property = $summary.PSObject.Properties[$field]
        if ($null -eq $property -or $property.Value -ne $true) {
            throw "Hosted evidence is missing required assertion '${field}': $RelativePath"
        }
    }
    if ($NotBeforeUtc.HasValue) {
        try {
            $capturedAt = [DateTimeOffset]::Parse(
                [string]$summary.captured_at,
                [Globalization.CultureInfo]::InvariantCulture,
                [Globalization.DateTimeStyles]::RoundtripKind
            )
        }
        catch {
            throw "Hosted evidence has an invalid captured_at clock: $RelativePath"
        }
        if ($capturedAt.UtcDateTime -lt $NotBeforeUtc.Value.AddSeconds(-2)) {
            throw "Hosted evidence predates the current handoff step: $RelativePath"
        }
    }
    foreach ($value in $ForbiddenValues) {
        if (-not [string]::IsNullOrWhiteSpace($value) -and $raw.Contains($value)) {
            throw "Hosted evidence contains a configured private identifier: $RelativePath"
        }
    }
    if ($summary.secrets_printed -ne $false -or $summary.identifiers_redacted -ne $true) {
        throw "Hosted evidence is missing its privacy assertions: $RelativePath"
    }
    return $summary
}

function Invoke-HandoffStep {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][scriptblock]$Operation
    )
    Write-Host ""
    Write-Host "========================================"
    Write-Host $Label
    Write-Host "========================================"
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    & $Operation | Out-Host
    $watch.Stop()
    return [Math]::Round($watch.Elapsed.TotalSeconds, 3)
}

Push-Location $repoRoot

try {
    if ($PreflightOnly -and $ResumeRecovery) {
        throw "PreflightOnly and ResumeRecovery cannot be used together."
    }
    $supabaseUrl = Get-DotEnvValue "SUPABASE_URL"
    $publishableKey = Get-DotEnvValue "SUPABASE_PUBLISHABLE_KEY"
    if ([string]::IsNullOrWhiteSpace($publishableKey)) {
        $publishableKey = Get-DotEnvValue "SUPABASE_ANON_KEY"
    }
    if ([string]::IsNullOrWhiteSpace($supabaseUrl) -or [string]::IsNullOrWhiteSpace($publishableKey)) {
        throw "SUPABASE_URL and a Supabase publishable/anon key are required in .env."
    }

    $forbiddenValues = @(
        (Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_EMAIL")
        (Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_EMAIL")
        (Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_USER_ID")
        (Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_USER_ID")
        (Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_TENANT_ID")
        (Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_TENANT_ID")
    )
    if ($forbiddenValues | Where-Object { [string]::IsNullOrWhiteSpace($_) }) {
        throw "All six PHASE6M_TEST_ACCOUNT_* identity values are required in .env."
    }

    $phase6n = Read-RedactedSummary `
        -RelativePath "review_workspace\phase6n_hosted_rls_summary.json" `
        -ExpectedEvidenceVersion "phase6n.hosted.rls.v1" `
        -ForbiddenValues $forbiddenValues `
        -RequiredTrueFields @("account_isolation", "optimistic_conflict", "composite_parent_integrity", "audit_immutable", "audit_retained_after_delete")

    $childScripts = @(
        "test-phase6o-alert-rls.ps1"
        "test-phase6p-account-continuity-rls.ps1"
        "test-phase6p-product-recovery.ps1"
    )
    foreach ($scriptName in $childScripts) {
        $tokens = $null
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile(
            (Join-Path $PSScriptRoot $scriptName),
            [ref]$tokens,
            [ref]$errors
        ) | Out-Null
        if ($errors.Count) { throw "PowerShell parse failure in $scriptName." }
    }
    $migrationPath = Join-Path $repoRoot "supabase\migrations\20260715180000_phase6p_account_continuity.sql"
    if (-not (Test-Path -LiteralPath $migrationPath)) { throw "Phase 6P migration is missing." }

    $runtimePreflightStartedAt = [DateTime]::UtcNow
    Write-Host "Validating isolated product-recovery runtime before requesting passwords..."
    & (Join-Path $PSScriptRoot "test-phase6p-product-recovery.ps1") -RuntimePreflightOnly | Out-Host
    $runtimePreflight = Read-RedactedSummary `
        -RelativePath "review_workspace\phase6p_product_recovery_runtime_preflight_summary.json" `
        -ExpectedEvidenceVersion "phase6p.product.recovery.runtime-preflight.v1" `
        -ForbiddenValues $forbiddenValues `
        -RequiredTrueFields @("runtime_env_injected", "supabase_configured", "hosted_auth_enabled", "hosted_sign_in_available", "anonymous_session") `
        -NotBeforeUtc $runtimePreflightStartedAt
    if (
        $runtimePreflight.remote_contacted -ne $false -or
        [int]$runtimePreflight.market_provider_calls -ne 0 -or
        [string]$runtimePreflight.source_status -ne "configured-unverified"
    ) {
        throw "Phase 6P isolated runtime preflight crossed its no-contact trust boundary."
    }

    if ($PreflightOnly) {
        $preflight = [ordered]@{
            evidence_version = "phase6p.hosted.handoff.preflight.v1"
            captured_at = [DateTime]::UtcNow.ToString("o")
            passed = $true
            supabase_configured = $true
            account_metadata_configured = $true
            inherited_phase6n_passed = [bool]$phase6n.passed
            phase6p_migration_present = $true
            child_script_count = $childScripts.Count
            child_scripts_parse = $true
            isolated_runtime_preflight_passed = [bool]$runtimePreflight.passed
            runtime_env_injected = [bool]$runtimePreflight.runtime_env_injected
            hosted_sign_in_available = [bool]$runtimePreflight.hosted_sign_in_available
            remote_contacted = $false
            identifiers_redacted = $true
            secrets_printed = $false
        }
        $preflightPath = Join-Path $repoRoot "review_workspace\phase6p_hosted_handoff_preflight_summary.json"
        $preflight | ConvertTo-Json | Set-Content -LiteralPath $preflightPath -Encoding UTF8
        Write-Host "Phase 6P hosted handoff preflight passed." -ForegroundColor Green
        Write-Host "No password prompt, Supabase auth request, hosted mutation, or provider request was made."
        Write-Host "Redacted summary: review_workspace/phase6p_hosted_handoff_preflight_summary.json"
        return
    }

    Write-Host "Phase 6P hosted owner handoff"
    if ($ResumeRecovery) {
        Write-Host "Resume mode revalidates recent Phase 6O/6P RLS evidence and reruns recovery only."
    }
    Write-Host "Passwords are requested once and remain SecureString references between in-process scripts."
    Write-Host "Passwords, tokens, emails, user IDs, tenant IDs, and payload rows will not be printed."
    $accountAPassword = Read-Host "Account A password" -AsSecureString
    $accountBPassword = Read-Host "Account B password" -AsSecureString

    if ($ResumeRecovery) {
        $reuseNotBeforeUtc = [DateTime]::UtcNow.AddHours(-24)
        $phase6oSeconds = 0.0
        $phase6o = Read-RedactedSummary `
            -RelativePath "review_workspace\phase6o_hosted_rls_summary.json" `
            -ExpectedEvidenceVersion "phase6o.hosted.rls.v1" `
            -ForbiddenValues $forbiddenValues `
            -RequiredTrueFields @("hosted_persistence_verified", "account_isolation", "cross_tenant_insert_blocked", "composite_parent_integrity", "optimistic_conflict", "worker_recovery_state", "audit_immutable", "audit_retained_after_delete") `
            -NotBeforeUtc $reuseNotBeforeUtc
        $phase6pRlsSeconds = 0.0
        $phase6pRls = Read-RedactedSummary `
            -RelativePath "review_workspace\phase6p_hosted_rls_summary.json" `
            -ExpectedEvidenceVersion "phase6p.hosted.rls.v1" `
            -ForbiddenValues $forbiddenValues `
            -RequiredTrueFields @("account_isolation", "server_derived_tenant", "idempotency", "optimistic_conflict", "audit_immutable", "audit_retained_after_delete", "product_document_untouched") `
            -NotBeforeUtc $reuseNotBeforeUtc
        Write-Host "PASS: Recent Phase 6O and Phase 6P RLS evidence revalidated" -ForegroundColor Green
    }
    else {
        $phase6oStartedAt = [DateTime]::UtcNow
        $phase6oSeconds = Invoke-HandoffStep -Label "1/3 Phase 6O Alert Manager hosted RLS" -Operation {
            & (Join-Path $PSScriptRoot "test-phase6o-alert-rls.ps1") `
                -AccountAPassword $accountAPassword `
                -AccountBPassword $accountBPassword
        }
        $phase6o = Read-RedactedSummary `
            -RelativePath "review_workspace\phase6o_hosted_rls_summary.json" `
            -ExpectedEvidenceVersion "phase6o.hosted.rls.v1" `
            -ForbiddenValues $forbiddenValues `
            -RequiredTrueFields @("hosted_persistence_verified", "account_isolation", "cross_tenant_insert_blocked", "composite_parent_integrity", "optimistic_conflict", "worker_recovery_state", "audit_immutable", "audit_retained_after_delete") `
            -NotBeforeUtc $phase6oStartedAt

        $phase6pRlsStartedAt = [DateTime]::UtcNow
        $phase6pRlsSeconds = Invoke-HandoffStep -Label "2/3 Phase 6P account document hosted RLS and latency" -Operation {
            & (Join-Path $PSScriptRoot "test-phase6p-account-continuity-rls.ps1") `
                -AccountAPassword $accountAPassword `
                -AccountBPassword $accountBPassword `
                -LatencySampleCount $LatencySampleCount
        }
        $phase6pRls = Read-RedactedSummary `
            -RelativePath "review_workspace\phase6p_hosted_rls_summary.json" `
            -ExpectedEvidenceVersion "phase6p.hosted.rls.v1" `
            -ForbiddenValues $forbiddenValues `
            -RequiredTrueFields @("account_isolation", "server_derived_tenant", "idempotency", "optimistic_conflict", "audit_immutable", "audit_retained_after_delete", "product_document_untouched") `
            -NotBeforeUtc $phase6pRlsStartedAt
    }
    if ([int]$phase6o.provider_calls -ne 0 -or $phase6o.hosted_scheduler_verified -ne $false) {
        throw "Phase 6O evidence has an invalid provider/scheduler boundary."
    }
    if ([int]$phase6pRls.provider_calls -ne 0 -or [int]$phase6pRls.hosted_latency.sample_count -ne $LatencySampleCount) {
        throw "Phase 6P hosted RLS evidence has an invalid provider or latency sample boundary."
    }
    foreach ($metric in @("read_p50_ms", "read_p95_ms", "idempotent_rpc_p50_ms", "idempotent_rpc_p95_ms")) {
        $metricProperty = $phase6pRls.hosted_latency.PSObject.Properties[$metric]
        if ($null -eq $metricProperty -or [double]$metricProperty.Value -lt 0) {
            throw "Phase 6P hosted latency evidence is missing a valid ${metric}."
        }
    }

    $phase6pRecoveryStartedAt = [DateTime]::UtcNow
    $phase6pRecoverySeconds = Invoke-HandoffStep -Label "3/3 Phase 6P two-repository product recovery" -Operation {
        & (Join-Path $PSScriptRoot "test-phase6p-product-recovery.ps1") `
            -AccountAPassword $accountAPassword `
            -AccountBPassword $accountBPassword
    }
    $phase6pRecovery = Read-RedactedSummary `
        -RelativePath "review_workspace\phase6p_product_recovery_summary.json" `
        -ExpectedEvidenceVersion "phase6p.product.recovery.v1" `
        -ForbiddenValues $forbiddenValues `
        -RequiredTrueFields @("supabase_session", "server_derived_tenant", "hosted_write", "new_repository_restore", "account_b_isolated", "cleanup_reconciled") `
        -NotBeforeUtc $phase6pRecoveryStartedAt
    if ([int]$phase6pRecovery.market_provider_calls -ne 0) {
        throw "Phase 6P product recovery evidence has an invalid provider-call boundary."
    }

    $combined = [ordered]@{
        evidence_version = "phase6p.hosted.handoff.v1"
        captured_at = [DateTime]::UtcNow.ToString("o")
        passed = $true
        inherited_phase6n_passed = [bool]$phase6n.passed
        phase6o_hosted_rls_passed = [bool]$phase6o.passed
        phase6p_hosted_rls_passed = [bool]$phase6pRls.passed
        phase6p_product_recovery_passed = [bool]$phase6pRecovery.passed
        evidence_freshness_verified = $true
        resumed_from_verified_rls = [bool]$ResumeRecovery
        evidence_reuse_window_hours = $(if ($ResumeRecovery) { 24 } else { 0 })
        child_evidence_versions = [ordered]@{
            phase6n = [string]$phase6n.evidence_version
            phase6o = [string]$phase6o.evidence_version
            phase6p_rls = [string]$phase6pRls.evidence_version
            phase6p_product_recovery = [string]$phase6pRecovery.evidence_version
        }
        elapsed_seconds = [ordered]@{
            phase6o = $phase6oSeconds
            phase6p_rls = $phase6pRlsSeconds
            phase6p_product_recovery = $phase6pRecoverySeconds
        }
        hosted_latency = $phase6pRls.hosted_latency
        hosted_scheduler_verified = $false
        market_provider_calls = 0
        identifiers_redacted = $true
        secrets_printed = $false
    }
    $summaryPath = Join-Path $repoRoot "review_workspace\phase6p_hosted_handoff_summary.json"
    $combined | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

    Write-Host ""
    Write-Host "Phase 6P hosted owner handoff passed." -ForegroundColor Green
    Write-Host "Hosted scheduling remains unverified and disabled."
    Write-Host "Redacted summary: review_workspace/phase6p_hosted_handoff_summary.json"
}
finally {
    $accountAPassword = $null
    $accountBPassword = $null
    Pop-Location
}
