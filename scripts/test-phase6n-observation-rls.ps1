$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)

    $envPath = Join-Path (Get-Location) ".env"
    if (-not (Test-Path -LiteralPath $envPath)) {
        throw ".env file not found: $envPath"
    }

    $escapedName = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match "^\s*$escapedName\s*=" } |
        Select-Object -Last 1
    if (-not $line) {
        return $null
    }

    $value = ($line -split "=", 2)[1].Trim()
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
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

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        return ([System.BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Get-ResultCount {
    param($Value)

    if ($null -eq $Value) {
        return 0
    }
    return @($Value).Count
}

function Assert-Condition {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) {
        throw "ASSERTION FAILED: $Message"
    }
    Write-Host "PASS: $Message" -ForegroundColor Green
}

function Get-SupabaseSession {
    param(
        [Parameter(Mandatory = $true)][string]$AccountLabel,
        [Parameter(Mandatory = $true)][string]$Email
    )

    $securePassword = Read-Host "$AccountLabel password" -AsSecureString
    $password = ConvertFrom-SecurePassword $securePassword
    try {
        $response = Invoke-RestMethod `
            -Method Post `
            -Uri "$script:SupabaseUrl/auth/v1/token?grant_type=password" `
            -Headers @{ apikey = $script:SupabasePublishableKey } `
            -ContentType "application/json" `
            -Body (@{ email = $Email; password = $password } | ConvertTo-Json -Compress)

        if (-not $response.access_token -or -not $response.user.id) {
            throw "$AccountLabel login response is incomplete."
        }
        Write-Host "PASS: $AccountLabel login" -ForegroundColor Green
        return [PSCustomObject]@{
            UserId = [string]$response.user.id
            AccessToken = [string]$response.access_token
        }
    }
    finally {
        $password = $null
        $securePassword = $null
    }
}

function Invoke-SupabaseRest {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Get", "Post", "Patch", "Delete")]
        [string]$Method,
        [Parameter(Mandatory = $true)][string]$PathAndQuery,
        [Parameter(Mandatory = $true)][string]$AccessToken,
        $Body = $null,
        [string]$Prefer = ""
    )

    $headers = @{
        apikey = $script:SupabasePublishableKey
        Authorization = "Bearer $AccessToken"
    }
    if (-not [string]::IsNullOrWhiteSpace($Prefer)) {
        $headers.Prefer = $Prefer
    }

    $request = @{
        Method = $Method
        Uri = "$script:SupabaseUrl/rest/v1/$PathAndQuery"
        Headers = $headers
    }
    if ($null -ne $Body) {
        $request.ContentType = "application/json"
        $request.Body = $Body | ConvertTo-Json -Depth 20 -Compress
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
        if ($_.Exception.Message -like "EXPECTED_FAILURE_MISSING:*") {
            throw
        }

        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
            catch {
                $statusCode = $null
            }
        }
        if ($statusCode -notin @(400, 401, 403, 404, 409)) {
            throw "Unexpected failure while checking: $Message`n$($_.Exception.Message)"
        }
        Write-Host "PASS: $Message (HTTP $statusCode)" -ForegroundColor Green
    }
}

$script:SupabaseUrl = Get-DotEnvValue "SUPABASE_URL"
$script:SupabasePublishableKey = Get-DotEnvValue "SUPABASE_PUBLISHABLE_KEY"
if ([string]::IsNullOrWhiteSpace($script:SupabasePublishableKey)) {
    $script:SupabasePublishableKey = Get-DotEnvValue "SUPABASE_ANON_KEY"
}

$accountAEmail = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_EMAIL"
$accountBEmail = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_EMAIL"
$accountAUserId = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_USER_ID"
$accountBUserId = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_USER_ID"
$accountATenantId = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_TENANT_ID"
$accountBTenantId = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_TENANT_ID"

$required = @(
    $script:SupabaseUrl,
    $script:SupabasePublishableKey,
    $accountAEmail,
    $accountBEmail,
    $accountAUserId,
    $accountBUserId,
    $accountATenantId,
    $accountBTenantId
)
if ($required | Where-Object { [string]::IsNullOrWhiteSpace($_) }) {
    throw "Supabase URL/key and all six PHASE6M_TEST_ACCOUNT_* values are required in .env."
}

$script:SupabaseUrl = $script:SupabaseUrl.TrimEnd("/")
$sessionA = $null
$sessionB = $null
$createdRunId = $null
$summaryPath = Join-Path (Get-Location) "review_workspace\phase6n_hosted_rls_summary.json"

Write-Host "Phase 6N hosted observation RLS conformance"
Write-Host "Secrets, tokens, emails, user IDs, and tenant IDs will not be printed."

try {
    $sessionA = Get-SupabaseSession -AccountLabel "Account A" -Email $accountAEmail
    $sessionB = Get-SupabaseSession -AccountLabel "Account B" -Email $accountBEmail

    Assert-Condition ($sessionA.UserId -eq $accountAUserId) "Account A identity matches configured UUID"
    Assert-Condition ($sessionB.UserId -eq $accountBUserId) "Account B identity matches configured UUID"
    Assert-Condition ($sessionA.UserId -ne $sessionB.UserId) "Account A/B identities are distinct"
    Assert-Condition ($accountATenantId -ne $accountBTenantId) "Account A/B tenants are distinct"

    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 16)
    $createdRunId = "obsr_$suffix"
    $snapshotId = "obss_$suffix"
    $quotaId = "obsq_$suffix"
    $now = [DateTime]::UtcNow.ToString("o")
    $fingerprint = New-Sha256Hex "phase6n-request-$suffix"
    $contentHash = New-Sha256Hex "phase6n-snapshot-$suffix"

    $run = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_observation_runs" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            run_id = $createdRunId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            watchlist_resource_id = "phase6n-hosted-watchlist"
            idempotency_key = "phase6n-$suffix"
            request_fingerprint = $fingerprint
            status = "queued"
            request_json = @{ mode = "hosted-conformance" }
            plan_json = @{ maximum_symbols = 1; maximum_calls = 0 }
            result_json = @{}
            version = 1
        }
    Assert-Condition ((Get-ResultCount $run) -eq 1) "Account A creates an observation run"

    $createdAudit = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_observation_run_audit?select=event_type&run_id=eq.$createdRunId" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $createdAudit) -eq 1) "Run creation produces immutable audit evidence"

    $snapshot = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_observation_snapshots" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            snapshot_id = $snapshotId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            run_id = $createdRunId
            watchlist_resource_id = "phase6n-hosted-watchlist"
            symbol = "AAPL"
            asset_class = "equity"
            snapshot_status = "fresh"
            source_status = "fixture"
            observed_at = $now
            retrieved_at = $now
            provider = "phase6n-conformance"
            source_url = ""
            confidence = 1.0
            content_hash = $contentHash
            payload_json = @{ price = 100.0; conformance = $true }
            caveat = "Synthetic hosted RLS conformance row."
            data_gap = "No market-provider call was made."
        }
    Assert-Condition ((Get-ResultCount $snapshot) -eq 1) "Account A creates a tenant-qualified snapshot"

    $quota = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_provider_quota_ledger" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            event_id = $quotaId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            run_id = $createdRunId
            provider = "phase6n-conformance"
            operation = "none"
            call_count = 0
            source_status = "fixture"
        }
    Assert-Condition ((Get-ResultCount $quota) -eq 1) "Account A creates a zero-call quota record"

    foreach ($table in @(
        "global_terminal_observation_runs",
        "global_terminal_observation_snapshots",
        "global_terminal_provider_quota_ledger",
        "global_terminal_observation_run_audit"
    )) {
        $bRead = Invoke-SupabaseRest `
            -Method Get `
            -PathAndQuery "$table`?select=*&run_id=eq.$createdRunId" `
            -AccessToken $sessionB.AccessToken
        Assert-Condition ((Get-ResultCount $bRead) -eq 0) "Account B cannot read Account A row from $table"
    }

    $bUpdate = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation" `
        -Body @{ status = "failed"; version = 99 }
    Assert-Condition ((Get-ResultCount $bUpdate) -eq 0) "Account B cannot update Account A run"

    $bDelete = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $bDelete) -eq 0) "Account B cannot delete Account A run"

    Invoke-ExpectedFailure -Message "Account B cannot insert into Account A tenant" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_observation_runs" `
            -AccessToken $sessionB.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                run_id = "cross_$suffix"
                tenant_id = $accountATenantId
                owner_user_id = $sessionB.UserId
                watchlist_resource_id = "phase6n-cross-tenant"
                idempotency_key = "phase6n-cross-$suffix"
                request_fingerprint = (New-Sha256Hex "cross-$suffix")
                status = "queued"
            }
    }

    Invoke-ExpectedFailure -Message "Composite foreign key blocks cross-tenant parent linkage" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_observation_snapshots" `
            -AccessToken $sessionB.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                snapshot_id = "crosss_$suffix"
                tenant_id = $accountBTenantId
                owner_user_id = $sessionB.UserId
                run_id = $createdRunId
                watchlist_resource_id = "phase6n-cross-parent"
                symbol = "MSFT"
                snapshot_status = "fresh"
                source_status = "fixture"
                retrieved_at = $now
                content_hash = (New-Sha256Hex "cross-snapshot-$suffix")
                payload_json = @{}
            }
    }

    Invoke-ExpectedFailure -Message "Authenticated clients cannot forge audit rows" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_observation_run_audit" `
            -AccessToken $sessionA.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                event_id = "forge_$suffix"
                tenant_id = $accountATenantId
                owner_user_id = $sessionA.UserId
                run_id = $createdRunId
                event_type = "forged"
            }
    }

    $running = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId&version=eq.1" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ status = "running"; version = 2; started_at = $now; updated_at = $now }
    Assert-Condition ((Get-ResultCount $running) -eq 1) "Account A advances run with the expected version"

    $stale = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId&version=eq.1" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ status = "failed"; version = 3; updated_at = $now }
    Assert-Condition ((Get-ResultCount $stale) -eq 0) "Stale optimistic update changes zero rows"

    $completed = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId&version=eq.2" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ status = "completed"; version = 3; completed_at = $now; updated_at = $now }
    Assert-Condition ((Get-ResultCount $completed) -eq 1) "Account A completes the run with the current version"

    $auditBeforeDelete = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_observation_run_audit?select=event_type&run_id=eq.$createdRunId" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $auditBeforeDelete) -eq 3) "Create and status transitions are audited"

    $deleted = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $deleted) -eq 1) "Account A deletes its own run"
    $createdRunId = $null

    foreach ($table in @(
        "global_terminal_observation_runs",
        "global_terminal_observation_snapshots",
        "global_terminal_provider_quota_ledger"
    )) {
        $afterDelete = Invoke-SupabaseRest `
            -Method Get `
            -PathAndQuery "$table`?select=*&run_id=eq.obsr_$suffix" `
            -AccessToken $sessionA.AccessToken
        Assert-Condition ((Get-ResultCount $afterDelete) -eq 0) "Run deletion removes bounded data from $table"
    }

    $retainedAudit = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_observation_run_audit?select=event_type&run_id=eq.obsr_$suffix" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $retainedAudit) -eq 4) "Audit evidence survives parent deletion"

    $bRetainedAudit = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_observation_run_audit?select=event_type&run_id=eq.obsr_$suffix" `
        -AccessToken $sessionB.AccessToken
    Assert-Condition ((Get-ResultCount $bRetainedAudit) -eq 0) "Retained audit evidence remains isolated from Account B"

    $summary = [ordered]@{
        evidence_version = "phase6n.hosted.rls.v1"
        captured_at = [DateTime]::UtcNow.ToString("o")
        passed = $true
        account_isolation = $true
        optimistic_conflict = $true
        composite_parent_integrity = $true
        audit_immutable = $true
        audit_retained_after_delete = $true
        provider_calls = 0
        identifiers_redacted = $true
        secrets_printed = $false
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $summaryPath) | Out-Null
    $summary | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    Write-Host "Phase 6N hosted RLS conformance passed." -ForegroundColor Green
    Write-Host "Redacted summary: review_workspace/phase6n_hosted_rls_summary.json"
}
finally {
    if ($createdRunId -and $sessionA -and $sessionA.AccessToken) {
        try {
            Invoke-SupabaseRest `
                -Method Delete `
                -PathAndQuery "global_terminal_observation_runs?run_id=eq.$createdRunId" `
                -AccessToken $sessionA.AccessToken | Out-Null
        }
        catch {
            Write-Warning "Best-effort cleanup did not complete. Review the run by its redacted test timestamp."
        }
    }
    if ($sessionA) { $sessionA.AccessToken = $null }
    if ($sessionB) { $sessionB.AccessToken = $null }
    $script:SupabasePublishableKey = $null
}
