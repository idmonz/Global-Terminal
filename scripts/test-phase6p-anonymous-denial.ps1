$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)
    $line = Get-Content -LiteralPath (Join-Path (Get-Location) ".env") |
        Where-Object { $_ -match ("^\s*" + [regex]::Escape($Name) + "\s*=") } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return (($line -split "=", 2)[1].Trim()).Trim('"').Trim("'")
}

function Assert-Denied {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Operation,
        [Parameter(Mandatory = $true)][string]$Label
    )
    try {
        & $Operation | Out-Null
        throw "ANONYMOUS_ACCESS_ALLOWED: $Label"
    }
    catch {
        if ($_.Exception.Message -like "ANONYMOUS_ACCESS_ALLOWED:*") { throw }
        $status = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            try { $status = [int]$_.Exception.Response.StatusCode } catch { $status = $null }
        }
        if ($status -notin @(401, 403, 404)) { throw "Unexpected anonymous response for $Label." }
        Write-Host "PASS: $Label denies anonymous access (HTTP $status)" -ForegroundColor Green
    }
}

$url = Get-DotEnvValue "SUPABASE_URL"
$key = Get-DotEnvValue "SUPABASE_PUBLISHABLE_KEY"
if ([string]::IsNullOrWhiteSpace($key)) { $key = Get-DotEnvValue "SUPABASE_ANON_KEY" }
if ([string]::IsNullOrWhiteSpace($url) -or [string]::IsNullOrWhiteSpace($key)) {
    throw "SUPABASE_URL and a publishable/anon key are required."
}
$url = $url.TrimEnd("/")
$headers = @{ apikey = $key }

foreach ($table in @(
    "global_terminal_account_documents",
    "global_terminal_account_document_receipts",
    "global_terminal_account_document_audit"
)) {
    Assert-Denied -Label $table -Operation {
        Invoke-RestMethod -Method Get -Uri "$url/rest/v1/$table`?select=*&limit=1" -Headers $headers
    }
}

$dummy = "0" * 64
Assert-Denied -Label "global_terminal_apply_account_document RPC" -Operation {
    Invoke-RestMethod `
        -Method Post `
        -Uri "$url/rest/v1/rpc/global_terminal_apply_account_document" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body (@{
            p_document_key = "phase6p-anonymous-check"
            p_payload = @{}
            p_document_fingerprint = $dummy
            p_expected_version = 0
            p_idempotency_key = "phase6p-anonymous-apply"
        } | ConvertTo-Json -Compress)
}
Assert-Denied -Label "global_terminal_delete_account_document RPC" -Operation {
    Invoke-RestMethod `
        -Method Post `
        -Uri "$url/rest/v1/rpc/global_terminal_delete_account_document" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body (@{
            p_document_key = "phase6p-anonymous-check"
            p_expected_version = 0
            p_idempotency_key = "phase6p-anonymous-delete"
        } | ConvertTo-Json -Compress)
}

$summary = [ordered]@{
    evidence_version = "phase6p.anonymous.denial.v1"
    captured_at = [DateTime]::UtcNow.ToString("o")
    passed = $true
    table_count = 3
    rpc_count = 2
    identifiers_redacted = $true
    secrets_printed = $false
}
$path = Join-Path (Get-Location) "review_workspace\phase6p_anonymous_denial_summary.json"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
$summary | ConvertTo-Json | Set-Content -LiteralPath $path -Encoding UTF8
$key = $null
Write-Host "Phase 6P anonymous denial passed." -ForegroundColor Green
Write-Host "Redacted summary: review_workspace/phase6p_anonymous_denial_summary.json"
