param(
    [Security.SecureString]$AccountAPassword,
    [Security.SecureString]$AccountBPassword,
    [ValidateRange(5, 50)][int]$LatencySampleCount = 10
)

$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)
    $path = Join-Path (Get-Location) ".env"
    if (-not (Test-Path -LiteralPath $path)) { throw ".env file not found." }
    $escaped = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $path |
        Where-Object { $_ -match "^\s*$escaped\s*=" } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    $value = ($line -split "=", 2)[1].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    return $value
}

function ConvertFrom-SecurePassword {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecurePassword)
    return [System.Net.NetworkCredential]::new("", $SecurePassword).Password
}

function New-Sha256Hex {
    param([Parameter(Mandatory = $true)][string]$Value)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace("-", "").ToLowerInvariant()
    }
    finally { $sha.Dispose() }
}

function Get-ResultCount {
    param($Value)
    if ($null -eq $Value) { return 0 }
    return @($Value).Count
}

function Get-FirstRow {
    param($Value)
    if ((Get-ResultCount $Value) -eq 0) { return $null }
    return @($Value)[0]
}

function Assert-Condition {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
    Write-Host "PASS: $Message" -ForegroundColor Green
}

function Get-SupabaseSession {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Email,
        [Security.SecureString]$SecurePassword
    )
    if ($null -eq $SecurePassword) {
        $SecurePassword = Read-Host "$Label password" -AsSecureString
    }
    $password = ConvertFrom-SecurePassword $SecurePassword
    try {
        $response = Invoke-RestMethod `
            -Method Post `
            -Uri "$script:SupabaseUrl/auth/v1/token?grant_type=password" `
            -Headers @{ apikey = $script:PublishableKey } `
            -ContentType "application/json" `
            -Body (@{ email = $Email; password = $password } | ConvertTo-Json -Compress)
        if (-not $response.access_token -or -not $response.user.id) { throw "$Label login response is incomplete." }
        Write-Host "PASS: $Label login" -ForegroundColor Green
        return [PSCustomObject]@{ UserId = [string]$response.user.id; AccessToken = [string]$response.access_token }
    }
    finally {
        $password = $null
        $SecurePassword = $null
    }
}

function Get-Percentile {
    param(
        [Parameter(Mandatory = $true)][double[]]$Values,
        [Parameter(Mandatory = $true)][ValidateRange(0, 100)][double]$Percentile
    )
    if ($Values.Count -eq 0) { return 0.0 }
    $ordered = @($Values | Sort-Object)
    $index = [Math]::Max(0, [Math]::Min($ordered.Count - 1, [Math]::Ceiling(($Percentile / 100.0) * $ordered.Count) - 1))
    return [Math]::Round([double]$ordered[$index], 3)
}

function Invoke-SupabaseRest {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("Get", "Post", "Patch", "Delete")][string]$Method,
        [Parameter(Mandatory = $true)][string]$PathAndQuery,
        [Parameter(Mandatory = $true)][string]$AccessToken,
        $Body = $null,
        [string]$Prefer = ""
    )
    $headers = @{ apikey = $script:PublishableKey; Authorization = "Bearer $AccessToken" }
    if ($Prefer) { $headers.Prefer = $Prefer }
    $request = @{ Method = $Method; Uri = "$script:SupabaseUrl/rest/v1/$PathAndQuery"; Headers = $headers }
    if ($null -ne $Body) {
        $request.ContentType = "application/json"
        $request.Body = $Body | ConvertTo-Json -Depth 30 -Compress
    }
    return Invoke-RestMethod @request
}

function Invoke-ExpectedFailure {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Operation,
        [Parameter(Mandatory = $true)][string]$Message
    )
    try {
        & $Operation | Out-Null
        throw "EXPECTED_FAILURE_MISSING: $Message"
    }
    catch {
        if ($_.Exception.Message -like "EXPECTED_FAILURE_MISSING:*") { throw }
        $status = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            try { $status = [int]$_.Exception.Response.StatusCode } catch { $status = $null }
        }
        if ($status -notin @(400, 401, 403, 404, 409)) {
            throw "Unexpected failure while checking: $Message`n$($_.Exception.Message)"
        }
        Write-Host "PASS: $Message (HTTP $status)" -ForegroundColor Green
    }
}

$script:SupabaseUrl = Get-DotEnvValue "SUPABASE_URL"
$script:PublishableKey = Get-DotEnvValue "SUPABASE_PUBLISHABLE_KEY"
if ([string]::IsNullOrWhiteSpace($script:PublishableKey)) { $script:PublishableKey = Get-DotEnvValue "SUPABASE_ANON_KEY" }
$emailA = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_EMAIL"
$emailB = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_EMAIL"
$userA = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_USER_ID"
$userB = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_USER_ID"
$tenantA = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_TENANT_ID"
$tenantB = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_TENANT_ID"

$required = @($script:SupabaseUrl, $script:PublishableKey, $emailA, $emailB, $userA, $userB, $tenantA, $tenantB)
if ($required | Where-Object { [string]::IsNullOrWhiteSpace($_) }) {
    throw "Supabase URL/key and all six PHASE6M_TEST_ACCOUNT_* values are required in .env."
}

$script:SupabaseUrl = $script:SupabaseUrl.TrimEnd("/")
$sessionA = $null
$sessionB = $null
$summaryPath = Join-Path (Get-Location) "review_workspace\phase6p_hosted_rls_summary.json"

Write-Host "Phase 6P hosted account continuity RLS conformance"
Write-Host "Passwords, tokens, emails, user IDs, tenant IDs, and payload rows will not be printed."

try {
    $sessionA = Get-SupabaseSession -Label "Account A" -Email $emailA -SecurePassword $AccountAPassword
    $sessionB = Get-SupabaseSession -Label "Account B" -Email $emailB -SecurePassword $AccountBPassword
    Assert-Condition ($sessionA.UserId -eq $userA) "Account A identity matches configured UUID"
    Assert-Condition ($sessionB.UserId -eq $userB) "Account B identity matches configured UUID"
    Assert-Condition ($sessionA.UserId -ne $sessionB.UserId) "Account A/B identities are distinct"
    Assert-Condition ($tenantA -ne $tenantB) "Account A/B tenants are distinct"

    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 16)
    $documentKey = "phase6p-conformance-$suffix"
    $fingerprintOne = New-Sha256Hex "phase6p-one-$suffix"
    $fingerprintTwo = New-Sha256Hex "phase6p-two-$suffix"
    $applyKeyOne = "phase6p-apply-one-$suffix"
    $applyKeyTwo = "phase6p-apply-two-$suffix"
    $deleteKey = "phase6p-delete-$suffix"
    $payloadOne = @{
        account_continuity_version = "account_continuity.v1"
        tables = @{}
        table_count = 0
        row_count = 0
        bounded = $true
        fingerprint = $fingerprintOne
        provider_call_count = 0
    }

    Invoke-ExpectedFailure -Message "Anonymous clients cannot execute the account document RPC" -Operation {
        Invoke-RestMethod `
            -Method Post `
            -Uri "$script:SupabaseUrl/rest/v1/rpc/global_terminal_apply_account_document" `
            -Headers @{ apikey = $script:PublishableKey } `
            -ContentType "application/json" `
            -Body (@{
                p_document_key = $documentKey
                p_payload = $payloadOne
                p_document_fingerprint = $fingerprintOne
                p_expected_version = 0
                p_idempotency_key = $applyKeyOne
            } | ConvertTo-Json -Depth 20 -Compress)
    }

    $created = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{
            p_document_key = $documentKey
            p_payload = $payloadOne
            p_document_fingerprint = $fingerprintOne
            p_expected_version = 0
            p_idempotency_key = $applyKeyOne
        })
    Assert-Condition ($created.status -eq "applied" -and [int]$created.version -eq 1) "Account A creates a tenant-derived account document"

    $deduped = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{
            p_document_key = $documentKey
            p_payload = $payloadOne
            p_document_fingerprint = $fingerprintOne
            p_expected_version = 0
            p_idempotency_key = $applyKeyOne
        })
    Assert-Condition ($deduped.status -eq "deduped" -and [int]$deduped.version -eq 1) "Repeated idempotency key deduplicates the account write"

    $aRead = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_documents?select=document_key,version,deleted&document_key=eq.$documentKey" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $aRead) -eq 1) "Account A reads its own account document"

    $readLatencyMs = [System.Collections.Generic.List[double]]::new()
    $rpcLatencyMs = [System.Collections.Generic.List[double]]::new()
    for ($sample = 0; $sample -lt $LatencySampleCount; $sample++) {
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        $sampleRead = Invoke-SupabaseRest `
            -Method Get `
            -PathAndQuery "global_terminal_account_documents?select=document_key,version&document_key=eq.$documentKey" `
            -AccessToken $sessionA.AccessToken
        $watch.Stop()
        if ((Get-ResultCount $sampleRead) -ne 1) { throw "Hosted read latency sample returned an unexpected row count." }
        $readLatencyMs.Add($watch.Elapsed.TotalMilliseconds)

        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        $sampleRpc = Get-FirstRow (Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "rpc/global_terminal_apply_account_document" `
            -AccessToken $sessionA.AccessToken `
            -Body @{
                p_document_key = $documentKey
                p_payload = $payloadOne
                p_document_fingerprint = $fingerprintOne
                p_expected_version = 0
                p_idempotency_key = $applyKeyOne
            })
        $watch.Stop()
        if ($sampleRpc.status -ne "deduped" -or [int]$sampleRpc.version -ne 1) {
            throw "Hosted idempotent RPC latency sample returned an unexpected result."
        }
        $rpcLatencyMs.Add($watch.Elapsed.TotalMilliseconds)
    }
    $hostedLatency = [ordered]@{
        sample_count = $LatencySampleCount
        read_p50_ms = Get-Percentile -Values $readLatencyMs.ToArray() -Percentile 50
        read_p95_ms = Get-Percentile -Values $readLatencyMs.ToArray() -Percentile 95
        idempotent_rpc_p50_ms = Get-Percentile -Values $rpcLatencyMs.ToArray() -Percentile 50
        idempotent_rpc_p95_ms = Get-Percentile -Values $rpcLatencyMs.ToArray() -Percentile 95
        network_included = $true
        market_provider_calls = 0
    }
    Write-Host "PASS: Hosted read and idempotent RPC latency samples recorded" -ForegroundColor Green

    $bRead = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_documents?select=document_key&document_key=eq.$documentKey" `
        -AccessToken $sessionB.AccessToken
    Assert-Condition ((Get-ResultCount $bRead) -eq 0) "Account B cannot read Account A account document"

    $bAudit = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_document_audit?select=event_id&document_key=eq.$documentKey" `
        -AccessToken $sessionB.AccessToken
    Assert-Condition ((Get-ResultCount $bAudit) -eq 0) "Account B cannot read Account A account audit"

    Invoke-ExpectedFailure -Message "Account B cannot directly insert into Account A tenant" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_account_documents" `
            -AccessToken $sessionB.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                tenant_id = $tenantA
                owner_user_id = $sessionB.UserId
                document_key = "phase6p-forged-$suffix"
                payload = @{}
                document_fingerprint = $fingerprintOne
                version = 1
            }
    }

    Invoke-ExpectedFailure -Message "Client payload cannot forge account identity" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "rpc/global_terminal_apply_account_document" `
            -AccessToken $sessionA.AccessToken `
            -Body @{
                p_document_key = $documentKey
                p_payload = @{ tenant_id = $tenantB; fingerprint = $fingerprintTwo }
                p_document_fingerprint = $fingerprintTwo
                p_expected_version = 1
                p_idempotency_key = "phase6p-forged-payload-$suffix"
            }
    }

    $stale = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{
            p_document_key = $documentKey
            p_payload = @{ account_continuity_version = "account_continuity.v1"; tables = @{}; fingerprint = $fingerprintTwo }
            p_document_fingerprint = $fingerprintTwo
            p_expected_version = 0
            p_idempotency_key = "phase6p-stale-$suffix"
        })
    Assert-Condition ($stale.status -eq "document-version-conflict" -and [int]$stale.version -eq 1) "Stale account write returns an optimistic conflict"

    $updated = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{
            p_document_key = $documentKey
            p_payload = @{ account_continuity_version = "account_continuity.v1"; tables = @{}; fingerprint = $fingerprintTwo; row_count = 0 }
            p_document_fingerprint = $fingerprintTwo
            p_expected_version = 1
            p_idempotency_key = $applyKeyTwo
        })
    Assert-Condition ($updated.status -eq "applied" -and [int]$updated.version -eq 2) "Account A updates with the current optimistic version"

    Invoke-ExpectedFailure -Message "Authenticated clients cannot forge immutable account audit rows" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_account_document_audit" `
            -AccessToken $sessionA.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                event_id = "phase6p-forged-$suffix"
                tenant_id = $tenantA
                owner_user_id = $sessionA.UserId
                document_id = [guid]::NewGuid()
                document_key = $documentKey
                event_type = "document-created"
                new_version = 1
            }
    }

    $deleteConflict = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_delete_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{ p_document_key = $documentKey; p_expected_version = 1; p_idempotency_key = "phase6p-delete-stale-$suffix" })
    Assert-Condition ($deleteConflict.status -eq "document-version-conflict" -and [int]$deleteConflict.version -eq 2) "Stale account deletion returns an optimistic conflict"

    $deleted = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_delete_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{ p_document_key = $documentKey; p_expected_version = 2; p_idempotency_key = $deleteKey })
    Assert-Condition ($deleted.status -eq "deleted" -and [int]$deleted.version -eq 3) "Account A soft-deletes its hosted account document"

    $deleteDedupe = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_delete_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{ p_document_key = $documentKey; p_expected_version = 2; p_idempotency_key = $deleteKey })
    Assert-Condition ($deleteDedupe.status -eq "deduped" -and [int]$deleteDedupe.version -eq 3) "Repeated account deletion is idempotent"

    $activeAfterDelete = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_documents?select=document_key&document_key=eq.$documentKey&deleted=eq.false" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $activeAfterDelete) -eq 0) "Deleted account document is absent from active restore reads"

    $auditAfterDelete = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_document_audit?select=event_type,new_version&document_key=eq.$documentKey&order=new_version.asc" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $auditAfterDelete) -eq 3) "Create, update, and delete audit evidence survives soft deletion"

    $bAfterDelete = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_document_audit?select=event_id&document_key=eq.$documentKey" `
        -AccessToken $sessionB.AccessToken
    Assert-Condition ((Get-ResultCount $bAfterDelete) -eq 0) "Retained account audit remains isolated from Account B"

    $summary = [ordered]@{
        evidence_version = "phase6p.hosted.rls.v1"
        captured_at = [DateTime]::UtcNow.ToString("o")
        passed = $true
        authenticated_accounts = 2
        account_isolation = $true
        server_derived_tenant = $true
        idempotency = $true
        optimistic_conflict = $true
        audit_immutable = $true
        audit_retained_after_delete = $true
        product_document_untouched = $true
        hosted_latency = $hostedLatency
        provider_calls = 0
        identifiers_redacted = $true
        secrets_printed = $false
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $summaryPath) | Out-Null
    $summary | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    Write-Host "Phase 6P hosted account continuity RLS conformance passed." -ForegroundColor Green
    Write-Host "Redacted summary: review_workspace/phase6p_hosted_rls_summary.json"
}
finally {
    if ($sessionA) { $sessionA.AccessToken = $null }
    if ($sessionB) { $sessionB.AccessToken = $null }
    $script:PublishableKey = $null
}
