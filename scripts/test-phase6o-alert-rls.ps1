param(
    [Security.SecureString]$AccountAPassword,
    [Security.SecureString]$AccountBPassword
)

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
        [Parameter(Mandatory = $true)][string]$Email,
        [Security.SecureString]$SecurePassword
    )

    if ($null -eq $SecurePassword) {
        $SecurePassword = Read-Host "$AccountLabel password" -AsSecureString
    }
    $password = ConvertFrom-SecurePassword $SecurePassword
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
        $SecurePassword = $null
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

function Remove-TestRows {
    param(
        [Parameter(Mandatory = $true)]$Session,
        [string]$TriggerId,
        [string]$WorkerId,
        [string]$RuleId,
        [string]$EvaluationId,
        [string]$ObservationRunId,
        [string]$WatchlistId
    )

    $targets = @(
        @{ Table = "global_terminal_watchlist_alert_triggers"; Key = "trigger_id"; Value = $TriggerId },
        @{ Table = "global_terminal_watchlist_alert_worker_state"; Key = "resource_id"; Value = $WorkerId },
        @{ Table = "global_terminal_watchlist_alert_rules"; Key = "resource_id"; Value = $RuleId },
        @{ Table = "global_terminal_watchlist_alert_evaluations"; Key = "run_id"; Value = $EvaluationId },
        @{ Table = "global_terminal_observation_runs"; Key = "run_id"; Value = $ObservationRunId },
        @{ Table = "global_terminal_watchlists"; Key = "id"; Value = $WatchlistId }
    )
    foreach ($target in $targets) {
        if ([string]::IsNullOrWhiteSpace($target.Value)) {
            continue
        }
        try {
            Invoke-SupabaseRest `
                -Method Delete `
                -PathAndQuery "$($target.Table)?$($target.Key)=eq.$($target.Value)" `
                -AccessToken $Session.AccessToken | Out-Null
        }
        catch {
            Write-Warning "Best-effort cleanup did not remove one bounded Phase 6O test row."
        }
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
$suffix = [guid]::NewGuid().ToString("N").Substring(0, 16)
$watchlistAId = [guid]::NewGuid().ToString()
$watchlistBId = [guid]::NewGuid().ToString()
$observationRunId = "obsr6o_$suffix"
$snapshotId = "obss6o_$suffix"
$ruleId = "alrule_$suffix"
$evaluationAId = "aleval_$suffix"
$evaluationBId = "albeval_$suffix"
$triggerId = "altrig_$suffix"
$workerId = "alwork_$suffix"
$summaryPath = Join-Path (Get-Location) "review_workspace\phase6o_hosted_rls_summary.json"

Write-Host "Phase 6O hosted Alert Manager RLS conformance"
Write-Host "Secrets, tokens, emails, user IDs, tenant IDs, and generated row IDs will not be printed."

try {
    $sessionA = Get-SupabaseSession -AccountLabel "Account A" -Email $accountAEmail -SecurePassword $AccountAPassword
    $sessionB = Get-SupabaseSession -AccountLabel "Account B" -Email $accountBEmail -SecurePassword $AccountBPassword

    Assert-Condition ($sessionA.UserId -eq $accountAUserId) "Account A identity matches configured UUID"
    Assert-Condition ($sessionB.UserId -eq $accountBUserId) "Account B identity matches configured UUID"
    Assert-Condition ($sessionA.UserId -ne $sessionB.UserId) "Account A/B identities are distinct"
    Assert-Condition ($accountATenantId -ne $accountBTenantId) "Account A/B tenants are distinct"

    $now = [DateTime]::UtcNow
    $nowText = $now.ToString("o")
    $expiresText = $now.AddDays(7).ToString("o")

    $watchlistA = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlists" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            id = $watchlistAId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            name = "Phase 6O hosted conformance"
            source_key = "phase6o-hosted-$suffix"
            source_fingerprint = (New-Sha256Hex "phase6o-watchlist-$suffix")
        }
    Assert-Condition ((Get-ResultCount $watchlistA) -eq 1) "Account A creates a bounded Watchlist parent"

    $observationRun = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_observation_runs" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            run_id = $observationRunId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            watchlist_resource_id = $watchlistAId
            idempotency_key = "phase6o-observation-$suffix"
            request_fingerprint = (New-Sha256Hex "phase6o-observation-$suffix")
            status = "completed"
            request_json = @{ mode = "hosted-conformance" }
            plan_json = @{ maximum_symbols = 1; maximum_calls = 0 }
            result_json = @{ provider_calls = 0 }
            completed_at = $nowText
        }
    Assert-Condition ((Get-ResultCount $observationRun) -eq 1) "Account A creates a stored observation run"

    $snapshot = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_observation_snapshots" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            snapshot_id = $snapshotId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            run_id = $observationRunId
            watchlist_resource_id = $watchlistAId
            symbol = "AAPL"
            asset_class = "equity"
            snapshot_status = "fresh"
            source_status = "fixture"
            observed_at = $nowText
            retrieved_at = $nowText
            provider = "phase6o-hosted-conformance"
            source_url = ""
            confidence = 1.0
            content_hash = (New-Sha256Hex "phase6o-snapshot-$suffix")
            payload_json = @{ quote = @{ last_price = 212.5 } }
            caveat = "Synthetic hosted RLS conformance row."
            data_gap = "No market-provider call was made."
        }
    Assert-Condition ((Get-ResultCount $snapshot) -eq 1) "Account A creates a tenant-qualified stored snapshot"

    $rule = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlist_alert_rules" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            resource_id = $ruleId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            watchlist_id = $watchlistAId
            symbol = "AAPL"
            asset_class = "equity"
            rule_type = "price_above"
            metric = "last_price"
            operator = "above"
            threshold = 200.0
            threshold_unit = "USD"
            frequency = "15m"
            frequency_minutes = 15
            session_policy = "market-aware"
            cooldown_minutes = 60
            severity = "high"
            state = "active"
            fingerprint = (New-Sha256Hex "phase6o-rule-$suffix")
            next_due_at = $nowText
            expires_at = $expiresText
        }
    Assert-Condition ((Get-ResultCount $rule) -eq 1) "Account A creates an active alert rule"

    $evaluationA = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlist_alert_evaluations" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            run_id = $evaluationAId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            idempotency_key = "phase6o-evaluation-$suffix"
            request_fingerprint = (New-Sha256Hex "phase6o-evaluation-$suffix")
            mode = "manual"
            status = "completed"
            due_count = 1
            evaluated_count = 1
            triggered_count = 1
            provider_call_count = 0
            source_clock = @{ observed_at = $nowText; retrieved_at = $nowText; evaluated_at = $nowText }
            detail = @{ market_provider_calls = 0; conformance = $true }
            completed_at = $nowText
        }
    Assert-Condition ((Get-ResultCount $evaluationA) -eq 1) "Account A records a zero-provider-call evaluation"

    $trigger = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlist_alert_triggers" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            trigger_id = $triggerId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            rule_id = $ruleId
            watchlist_id = $watchlistAId
            evaluation_run_id = $evaluationAId
            snapshot_id = $snapshotId
            symbol = "AAPL"
            dedupe_key = (New-Sha256Hex "phase6o-trigger-$suffix")
            status = "triggered"
            severity = "high"
            review_state = "new"
            metric = "last_price"
            operator = "above"
            threshold = 200.0
            observed_value = 212.5
            source_status = "fixture"
            provider = "phase6o-hosted-conformance"
            source_url = ""
            observed_at = $nowText
            retrieved_at = $nowText
            evaluated_at = $nowText
            triggered_at = $nowText
            message = "AAPL price condition matched a synthetic stored observation."
            caveat = "Synthetic hosted RLS conformance row."
            data_gap = "No market-provider call was made."
            evidence = @{ snapshot_id = $snapshotId; provider_calls = 0 }
        }
    Assert-Condition ((Get-ResultCount $trigger) -eq 1) "Account A persists an explainable in-app trigger"

    $worker = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlist_alert_worker_state" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            resource_id = $workerId
            tenant_id = $accountATenantId
            owner_user_id = $sessionA.UserId
            state = "stopped"
            enabled = $false
            last_heartbeat_at = $nowText
            last_evaluation_run_id = $evaluationAId
        }
    Assert-Condition ((Get-ResultCount $worker) -eq 1) "Account A persists disabled local-worker state"

    $auditCreated = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_watchlist_alert_audit?select=event_type,resource_type,resource_id&resource_id=in.($ruleId,$evaluationAId,$triggerId,$workerId)" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $auditCreated) -ge 4) "Rule, evaluation, trigger, and worker creation produce immutable audit evidence"

    $protectedRows = @(
        @{ Table = "global_terminal_watchlist_alert_rules"; Filter = "resource_id=eq.$ruleId" },
        @{ Table = "global_terminal_watchlist_alert_evaluations"; Filter = "run_id=eq.$evaluationAId" },
        @{ Table = "global_terminal_watchlist_alert_triggers"; Filter = "trigger_id=eq.$triggerId" },
        @{ Table = "global_terminal_watchlist_alert_worker_state"; Filter = "resource_id=eq.$workerId" },
        @{ Table = "global_terminal_watchlist_alert_audit"; Filter = "resource_id=eq.$ruleId" }
    )
    foreach ($protected in $protectedRows) {
        $bRead = Invoke-SupabaseRest `
            -Method Get `
            -PathAndQuery "$($protected.Table)?select=*&$($protected.Filter)" `
            -AccessToken $sessionB.AccessToken
        Assert-Condition ((Get-ResultCount $bRead) -eq 0) "Account B cannot read Account A row from $($protected.Table)"
    }

    $bUpdate = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_rules?resource_id=eq.$ruleId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation" `
        -Body @{ state = "cancelled"; version = 99 }
    Assert-Condition ((Get-ResultCount $bUpdate) -eq 0) "Account B cannot update Account A alert rule"

    $bDelete = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlist_alert_triggers?trigger_id=eq.$triggerId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $bDelete) -eq 0) "Account B cannot delete Account A alert trigger"

    Invoke-ExpectedFailure -Message "Account B cannot insert an alert rule into Account A tenant" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_watchlist_alert_rules" `
            -AccessToken $sessionB.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                resource_id = "alcross_$suffix"
                tenant_id = $accountATenantId
                owner_user_id = $sessionB.UserId
                watchlist_id = $watchlistAId
                symbol = "MSFT"
                rule_type = "price_above"
                metric = "last_price"
                operator = "above"
                threshold = 300.0
                frequency = "15m"
                frequency_minutes = 15
                session_policy = "market-aware"
                fingerprint = (New-Sha256Hex "phase6o-cross-tenant-$suffix")
            }
    }

    $watchlistB = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlists" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            id = $watchlistBId
            tenant_id = $accountBTenantId
            owner_user_id = $sessionB.UserId
            name = "Phase 6O hosted cross-parent control"
            source_key = "phase6o-hosted-b-$suffix"
            source_fingerprint = (New-Sha256Hex "phase6o-watchlist-b-$suffix")
        }
    Assert-Condition ((Get-ResultCount $watchlistB) -eq 1) "Account B creates its own bounded Watchlist parent"

    $evaluationB = Invoke-SupabaseRest `
        -Method Post `
        -PathAndQuery "global_terminal_watchlist_alert_evaluations" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            run_id = $evaluationBId
            tenant_id = $accountBTenantId
            owner_user_id = $sessionB.UserId
            idempotency_key = "phase6o-evaluation-b-$suffix"
            request_fingerprint = (New-Sha256Hex "phase6o-evaluation-b-$suffix")
            mode = "manual"
            status = "no-due"
            provider_call_count = 0
        }
    Assert-Condition ((Get-ResultCount $evaluationB) -eq 1) "Account B creates its own zero-call evaluation parent"

    Invoke-ExpectedFailure -Message "Composite foreign keys block Account B from linking Account A rule and snapshot" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_watchlist_alert_triggers" `
            -AccessToken $sessionB.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                trigger_id = "alcrossp_$suffix"
                tenant_id = $accountBTenantId
                owner_user_id = $sessionB.UserId
                rule_id = $ruleId
                watchlist_id = $watchlistBId
                evaluation_run_id = $evaluationBId
                snapshot_id = $snapshotId
                symbol = "AAPL"
                dedupe_key = (New-Sha256Hex "phase6o-cross-parent-$suffix")
                metric = "last_price"
                operator = "above"
                threshold = 200.0
                observed_value = 212.5
                source_status = "fixture"
                evaluated_at = $nowText
                triggered_at = $nowText
                message = "Cross-parent linkage must fail."
            }
    }

    Invoke-ExpectedFailure -Message "Authenticated clients cannot forge Alert Manager audit rows" -Operation {
        Invoke-SupabaseRest `
            -Method Post `
            -PathAndQuery "global_terminal_watchlist_alert_audit" `
            -AccessToken $sessionA.AccessToken `
            -Prefer "return=representation" `
            -Body @{
                event_id = "alforge_$suffix"
                tenant_id = $accountATenantId
                owner_user_id = $sessionA.UserId
                resource_type = "rule"
                resource_id = $ruleId
                event_type = "forged"
            }
    }

    $paused = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_rules?resource_id=eq.$ruleId&version=eq.1" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ state = "paused"; version = 2; updated_at = $nowText }
    Assert-Condition ((Get-ResultCount $paused) -eq 1) "Account A pauses its rule with the expected version"

    $stale = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_rules?resource_id=eq.$ruleId&version=eq.1" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ state = "cancelled"; version = 3; updated_at = $nowText }
    Assert-Condition ((Get-ResultCount $stale) -eq 0) "Stale optimistic rule update changes zero rows"

    $resumed = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_rules?resource_id=eq.$ruleId&version=eq.2" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ state = "active"; version = 3; updated_at = $nowText }
    Assert-Condition ((Get-ResultCount $resumed) -eq 1) "Account A resumes its rule with the current version"

    $acknowledged = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_triggers?trigger_id=eq.$triggerId&version=eq.1" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ review_state = "acknowledged"; reviewed_at = $nowText; acknowledged_at = $nowText; version = 2; updated_at = $nowText }
    Assert-Condition ((Get-ResultCount $acknowledged) -eq 1) "Account A acknowledges its in-app trigger"

    $restartedWorker = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_worker_state?resource_id=eq.$workerId&version=eq.1" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            state = "restarted"
            enabled = $false
            restart_count = 1
            last_started_at = $nowText
            last_heartbeat_at = $nowText
            version = 2
            updated_at = $nowText
        }
    Assert-Condition ((Get-ResultCount $restartedWorker) -eq 1) "Account A records a disabled worker restart state"

    $stoppedWorker = Invoke-SupabaseRest `
        -Method Patch `
        -PathAndQuery "global_terminal_watchlist_alert_worker_state?resource_id=eq.$workerId&version=eq.2" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{ state = "stopped"; enabled = $false; last_stopped_at = $nowText; version = 3; updated_at = $nowText }
    Assert-Condition ((Get-ResultCount $stoppedWorker) -eq 1) "Account A returns the local worker to a safe stopped state"

    $auditBeforeDelete = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_watchlist_alert_audit?select=event_type,resource_type,resource_id&resource_id=in.($ruleId,$evaluationAId,$triggerId,$workerId)" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $auditBeforeDelete) -ge 9) "Rule, trigger, and worker recovery transitions are audited"

    $deletedTrigger = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlist_alert_triggers?trigger_id=eq.$triggerId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $deletedTrigger) -eq 1) "Account A deletes the bounded trigger row"

    $deletedWorker = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlist_alert_worker_state?resource_id=eq.$workerId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $deletedWorker) -eq 1) "Account A deletes the bounded worker row"

    $deletedRule = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlist_alert_rules?resource_id=eq.$ruleId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $deletedRule) -eq 1) "Account A deletes the bounded alert rule"

    $deletedEvaluation = Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlist_alert_evaluations?run_id=eq.$evaluationAId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"
    Assert-Condition ((Get-ResultCount $deletedEvaluation) -eq 1) "Account A deletes the bounded evaluation row"

    $boundedChecks = @(
        @{ Table = "global_terminal_watchlist_alert_rules"; Filter = "resource_id=eq.$ruleId" },
        @{ Table = "global_terminal_watchlist_alert_evaluations"; Filter = "run_id=eq.$evaluationAId" },
        @{ Table = "global_terminal_watchlist_alert_triggers"; Filter = "trigger_id=eq.$triggerId" },
        @{ Table = "global_terminal_watchlist_alert_worker_state"; Filter = "resource_id=eq.$workerId" }
    )
    foreach ($bounded in $boundedChecks) {
        $afterDelete = Invoke-SupabaseRest `
            -Method Get `
            -PathAndQuery "$($bounded.Table)?select=*&$($bounded.Filter)" `
            -AccessToken $sessionA.AccessToken
        Assert-Condition ((Get-ResultCount $afterDelete) -eq 0) "Cleanup removes bounded data from $($bounded.Table)"
    }

    $retainedAudit = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_watchlist_alert_audit?select=event_type,resource_type,resource_id&resource_id=in.($ruleId,$evaluationAId,$triggerId,$workerId)" `
        -AccessToken $sessionA.AccessToken
    Assert-Condition ((Get-ResultCount $retainedAudit) -ge 13) "Alert Manager audit evidence survives parent deletion"

    $bRetainedAudit = Invoke-SupabaseRest `
        -Method Get `
        -PathAndQuery "global_terminal_watchlist_alert_audit?select=event_type&resource_id=in.($ruleId,$evaluationAId,$triggerId,$workerId)" `
        -AccessToken $sessionB.AccessToken
    Assert-Condition ((Get-ResultCount $bRetainedAudit) -eq 0) "Retained Alert Manager audit evidence remains isolated from Account B"

    Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_observation_runs?run_id=eq.$observationRunId" `
        -AccessToken $sessionA.AccessToken | Out-Null
    Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlists?id=eq.$watchlistAId" `
        -AccessToken $sessionA.AccessToken | Out-Null
    Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlist_alert_evaluations?run_id=eq.$evaluationBId" `
        -AccessToken $sessionB.AccessToken | Out-Null
    Invoke-SupabaseRest `
        -Method Delete `
        -PathAndQuery "global_terminal_watchlists?id=eq.$watchlistBId" `
        -AccessToken $sessionB.AccessToken | Out-Null

    $observationRunId = $null
    $watchlistAId = $null
    $evaluationBId = $null
    $watchlistBId = $null
    $ruleId = $null
    $evaluationAId = $null
    $triggerId = $null
    $workerId = $null

    $summary = [ordered]@{
        evidence_version = "phase6o.hosted.rls.v1"
        captured_at = [DateTime]::UtcNow.ToString("o")
        passed = $true
        hosted_persistence_verified = $true
        hosted_scheduler_verified = $false
        account_isolation = $true
        cross_tenant_insert_blocked = $true
        composite_parent_integrity = $true
        optimistic_conflict = $true
        worker_recovery_state = $true
        audit_immutable = $true
        audit_retained_after_delete = $true
        provider_calls = 0
        identifiers_redacted = $true
        secrets_printed = $false
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $summaryPath) | Out-Null
    $summary | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    Write-Host "Phase 6O hosted Alert Manager RLS conformance passed." -ForegroundColor Green
    Write-Host "Hosted scheduling remains unverified until a deployed scheduler is exercised."
    Write-Host "Redacted summary: review_workspace/phase6o_hosted_rls_summary.json"
}
finally {
    if ($sessionA -and $sessionA.AccessToken) {
        Remove-TestRows `
            -Session $sessionA `
            -TriggerId $triggerId `
            -WorkerId $workerId `
            -RuleId $ruleId `
            -EvaluationId $evaluationAId `
            -ObservationRunId $observationRunId `
            -WatchlistId $watchlistAId
    }
    if ($sessionB -and $sessionB.AccessToken) {
        Remove-TestRows `
            -Session $sessionB `
            -EvaluationId $evaluationBId `
            -WatchlistId $watchlistBId
    }
    if ($sessionA) { $sessionA.AccessToken = $null }
    if ($sessionB) { $sessionB.AccessToken = $null }
    $script:SupabasePublishableKey = $null
}
