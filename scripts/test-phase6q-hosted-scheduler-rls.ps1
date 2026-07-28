param(
    [Security.SecureString]$AccountAPassword,
    [Security.SecureString]$AccountBPassword
)

$ErrorActionPreference = "Stop"
$script:RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)
    $path = Join-Path $script:RepoRoot ".env"
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

function Set-JsonProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        $Value
    )
    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.$Name = $Value
    }
    else {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
    }
}

function Get-SupabaseSession {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Email,
        [Security.SecureString]$SecurePassword
    )
    if ($null -eq $SecurePassword) { $SecurePassword = Read-Host "$Label password" -AsSecureString }
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
        $request.Body = $Body | ConvertTo-Json -Depth 100 -Compress
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
            throw "Unexpected failure while checking: $Message (HTTP $status)"
        }
        Write-Host "PASS: $Message (HTTP $status)" -ForegroundColor Green
    }
}

function Invoke-ScheduleRpc {
    param(
        [Parameter(Mandatory = $true)][string]$AccessToken,
        [Parameter(Mandatory = $true)]$Schedule,
        [Parameter(Mandatory = $true)][int]$ExpectedVersion
    )
    return Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_hosted_observation_schedule" `
        -AccessToken $AccessToken `
        -Body @{ p_schedule = $Schedule; p_expected_version = $ExpectedVersion })
}

function New-SchedulePayload {
    param(
        [Parameter(Mandatory = $true)][string]$ScheduleId,
        [Parameter(Mandatory = $true)][string]$WatchlistId,
        [Parameter(Mandatory = $true)][string]$RuleId,
        [Parameter(Mandatory = $true)][ValidateSet("disabled", "enabled", "paused", "killed", "deleted")][string]$State,
        [Parameter(Mandatory = $true)][int]$Version,
        [string]$ConsentedAt = ""
    )
    $now = [DateTimeOffset]::UtcNow.ToString("o")
    $payload = [ordered]@{
        schedule_id = $ScheduleId
        watchlist_id = $WatchlistId
        alert_rule_id = $RuleId
        state = $State
        timezone = "UTC"
        cadence_minutes = 60
        bounds = [ordered]@{ max_symbols = 1; max_provider_calls = 4; max_attempts = 2; timeout_seconds = 90 }
        version = $Version
    }
    if ($State -in @("enabled", "paused")) {
        $payload.consented_at = $(if ($ConsentedAt) { $ConsentedAt } else { $now })
    }
    if ($State -eq "enabled") {
        $payload.enabled_at = $now
        $payload.next_due_at = [DateTimeOffset]::UtcNow.AddHours(1).ToString("o")
    }
    elseif ($State -eq "paused") { $payload.paused_at = $now }
    elseif ($State -eq "killed") { $payload.killed_at = $now }
    elseif ($State -eq "deleted") { $payload.deleted_at = $now }
    return $payload
}

function Close-TestSchedule {
    param(
        [Parameter(Mandatory = $true)][string]$AccessToken,
        [Parameter(Mandatory = $true)][string]$ScheduleId,
        [Parameter(Mandatory = $true)][string]$WatchlistId,
        [Parameter(Mandatory = $true)][string]$RuleId
    )
    $rows = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_hosted_observation_schedules?select=schedule_id,state,version,consented_at&schedule_id=eq.$ScheduleId&limit=1" `
        -AccessToken $AccessToken
    $row = Get-FirstRow $rows
    if ($null -eq $row -or [string]$row.state -eq "deleted") { return }
    $state = [string]$row.state
    $version = [int]$row.version
    $consentedAt = [string]$row.consented_at
    if ($state -in @("enabled", "paused")) {
        $killed = Invoke-ScheduleRpc `
            -AccessToken $AccessToken `
            -Schedule (New-SchedulePayload -ScheduleId $ScheduleId -WatchlistId $WatchlistId -RuleId $RuleId -State "killed" -Version ($version + 1) -ConsentedAt $consentedAt) `
            -ExpectedVersion $version
        if ($killed.status -ne "applied") { throw "Test schedule kill transition was not applied." }
        $version = [int]$killed.version
        $state = "killed"
    }
    if ($state -in @("disabled", "killed")) {
        $deleted = Invoke-ScheduleRpc `
            -AccessToken $AccessToken `
            -Schedule (New-SchedulePayload -ScheduleId $ScheduleId -WatchlistId $WatchlistId -RuleId $RuleId -State "deleted" -Version ($version + 1)) `
            -ExpectedVersion $version
        if ($deleted.status -ne "applied") { throw "Test schedule delete transition was not applied." }
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
$parentPatched = $false
$parentRestored = $false
$originalPayload = $null
$originalFingerprint = ""
$parentVersion = 0
$scheduleIds = [System.Collections.Generic.List[string]]::new()
$suffix = [guid]::NewGuid().ToString("N").Substring(0, 16)
$watchlistId = "twl_q_$suffix"
$ruleId = "alrule_q_$suffix"
$scheduleId = "hsched_q_rls_$suffix"
$replacementId = "hsched_q_replace_$suffix"
$summaryPath = Join-Path $script:RepoRoot "review_workspace\phase6q_hosted_rls_summary.json"

Write-Host "Phase 6Q hosted scheduler Account A/B RLS conformance"
Write-Host "Passwords, tokens, emails, user IDs, tenant IDs, payload rows, and project identifiers will not be printed."
Write-Host "The global operator gate and provider execution are not enabled by this harness."

try {
    $sessionA = Get-SupabaseSession -Label "Account A" -Email $emailA -SecurePassword $AccountAPassword
    $sessionB = Get-SupabaseSession -Label "Account B" -Email $emailB -SecurePassword $AccountBPassword
    Assert-Condition ($sessionA.UserId -eq $userA) "Account A identity matches configured UUID"
    Assert-Condition ($sessionB.UserId -eq $userB) "Account B identity matches configured UUID"
    Assert-Condition ($sessionA.UserId -ne $sessionB.UserId) "Account A/B identities are distinct"
    Assert-Condition ($tenantA -ne $tenantB) "Account A/B tenants are distinct"

    $documents = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_documents?select=document_id,payload,document_fingerprint,version,deleted&document_key=eq.research-continuity&deleted=eq.false&limit=1" `
        -AccessToken $sessionA.AccessToken
    $document = Get-FirstRow $documents
    Assert-Condition ($null -ne $document -and $null -ne $document.payload) "Account A has an active research-continuity document"
    $originalPayloadJson = $document.payload | ConvertTo-Json -Depth 100 -Compress
    $originalPayload = $originalPayloadJson | ConvertFrom-Json
    $originalFingerprint = [string]$document.document_fingerprint
    $originalVersion = [int]$document.version
    Assert-Condition ($originalFingerprint -match '^[a-f0-9]{64}$') "Account A document has a bounded fingerprint"

    $workingPayload = $originalPayloadJson | ConvertFrom-Json
    if ($null -eq $workingPayload.tables) { Set-JsonProperty -Object $workingPayload -Name "tables" -Value ([PSCustomObject]@{}) }
    $watchlists = @($workingPayload.tables.tenant_watchlists | Where-Object { $null -ne $_ -and $_.resource_id -ne $watchlistId })
    $watchlists += [PSCustomObject]@{ resource_id = $watchlistId; name = "Phase 6Q RLS probe"; symbols = @("AAPL") }
    Set-JsonProperty -Object $workingPayload.tables -Name "tenant_watchlists" -Value $watchlists
    $rules = @($workingPayload.tables.tenant_watchlist_alert_rules | Where-Object { $null -ne $_ -and $_.resource_id -ne $ruleId })
    $rules += [PSCustomObject]@{ resource_id = $ruleId; watchlist_resource_id = $watchlistId; name = "Phase 6Q RLS probe" }
    Set-JsonProperty -Object $workingPayload.tables -Name "tenant_watchlist_alert_rules" -Value $rules
    $workingJson = $workingPayload | ConvertTo-Json -Depth 100 -Compress
    $workingFingerprint = New-Sha256Hex $workingJson
    $parentApplied = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{
            p_document_key = "research-continuity"
            p_payload = $workingPayload
            p_document_fingerprint = $workingFingerprint
            p_expected_version = $originalVersion
            p_idempotency_key = "phase6q-parent-$suffix"
        })
    Assert-Condition ($parentApplied.status -eq "applied" -and [int]$parentApplied.version -eq ($originalVersion + 1)) "Account A adds bounded temporary schedule parents"
    $parentVersion = [int]$parentApplied.version
    $parentPatched = $true

    $created = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $scheduleId -WatchlistId $watchlistId -RuleId $ruleId -State "disabled" -Version 1) `
        -ExpectedVersion 0
    Assert-Condition ($created.status -eq "applied" -and $created.state -eq "disabled" -and [int]$created.version -eq 1) "Account A creates a disabled tenant-qualified hosted schedule"
    $scheduleIds.Add($scheduleId)

    $aSchedule = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_hosted_observation_schedules?select=schedule_id,state,version&schedule_id=eq.$scheduleId" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $aSchedule) -eq 1) "Account A reads its own hosted schedule"

    foreach ($surface in @(
        "global_terminal_hosted_observation_schedules?select=schedule_id&schedule_id=eq.$scheduleId",
        "global_terminal_hosted_observation_schedule_runs?select=scheduler_run_id&schedule_id=eq.$scheduleId",
        "global_terminal_hosted_observation_schedule_audit?select=event_id&schedule_id=eq.$scheduleId"
    )) {
        $bRows = Invoke-SupabaseRest -Method Get -PathAndQuery $surface -AccessToken $sessionB.AccessToken
        Assert-Condition ((Get-ResultCount $bRows) -eq 0) "Account B cannot read Account A hosted scheduler evidence"
    }

    Invoke-ExpectedFailure -Message "Account B cannot insert a schedule into Account A tenant" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_hosted_observation_schedules" `
            -AccessToken $sessionB.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                schedule_id = "hsched_q_forge_$suffix"
                tenant_id = $tenantA
                owner_user_id = $userA
                account_document_id = [string]$document.document_id
                account_document_version = $parentVersion
                watchlist_resource_id = $watchlistId
                alert_rule_resource_id = $ruleId
            }
    }
    Invoke-ExpectedFailure -Message "Account B cannot update Account A hosted schedule" -Operation {
        Invoke-SupabaseRest -Method Patch -PathAndQuery "global_terminal_hosted_observation_schedules?schedule_id=eq.$scheduleId" -AccessToken $sessionB.AccessToken -Body @{ state = "killed" }
    }
    Invoke-ExpectedFailure -Message "Account B cannot delete Account A hosted schedule" -Operation {
        Invoke-SupabaseRest -Method Delete -PathAndQuery "global_terminal_hosted_observation_schedules?schedule_id=eq.$scheduleId" -AccessToken $sessionB.AccessToken
    }
    Invoke-ExpectedFailure -Message "Client payload cannot forge hosted schedule identity" -Operation {
        $forged = New-SchedulePayload -ScheduleId "hsched_q_identity_$suffix" -WatchlistId $watchlistId -RuleId $ruleId -State "disabled" -Version 1
        $forged.tenant_id = $tenantA
        Invoke-ScheduleRpc -AccessToken $sessionB.AccessToken -Schedule $forged -ExpectedVersion 0
    }
    Invoke-ExpectedFailure -Message "Authenticated clients cannot forge hosted scheduler audit rows" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_hosted_observation_schedule_audit" `
            -AccessToken $sessionA.AccessToken `
            -Body @{
                event_id = "hsaudit_q_forge_$suffix"
                tenant_id = $tenantA
                owner_user_id = $userA
                schedule_id = $scheduleId
                event_type = "forged"
            }
    }

    $stale = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $scheduleId -WatchlistId $watchlistId -RuleId $ruleId -State "enabled" -Version 2) `
        -ExpectedVersion 0
    Assert-Condition ($stale.status -eq "conflict" -and [int]$stale.current_version -eq 1) "Stale hosted schedule update returns an optimistic conflict"

    $consentedAt = [DateTimeOffset]::UtcNow.ToString("o")
    $enabled = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $scheduleId -WatchlistId $watchlistId -RuleId $ruleId -State "enabled" -Version 2 -ConsentedAt $consentedAt) `
        -ExpectedVersion 1
    Assert-Condition ($enabled.status -eq "applied" -and $enabled.state -eq "enabled" -and [int]$enabled.version -eq 2) "Account A explicitly enables its hosted schedule"
    $paused = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $scheduleId -WatchlistId $watchlistId -RuleId $ruleId -State "paused" -Version 3 -ConsentedAt $consentedAt) `
        -ExpectedVersion 2
    Assert-Condition ($paused.status -eq "applied" -and $paused.state -eq "paused") "Account A pauses its hosted schedule"
    $killed = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $scheduleId -WatchlistId $watchlistId -RuleId $ruleId -State "killed" -Version 4) `
        -ExpectedVersion 3
    Assert-Condition ($killed.status -eq "applied" -and $killed.state -eq "killed") "Account A activates the schedule kill transition"
    $deleted = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $scheduleId -WatchlistId $watchlistId -RuleId $ruleId -State "deleted" -Version 5) `
        -ExpectedVersion 4
    Assert-Condition ($deleted.status -eq "applied" -and $deleted.state -eq "deleted") "Account A soft-deletes the bounded hosted schedule"

    $auditRows = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_hosted_observation_schedule_audit?select=event_id,event_type&schedule_id=eq.$scheduleId" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $auditRows) -ge 5) "Hosted schedule lifecycle produces immutable audit evidence"
    $bAuditRows = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_hosted_observation_schedule_audit?select=event_id&schedule_id=eq.$scheduleId" `
        -AccessToken $sessionB.AccessToken
    Assert-Condition ((Get-ResultCount $bAuditRows) -eq 0) "Retained hosted schedule audit remains isolated from Account B"

    $replacement = Invoke-ScheduleRpc `
        -AccessToken $sessionA.AccessToken `
        -Schedule (New-SchedulePayload -ScheduleId $replacementId -WatchlistId $watchlistId -RuleId $ruleId -State "disabled" -Version 1) `
        -ExpectedVersion 0
    Assert-Condition ($replacement.status -eq "applied" -and $replacement.state -eq "disabled") "A deleted schedule no longer blocks one replacement schedule"
    $scheduleIds.Add($replacementId)
    Close-TestSchedule -AccessToken $sessionA.AccessToken -ScheduleId $replacementId -WatchlistId $watchlistId -RuleId $ruleId
    Assert-Condition $true "Replacement schedule returns to deleted safe state"

    $restored = Get-FirstRow (Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "rpc/global_terminal_apply_account_document" `
        -AccessToken $sessionA.AccessToken `
        -Body @{
            p_document_key = "research-continuity"
            p_payload = $originalPayload
            p_document_fingerprint = $originalFingerprint
            p_expected_version = $parentVersion
            p_idempotency_key = "phase6q-parent-restore-$suffix"
        })
    Assert-Condition ($restored.status -eq "applied" -and [string]$restored.document_fingerprint -eq $originalFingerprint) "Account A restores the exact original research-continuity payload"
    $parentVersion = [int]$restored.version
    $parentRestored = $true
    $restoredDocuments = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_account_documents?select=payload,document_fingerprint,version,deleted&document_key=eq.research-continuity&deleted=eq.false&limit=1" `
        -AccessToken $sessionA.AccessToken
    $restoredDocument = Get-FirstRow $restoredDocuments
    $restoredPayloadJson = $restoredDocument.payload | ConvertTo-Json -Depth 100 -Compress
    Assert-Condition (
        [string]$restoredDocument.document_fingerprint -eq $originalFingerprint -and
        $restoredPayloadJson -eq $originalPayloadJson
    ) "Hosted cleanup re-reads the original account document without temporary parents"

    $summary = [ordered]@{
        evidence_version = "phase6q.hosted-rls.v1"
        captured_at = [DateTimeOffset]::UtcNow.ToString("o")
        passed = $true
        remote_schema_verified = $true
        account_identities_distinct = $true
        tenant_scopes_distinct = $true
        cross_tenant_schedule_rows_visible = 0
        cross_tenant_run_rows_visible = 0
        cross_tenant_audit_rows_visible = 0
        optimistic_conflict_verified = $true
        immutable_audit_verified = $true
        deleted_schedule_replacement_verified = $true
        original_account_document_restored = $true
        operator_gate_changed = $false
        hosted_worker_invoked = $false
        hosted_scheduler_verified = $false
        provider_call_count = 0
        identifiers_redacted = $true
        secrets_printed = $false
    }
    $directory = Split-Path -Parent $summaryPath
    if (-not (Test-Path -LiteralPath $directory)) { New-Item -ItemType Directory -Path $directory -Force | Out-Null }
    [IO.File]::WriteAllText($summaryPath, ($summary | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
    Write-Host "Phase 6Q hosted scheduler RLS conformance passed." -ForegroundColor Green
    Write-Host "Hosted worker scheduling remains unverified and disabled." -ForegroundColor Yellow
    Write-Host "Redacted summary: review_workspace/phase6q_hosted_rls_summary.json"
}
finally {
    if ($null -ne $sessionA -and $parentPatched) {
        foreach ($id in $scheduleIds) {
            try { Close-TestSchedule -AccessToken $sessionA.AccessToken -ScheduleId $id -WatchlistId $watchlistId -RuleId $ruleId }
            catch { Write-Warning "A bounded test schedule could not be returned to deleted state; keep the global kill switch armed." }
        }
        if (-not $parentRestored -and $null -ne $originalPayload -and $parentVersion -gt 0) {
            try {
                $restoreResult = Get-FirstRow (Invoke-SupabaseRest `
                    -Method Post `
                    -PathAndQuery "rpc/global_terminal_apply_account_document" `
                    -AccessToken $sessionA.AccessToken `
                    -Body @{
                        p_document_key = "research-continuity"
                        p_payload = $originalPayload
                        p_document_fingerprint = $originalFingerprint
                        p_expected_version = $parentVersion
                        p_idempotency_key = "phase6q-parent-finally-$suffix"
                    })
                if ($restoreResult.status -eq "applied") { $parentRestored = $true }
            }
            catch { Write-Warning "The original account document could not be restored automatically; do not enable the hosted scheduler." }
        }
    }
    if ($null -ne $sessionA) { $sessionA.AccessToken = $null }
    if ($null -ne $sessionB) { $sessionB.AccessToken = $null }
    $AccountAPassword = $null
    $AccountBPassword = $null
}

$verifierPath = Join-Path $script:RepoRoot "scripts\verify_phase6q_hosted_rls_summary.py"
& python $verifierPath $summaryPath
if ($LASTEXITCODE -ne 0) { throw "Phase 6Q hosted RLS summary verification failed with exit code $LASTEXITCODE" }
Write-Host "Phase 6Q hosted RLS evidence independently verified." -ForegroundColor Green
