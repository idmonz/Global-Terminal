param(
    [Security.SecureString]$AccountAPassword,
    [Security.SecureString]$AccountBPassword,
    [switch]$RuntimePreflightOnly
)

$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)
    $line = Get-Content -LiteralPath (Join-Path (Get-Location) ".env") |
        Where-Object { $_ -match ("^\s*" + [regex]::Escape($Name) + "\s*=") } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return (($line -split "=", 2)[1].Trim()).Trim('"').Trim("'")
}

function ConvertFrom-SecurePassword {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecurePassword)
    return [System.Net.NetworkCredential]::new("", $SecurePassword).Password
}

function Assert-Condition {
    param([Parameter(Mandatory = $true)][bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
    Write-Host "PASS: $Message" -ForegroundColor Green
}

function Get-HttpStatusCode {
    param($ErrorRecord)
    if ($ErrorRecord.Exception.Response -and $ErrorRecord.Exception.Response.StatusCode) {
        try { return [int]$ErrorRecord.Exception.Response.StatusCode } catch { return 0 }
    }
    return 0
}

function Get-SafeAuthStage {
    param($ErrorRecord)
    try {
        $stage = [string]$ErrorRecord.Exception.Response.Headers["X-Global-Terminal-QA-Auth-Stage"]
        if ($stage -match "^[a-z0-9-]{1,64}$") { return $stage }
    }
    catch { }
    return "unavailable"
}

function Get-AvailableTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try {
        $listener.Start()
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    }
    finally {
        $listener.Stop()
    }
}

function Start-Phase6PBackend {
    param(
        [Parameter(Mandatory = $true)][string]$DatabasePath,
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$LogPrefix
    )
    $priorDb = $env:GLOBAL_TERMINAL_ACCOUNT_DB_PATH
    $priorHosted = $env:GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED
    $priorContinuity = $env:GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED
    $priorLocalAuth = $env:GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED
    $priorCookieSecure = $env:GLOBAL_TERMINAL_COOKIE_SECURE
    $priorAuthDiagnostics = $env:GLOBAL_TERMINAL_QA_AUTH_DIAGNOSTICS
    $priorSupabaseUrl = $env:SUPABASE_URL
    $priorPublishableKey = $env:SUPABASE_PUBLISHABLE_KEY
    $priorAnonKey = $env:SUPABASE_ANON_KEY
    try {
        $env:GLOBAL_TERMINAL_ACCOUNT_DB_PATH = $DatabasePath
        $env:GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED = "true"
        $env:GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED = "true"
        $env:GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED = "false"
        $env:GLOBAL_TERMINAL_COOKIE_SECURE = "false"
        $env:GLOBAL_TERMINAL_QA_AUTH_DIAGNOSTICS = "phase6p-recovery"
        $env:SUPABASE_URL = $script:SupabaseUrl
        $env:SUPABASE_PUBLISHABLE_KEY = $script:PublishableKey
        $env:SUPABASE_ANON_KEY = $null
        $stdout = Join-Path $script:RunDirectory "$LogPrefix.stdout.log"
        $stderr = Join-Path $script:RunDirectory "$LogPrefix.stderr.log"
        $process = Start-Process `
            -FilePath "python" `
            -ArgumentList @("-m", "uvicorn", "backend.api.app:app", "--host", "127.0.0.1", "--port", [string]$Port) `
            -WorkingDirectory (Get-Location) `
            -RedirectStandardOutput $stdout `
            -RedirectStandardError $stderr `
            -WindowStyle Hidden `
            -PassThru
    }
    finally {
        $env:GLOBAL_TERMINAL_ACCOUNT_DB_PATH = $priorDb
        $env:GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED = $priorHosted
        $env:GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED = $priorContinuity
        $env:GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED = $priorLocalAuth
        $env:GLOBAL_TERMINAL_COOKIE_SECURE = $priorCookieSecure
        $env:GLOBAL_TERMINAL_QA_AUTH_DIAGNOSTICS = $priorAuthDiagnostics
        $env:SUPABASE_URL = $priorSupabaseUrl
        $env:SUPABASE_PUBLISHABLE_KEY = $priorPublishableKey
        $env:SUPABASE_ANON_KEY = $priorAnonKey
    }
    $health = "http://127.0.0.1:$Port/api/runtime-health"
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($process.HasExited) { throw "Phase 6P test backend exited before readiness." }
        try {
            $response = Invoke-WebRequest -Method Get -Uri $health -TimeoutSec 2
            if ([int]$response.StatusCode -eq 200) { return $process }
        }
        catch { Start-Sleep -Milliseconds 500 }
    }
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "Phase 6P test backend did not become ready."
}

function New-HostedSession {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Email,
        [Parameter(Mandatory = $true)][string]$Password,
        [Parameter(Mandatory = $true)][string]$ExpectedUserId,
        [Parameter(Mandatory = $true)][string]$ExpectedTenantId
    )
    $web = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $request = @{
        Method = "Post"
        Uri = "$BaseUrl/api/account/hosted-session"
        WebSession = $web
        Headers = @{ Origin = $BaseUrl }
        ContentType = "application/json"
        Body = (@{ email = $Email; password = $Password; return_to = "/?view=watchlist-desk" } | ConvertTo-Json -Compress)
    }
    try {
        $response = Invoke-RestMethod @request
    }
    catch {
        $productStatus = Get-HttpStatusCode $_
        if ($productStatus -ne 401) { throw }
        $productStage = Get-SafeAuthStage $_
        Write-Host "$Label product sign-in returned HTTP 401 at safe stage '$productStage'; running a bounded credential/membership probe."
        Test-DirectSupabaseIdentity `
            -Label $Label `
            -Email $Email `
            -Password $Password `
            -ExpectedUserId $ExpectedUserId `
            -ExpectedTenantId $ExpectedTenantId
        $script:HostedSignInRetryCount++
        Start-Sleep -Milliseconds 500
        try {
            $web = New-Object Microsoft.PowerShell.Commands.WebRequestSession
            $request.WebSession = $web
            $response = Invoke-RestMethod @request
        }
        catch {
            $retryStatus = Get-HttpStatusCode $_
            $retryStage = Get-SafeAuthStage $_
            throw "$Label direct Supabase identity passed, but the product session retry failed (HTTP $retryStatus, stage '$retryStage')."
        }
    }
    $csrf = $web.Cookies.GetCookies($BaseUrl)["gt_csrf"].Value
    if (-not $csrf -or -not $response.data.identity.authenticated) { throw "Hosted product session was not established." }
    return [PSCustomObject]@{ Web = $web; Csrf = $csrf; Response = $response }
}

function Test-DirectSupabaseIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Email,
        [Parameter(Mandatory = $true)][string]$Password,
        [Parameter(Mandatory = $true)][string]$ExpectedUserId,
        [Parameter(Mandatory = $true)][string]$ExpectedTenantId
    )
    $authResponse = $null
    $accessToken = $null
    try {
        try {
            $authResponse = Invoke-RestMethod `
                -Method Post `
                -Uri "$script:SupabaseUrl/auth/v1/token?grant_type=password" `
                -Headers @{ apikey = $script:PublishableKey } `
                -ContentType "application/json" `
                -Body (@{ email = $Email; password = $Password } | ConvertTo-Json -Compress)
            $script:AccountDiagnosticCallCount++
        }
        catch {
            $status = Get-HttpStatusCode $_
            throw "$Label credential probe failed (HTTP $status). Re-enter the password carefully."
        }
        $accessToken = [string]$authResponse.access_token
        $userId = [string]$authResponse.user.id
        if ([string]::IsNullOrWhiteSpace($accessToken) -or $userId -ne $ExpectedUserId) {
            throw "$Label credential probe returned an unexpected identity."
        }
        $encodedUserId = [Uri]::EscapeDataString($userId)
        try {
            $membership = Invoke-RestMethod `
                -Method Get `
                -Uri "$script:SupabaseUrl/rest/v1/global_terminal_tenant_memberships?select=tenant_id%2Crole&user_id=eq.$encodedUserId&order=created_at.asc%2Ctenant_id.asc&limit=1" `
                -Headers @{ apikey = $script:PublishableKey; Authorization = "Bearer $accessToken" }
            $script:AccountDiagnosticCallCount++
        }
        catch {
            $status = Get-HttpStatusCode $_
            throw "$Label authenticated, but its tenant membership query failed (HTTP $status)."
        }
        $membershipRow = @($membership)[0]
        if (
            $null -eq $membershipRow -or
            [string]$membershipRow.tenant_id -ne $ExpectedTenantId -or
            [string]$membershipRow.role -notin @("owner", "member", "viewer")
        ) {
            throw "$Label authenticated, but its expected tenant membership is unavailable."
        }
        Write-Host "PASS: $Label direct credential and tenant membership probe" -ForegroundColor Green
    }
    finally {
        if (-not [string]::IsNullOrWhiteSpace($accessToken)) {
            try {
                Invoke-RestMethod `
                    -Method Post `
                    -Uri "$script:SupabaseUrl/auth/v1/logout?scope=local" `
                    -Headers @{ apikey = $script:PublishableKey; Authorization = "Bearer $accessToken" } `
                    -ContentType "application/json" `
                    -Body "{}" | Out-Null
                $script:AccountDiagnosticCallCount++
            }
            catch { }
        }
        $accessToken = $null
        $authResponse = $null
    }
}

function Invoke-AccountMutation {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("Post", "Put", "Patch", "Delete")][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)]$Session,
        $Body = $null
    )
    $request = @{
        Method = $Method
        Uri = $Uri
        WebSession = $Session.Web
        Headers = @{ Origin = ([Uri]$Uri).GetLeftPart([UriPartial]::Authority); "X-CSRF-Token" = $Session.Csrf }
    }
    if ($null -ne $Body) {
        $request.ContentType = "application/json"
        $request.Body = $Body | ConvertTo-Json -Depth 20 -Compress
    }
    return Invoke-RestMethod @request
}

$emailA = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_EMAIL"
$emailB = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_EMAIL"
$userA = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_USER_ID"
$userB = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_USER_ID"
$tenantA = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_A_TENANT_ID"
$tenantB = Get-DotEnvValue "PHASE6M_TEST_ACCOUNT_B_TENANT_ID"
$script:SupabaseUrl = Get-DotEnvValue "SUPABASE_URL"
$script:PublishableKey = Get-DotEnvValue "SUPABASE_PUBLISHABLE_KEY"
if ([string]::IsNullOrWhiteSpace($script:PublishableKey)) {
    $script:PublishableKey = Get-DotEnvValue "SUPABASE_ANON_KEY"
}
if (
    [string]::IsNullOrWhiteSpace($emailA) -or
    [string]::IsNullOrWhiteSpace($emailB) -or
    [string]::IsNullOrWhiteSpace($userA) -or
    [string]::IsNullOrWhiteSpace($userB) -or
    [string]::IsNullOrWhiteSpace($tenantA) -or
    [string]::IsNullOrWhiteSpace($tenantB) -or
    [string]::IsNullOrWhiteSpace($script:SupabaseUrl) -or
    [string]::IsNullOrWhiteSpace($script:PublishableKey)
) {
    throw "Supabase URL/key and PHASE6M_TEST_ACCOUNT_A/B_EMAIL are required."
}
$script:SupabaseUrl = $script:SupabaseUrl.TrimEnd("/")

$root = (Resolve-Path (Get-Location)).Path
$runId = [guid]::NewGuid().ToString("N")
$script:RunDirectory = Join-Path $root "review_workspace\private\phase6p_product_recovery\$runId"
New-Item -ItemType Directory -Force -Path $script:RunDirectory | Out-Null
$dbOne = Join-Path $script:RunDirectory "session-one.db"
$dbTwo = Join-Path $script:RunDirectory "session-two.db"
$portOne = Get-AvailableTcpPort
do { $portTwo = Get-AvailableTcpPort } while ($portTwo -eq $portOne)
$summaryPath = Join-Path $root "review_workspace\phase6p_product_recovery_summary.json"
$processOne = $null
$processTwo = $null
$sessionAOne = $null
$sessionATwo = $null
$sessionBTwo = $null
$script:HostedSignInRetryCount = 0
$script:AccountDiagnosticCallCount = 0

if ($RuntimePreflightOnly) {
    $preflightPath = Join-Path $root "review_workspace\phase6p_product_recovery_runtime_preflight_summary.json"
    Write-Host "Phase 6P product recovery isolated-runtime preflight"
    Write-Host "No password prompt, Supabase auth request, hosted mutation, or market-provider request will be made."
    try {
        $processOne = Start-Phase6PBackend -DatabasePath $dbOne -Port $portOne -LogPrefix "runtime-preflight"
        $baseOne = "http://127.0.0.1:$portOne"
        $sessionPayload = Invoke-RestMethod -Method Get -Uri "$baseOne/api/account/session"
        $persistence = $sessionPayload.data.persistence
        $runtimeTruth = $sessionPayload.data.runtime_truth
        Assert-Condition ($persistence.configured -eq $true) "Isolated backend receives configured Supabase runtime"
        Assert-Condition ($persistence.enabled -eq $true) "Isolated backend enables hosted authentication"
        Assert-Condition ($persistence.source_status -eq "configured-unverified") "Preflight does not promote configuration to hosted verification"
        Assert-Condition ($runtimeTruth.hosted_sign_in_available -eq $true) "Hosted sign-in route is available to the recovery runtime"
        Assert-Condition ($sessionPayload.data.identity.authenticated -eq $false) "Preflight remains anonymous and credential-free"
        Assert-Condition ([int]$sessionPayload.data.summary.provider_calls -eq 0) "Preflight makes zero provider calls"

        $preflight = [ordered]@{
            evidence_version = "phase6p.product.recovery.runtime-preflight.v1"
            captured_at = [DateTime]::UtcNow.ToString("o")
            passed = $true
            runtime_env_injected = $true
            supabase_configured = $true
            hosted_auth_enabled = $true
            hosted_sign_in_available = $true
            source_status = "configured-unverified"
            anonymous_session = $true
            remote_contacted = $false
            market_provider_calls = 0
            identifiers_redacted = $true
            secrets_printed = $false
        }
        $preflight | ConvertTo-Json | Set-Content -LiteralPath $preflightPath -Encoding UTF8
        Write-Host "Phase 6P product recovery isolated-runtime preflight passed." -ForegroundColor Green
        Write-Host "Redacted summary: review_workspace/phase6p_product_recovery_runtime_preflight_summary.json"
    }
    finally {
        if ($processOne -and -not $processOne.HasExited) {
            Stop-Process -Id $processOne.Id -Force -ErrorAction SilentlyContinue
        }
        $script:PublishableKey = $null
    }
    return
}

if ($null -eq $AccountAPassword) { $AccountAPassword = Read-Host "Account A password" -AsSecureString }
if ($null -eq $AccountBPassword) { $AccountBPassword = Read-Host "Account B password" -AsSecureString }
$passwordA = ConvertFrom-SecurePassword $AccountAPassword
$passwordB = ConvertFrom-SecurePassword $AccountBPassword

Write-Host "Phase 6P product recovery conformance"
Write-Host "Passwords, tokens, emails, user IDs, tenant IDs, and workspace rows will not be printed."

try {
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 12)
    $preferenceKey = "phase6p-recovery-$suffix"

    $processOne = Start-Phase6PBackend -DatabasePath $dbOne -Port $portOne -LogPrefix "session-one"
    $baseOne = "http://127.0.0.1:$portOne"
    $sessionAOne = New-HostedSession -Label "Account A" -BaseUrl $baseOne -Email $emailA -Password $passwordA -ExpectedUserId $userA -ExpectedTenantId $tenantA
    Assert-Condition ($sessionAOne.Response.data.identity.identity_provider -eq "supabase") "First Account A session uses Supabase identity"
    Assert-Condition ($sessionAOne.Response.data.workspace.tenant_scope -eq "server-derived") "First Account A tenant scope is server-derived"

    $saved = Invoke-AccountMutation `
        -Method Put `
        -Uri "$baseOne/api/account/preferences/$preferenceKey" `
        -Session $sessionAOne `
        -Body @{ expected_version = 0; value = @{ phase = "6P"; recovery_proof = $suffix } }
    Assert-Condition ($saved.data.persistence.status -in @("applied", "deduped")) "Account A persists a hosted recovery marker"
    Assert-Condition ($saved.data.persistence.remote_contacted -eq $true) "Hosted repository is contacted for the recovery marker"

    Invoke-AccountMutation -Method Post -Uri "$baseOne/api/account/signout" -Session $sessionAOne -Body @{} | Out-Null
    Stop-Process -Id $processOne.Id -Force
    $processOne = $null

    $processTwo = Start-Phase6PBackend -DatabasePath $dbTwo -Port $portTwo -LogPrefix "session-two"
    $baseTwo = "http://127.0.0.1:$portTwo"
    $sessionATwo = New-HostedSession -Label "Account A" -BaseUrl $baseTwo -Email $emailA -Password $passwordA -ExpectedUserId $userA -ExpectedTenantId $tenantA
    Assert-Condition ($sessionATwo.Response.data.restore.status -eq "hosted-ready") "Account A restores hosted state into a new local repository"
    $restored = Invoke-RestMethod -Method Get -Uri "$baseTwo/api/account/preferences/$preferenceKey" -WebSession $sessionATwo.Web
    Assert-Condition ($restored.data.value.recovery_proof -eq $suffix) "New Account A session reads the exact hosted recovery marker"

    $sessionBTwo = New-HostedSession -Label "Account B" -BaseUrl $baseTwo -Email $emailB -Password $passwordB -ExpectedUserId $userB -ExpectedTenantId $tenantB
    $isolated = $false
    try {
        Invoke-RestMethod -Method Get -Uri "$baseTwo/api/account/preferences/$preferenceKey" -WebSession $sessionBTwo.Web | Out-Null
    }
    catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) { $isolated = $true } else { throw }
    }
    Assert-Condition $isolated "Account B cannot read Account A restored recovery marker"

    $deleted = Invoke-AccountMutation `
        -Method Delete `
        -Uri "$baseTwo/api/account/preferences/$preferenceKey`?expected_version=1" `
        -Session $sessionATwo
    Assert-Condition ($deleted.data.status -eq "deleted") "Account A removes the temporary recovery marker"
    Assert-Condition ($deleted.data.persistence.status -in @("applied", "deduped")) "Recovery marker cleanup reconciles to hosted state"

    Invoke-AccountMutation -Method Post -Uri "$baseTwo/api/account/signout" -Session $sessionATwo -Body @{} | Out-Null
    Invoke-AccountMutation -Method Post -Uri "$baseTwo/api/account/signout" -Session $sessionBTwo -Body @{} | Out-Null

    $summary = [ordered]@{
        evidence_version = "phase6p.product.recovery.v1"
        captured_at = [DateTime]::UtcNow.ToString("o")
        passed = $true
        supabase_session = $true
        server_derived_tenant = $true
        hosted_write = $true
        new_repository_restore = $true
        account_b_isolated = $true
        cleanup_reconciled = $true
        runtime_env_injected = $true
        hosted_sign_in_retry_count = $script:HostedSignInRetryCount
        account_diagnostic_call_count = $script:AccountDiagnosticCallCount
        market_provider_calls = 0
        identifiers_redacted = $true
        secrets_printed = $false
    }
    $summary | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    Write-Host "Phase 6P product recovery conformance passed." -ForegroundColor Green
    Write-Host "Redacted summary: review_workspace/phase6p_product_recovery_summary.json"
}
finally {
    if ($processOne -and -not $processOne.HasExited) { Stop-Process -Id $processOne.Id -Force -ErrorAction SilentlyContinue }
    if ($processTwo -and -not $processTwo.HasExited) { Stop-Process -Id $processTwo.Id -Force -ErrorAction SilentlyContinue }
    $passwordA = $null
    $passwordB = $null
    $AccountAPassword = $null
    $AccountBPassword = $null
    $script:PublishableKey = $null
    if ($sessionAOne) { $sessionAOne.Csrf = $null }
    if ($sessionATwo) { $sessionATwo.Csrf = $null }
    if ($sessionBTwo) { $sessionBTwo.Csrf = $null }
}
