$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $envPath = Join-Path -Path (Get-Location) -ChildPath ".env"

    if (-not (Test-Path -Path $envPath)) {
        throw ".env 파일을 찾을 수 없습니다: $envPath"
    }

    $escapedName = [regex]::Escape($Name)

    $line = Get-Content -Path $envPath |
        Where-Object {
            $_ -match "^\s*$escapedName\s*="
        } |
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
    param(
        [Parameter(Mandatory = $true)]
        [Security.SecureString]$SecurePassword
    )

    return [System.Net.NetworkCredential]::new(
        "",
        $SecurePassword
    ).Password
}

function New-Sha256Hex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $sha256 = [System.Security.Cryptography.SHA256]::Create()

    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        $hash = $sha256.ComputeHash($bytes)

        return (
            [System.BitConverter]::ToString($hash)
        ).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Get-ResultCount {
    param(
        $Value
    )

    if ($null -eq $Value) {
        return 0
    }

    return @($Value).Count
}

function Assert-Condition {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$Condition,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if (-not $Condition) {
        throw "ASSERTION FAILED: $Message"
    }

    Write-Host "PASS: $Message" -ForegroundColor Green
}

function Get-SupabaseSession {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AccountLabel,

        [Parameter(Mandatory = $true)]
        [string]$Email
    )

    Write-Host ""
    Write-Host "========================================"
    Write-Host "$AccountLabel 로그인"
    Write-Host "이메일: $Email"
    Write-Host "========================================"

    $securePassword = Read-Host "$AccountLabel 비밀번호" -AsSecureString
    $password = ConvertFrom-SecurePassword -SecurePassword $securePassword

    try {
        $loginBody = @{
            email    = $Email
            password = $password
        } | ConvertTo-Json -Compress

        $request = @{
            Method      = "Post"
            Uri         = "$script:SupabaseUrl/auth/v1/token?grant_type=password"
            Headers     = @{
                apikey = $script:SupabasePublishableKey
            }
            ContentType = "application/json"
            Body        = $loginBody
        }

        $response = Invoke-RestMethod @request

        if (-not $response.access_token) {
            throw "$AccountLabel 로그인 응답에 access_token이 없습니다."
        }

        if (-not $response.user.id) {
            throw "$AccountLabel 로그인 응답에 사용자 UUID가 없습니다."
        }

        Write-Host "$AccountLabel 로그인 성공" -ForegroundColor Green
        Write-Host "사용자 UUID: $($response.user.id)"

        return [PSCustomObject]@{
            AccountLabel = $AccountLabel
            Email        = $Email
            UserId       = [string]$response.user.id
            AccessToken  = [string]$response.access_token
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

        [Parameter(Mandatory = $true)]
        [string]$PathAndQuery,

        [Parameter(Mandatory = $true)]
        [string]$AccessToken,

        $Body = $null,

        [string]$Prefer = ""
    )

    $headers = @{
        apikey        = $script:SupabasePublishableKey
        Authorization = "Bearer $AccessToken"
    }

    if (-not [string]::IsNullOrWhiteSpace($Prefer)) {
        $headers["Prefer"] = $Prefer
    }

    $request = @{
        Method  = $Method
        Uri     = "$script:SupabaseUrl/rest/v1/$PathAndQuery"
        Headers = $headers
    }

    if ($null -ne $Body) {
        $request["ContentType"] = "application/json"
        $request["Body"] = (
            $Body |
                ConvertTo-Json -Depth 20 -Compress
        )
    }

    return Invoke-RestMethod @request
}

function Invoke-ExpectedRlsDenial {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Operation,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    try {
        & $Operation | Out-Null
        throw "RLS가 요청을 거부하지 않았습니다: $Message"
    }
    catch {
        $statusCode = $null

        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
            catch {
                $statusCode = $null
            }
        }

        if ($statusCode -in @(400, 401, 403, 404, 409)) {
            Write-Host "PASS: $Message (HTTP $statusCode)" -ForegroundColor Green
            return
        }

        if ($_.Exception.Message -like "RLS가 요청을 거부하지 않았습니다:*") {
            throw
        }

        throw "예상된 RLS 거부인지 확인할 수 없습니다: $Message`n$($_.Exception.Message)"
    }
}

$script:SupabaseUrl = Get-DotEnvValue -Name "SUPABASE_URL"

$script:SupabasePublishableKey = Get-DotEnvValue `
    -Name "SUPABASE_PUBLISHABLE_KEY"

if ([string]::IsNullOrWhiteSpace($script:SupabasePublishableKey)) {
    $script:SupabasePublishableKey = Get-DotEnvValue `
        -Name "SUPABASE_ANON_KEY"
}

if ([string]::IsNullOrWhiteSpace($script:SupabaseUrl)) {
    throw ".env에 SUPABASE_URL이 없습니다."
}

if ([string]::IsNullOrWhiteSpace($script:SupabasePublishableKey)) {
    throw ".env에 SUPABASE_PUBLISHABLE_KEY 또는 SUPABASE_ANON_KEY가 없습니다."
}

$script:SupabaseUrl = $script:SupabaseUrl.TrimEnd("/")

$accountAEmail = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_A_EMAIL"
$accountBEmail = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_B_EMAIL"
$expectedAccountAUserId = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_A_USER_ID"
$expectedAccountBUserId = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_B_USER_ID"
$accountATenantId = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_A_TENANT_ID"
$accountBTenantId = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_B_TENANT_ID"

$requiredTestValues = @(
    $accountAEmail,
    $accountBEmail,
    $expectedAccountAUserId,
    $expectedAccountBUserId,
    $accountATenantId,
    $accountBTenantId
)
if ($requiredTestValues | Where-Object { [string]::IsNullOrWhiteSpace($_) }) {
    throw ".env의 PHASE6M_TEST_ACCOUNT_* 검증 값 6개가 모두 필요합니다. 저장소에 실제 식별자를 기록하지 마십시오."
}

Write-Host "Supabase 프로젝트:"
Write-Host $script:SupabaseUrl
Write-Host ""
Write-Host "Phase 6M 실제 RLS CRUD 격리 시험을 시작합니다."
Write-Host "비밀번호, API 키, access token은 출력하지 않습니다."

$sessionA = Get-SupabaseSession `
    -AccountLabel "Account A" `
    -Email $accountAEmail

$sessionB = Get-SupabaseSession `
    -AccountLabel "Account B" `
    -Email $accountBEmail

Assert-Condition `
    -Condition ($sessionA.UserId -eq $expectedAccountAUserId) `
    -Message "Account A 사용자 UUID 일치"

Assert-Condition `
    -Condition ($sessionB.UserId -eq $expectedAccountBUserId) `
    -Message "Account B 사용자 UUID 일치"

Assert-Condition `
    -Condition ($sessionA.UserId -ne $sessionB.UserId) `
    -Message "Account A/B 사용자 UUID 분리"

$runId = [guid]::NewGuid().ToString("N").Substring(0, 12)
$now = [DateTime]::UtcNow.ToString("o")

$preferenceKey = "phase6m-rls-$runId"
$watchlistSourceKey = "phase6m-watchlist-$runId"
$watchlistFingerprint = New-Sha256Hex -Value $watchlistSourceKey
$syncIdempotencyKey = "phase6m-sync-$runId"
$syncFingerprint = New-Sha256Hex -Value $syncIdempotencyKey
$attentionFingerprint = New-Sha256Hex -Value "phase6m-attention-$runId"

$createdPreferenceId = $null
$createdWatchlistId = $null
$createdSyncReceiptId = $null
$createdAttentionStateId = $null

try {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "1. Account A 자체 데이터 생성"
    Write-Host "========================================"

    $preferenceInsert = Invoke-SupabaseRest `
        -Method "Post" `
        -PathAndQuery "global_terminal_workspace_preferences" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            tenant_id      = $accountATenantId
            owner_user_id  = $sessionA.UserId
            preference_key = $preferenceKey
            value          = @{
                phase = "created"
                run   = $runId
            }
            version         = 1
        }

    $createdPreferenceId = [string]$preferenceInsert.id

    Assert-Condition `
        -Condition (-not [string]::IsNullOrWhiteSpace($createdPreferenceId)) `
        -Message "Account A preference 생성"

    $watchlistInsert = Invoke-SupabaseRest `
        -Method "Post" `
        -PathAndQuery "global_terminal_watchlists" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            tenant_id          = $accountATenantId
            owner_user_id      = $sessionA.UserId
            name               = "Phase 6M RLS Test"
            source_key         = $watchlistSourceKey
            source_fingerprint = $watchlistFingerprint
            version            = 1
            active             = $true
        }

    $createdWatchlistId = [string]$watchlistInsert.id

    Assert-Condition `
        -Condition (-not [string]::IsNullOrWhiteSpace($createdWatchlistId)) `
        -Message "Account A watchlist 생성"

    $syncInsert = Invoke-SupabaseRest `
        -Method "Post" `
        -PathAndQuery "global_terminal_sync_receipts" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            tenant_id           = $accountATenantId
            owner_user_id       = $sessionA.UserId
            idempotency_key     = $syncIdempotencyKey
            snapshot_fingerprint = $syncFingerprint
            resource_count      = 1
            payload_bytes       = 512
            result_status       = "applied"
            remote_revision     = "r1"
            consented_at        = $now
        }

    $createdSyncReceiptId = [string]$syncInsert.id

    Assert-Condition `
        -Condition (-not [string]::IsNullOrWhiteSpace($createdSyncReceiptId)) `
        -Message "Account A sync receipt 생성"

    $attentionInsert = Invoke-SupabaseRest `
        -Method "Post" `
        -PathAndQuery "global_terminal_attention_states" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            tenant_id      = $accountATenantId
            owner_user_id  = $sessionA.UserId
            fingerprint    = $attentionFingerprint
            review_state   = "new"
            prior_state    = "new"
            version        = 1
        }

    $createdAttentionStateId = [string]$attentionInsert.id

    Assert-Condition `
        -Condition (-not [string]::IsNullOrWhiteSpace($createdAttentionStateId)) `
        -Message "Account A Attention state 생성"

    Write-Host ""
    Write-Host "========================================"
    Write-Host "2. Account A 자체 데이터 조회"
    Write-Host "========================================"

    $aPreferenceRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_workspace_preferences?select=*&id=eq.$createdPreferenceId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aPreferenceRead) -eq 1) `
        -Message "Account A가 자신의 preference 조회"

    $aWatchlistRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_watchlists?select=*&id=eq.$createdWatchlistId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aWatchlistRead) -eq 1) `
        -Message "Account A가 자신의 watchlist 조회"

    $aSyncRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_sync_receipts?select=*&id=eq.$createdSyncReceiptId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aSyncRead) -eq 1) `
        -Message "Account A가 자신의 sync receipt 조회"

    $aAttentionRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_attention_states?select=*&id=eq.$createdAttentionStateId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aAttentionRead) -eq 1) `
        -Message "Account A가 자신의 Attention state 조회"

    Write-Host ""
    Write-Host "========================================"
    Write-Host "3. Account A 자체 데이터 수정"
    Write-Host "========================================"

    $updatedAt = [DateTime]::UtcNow.ToString("o")

    $aPreferenceUpdate = Invoke-SupabaseRest `
        -Method "Patch" `
        -PathAndQuery "global_terminal_workspace_preferences?id=eq.$createdPreferenceId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            value = @{
                phase = "updated"
                run   = $runId
            }
            version    = 2
            updated_at = $updatedAt
        }

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aPreferenceUpdate) -eq 1) `
        -Message "Account A가 자신의 preference 수정"

    $aWatchlistUpdate = Invoke-SupabaseRest `
        -Method "Patch" `
        -PathAndQuery "global_terminal_watchlists?id=eq.$createdWatchlistId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            name       = "Phase 6M RLS Test Updated"
            version    = 2
            updated_at = $updatedAt
        }

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aWatchlistUpdate) -eq 1) `
        -Message "Account A가 자신의 watchlist 수정"

    $aSyncUpdate = Invoke-SupabaseRest `
        -Method "Patch" `
        -PathAndQuery "global_terminal_sync_receipts?id=eq.$createdSyncReceiptId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            result_status   = "deduped"
            remote_revision = "r2"
            updated_at      = $updatedAt
        }

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aSyncUpdate) -eq 1) `
        -Message "Account A가 자신의 sync receipt 수정"

    $aAttentionUpdate = Invoke-SupabaseRest `
        -Method "Patch" `
        -PathAndQuery "global_terminal_attention_states?id=eq.$createdAttentionStateId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            review_state = "reviewed"
            prior_state  = "new"
            reviewed_at  = $updatedAt
            version      = 2
            updated_at   = $updatedAt
        }

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aAttentionUpdate) -eq 1) `
        -Message "Account A가 자신의 Attention state 수정"

    Write-Host ""
    Write-Host "========================================"
    Write-Host "4. Account B의 Account A 데이터 조회 차단"
    Write-Host "========================================"

    $bTenantRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_tenants?select=id&id=eq.$accountATenantId" `
        -AccessToken $sessionB.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bTenantRead) -eq 0) `
        -Message "Account B가 Account A tenant를 조회하지 못함"

    $bPreferenceRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_workspace_preferences?select=id&id=eq.$createdPreferenceId" `
        -AccessToken $sessionB.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bPreferenceRead) -eq 0) `
        -Message "Account B가 Account A preference를 조회하지 못함"

    $bWatchlistRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_watchlists?select=id&id=eq.$createdWatchlistId" `
        -AccessToken $sessionB.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bWatchlistRead) -eq 0) `
        -Message "Account B가 Account A watchlist를 조회하지 못함"

    $bSyncRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_sync_receipts?select=id&id=eq.$createdSyncReceiptId" `
        -AccessToken $sessionB.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bSyncRead) -eq 0) `
        -Message "Account B가 Account A sync receipt를 조회하지 못함"

    $bAttentionRead = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_attention_states?select=id&id=eq.$createdAttentionStateId" `
        -AccessToken $sessionB.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bAttentionRead) -eq 0) `
        -Message "Account B가 Account A Attention state를 조회하지 못함"

    Write-Host ""
    Write-Host "========================================"
    Write-Host "5. Account B의 Account A 데이터 수정·삭제 차단"
    Write-Host "========================================"

    $bPreferenceUpdate = Invoke-SupabaseRest `
        -Method "Patch" `
        -PathAndQuery "global_terminal_workspace_preferences?id=eq.$createdPreferenceId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            value = @{
                phase = "forbidden-update"
            }
            version    = 999
            updated_at = [DateTime]::UtcNow.ToString("o")
        }

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bPreferenceUpdate) -eq 0) `
        -Message "Account B가 Account A preference를 수정하지 못함"

    $bWatchlistDelete = Invoke-SupabaseRest `
        -Method "Delete" `
        -PathAndQuery "global_terminal_watchlists?id=eq.$createdWatchlistId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation"

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bWatchlistDelete) -eq 0) `
        -Message "Account B가 Account A watchlist를 삭제하지 못함"

    $bSyncDelete = Invoke-SupabaseRest `
        -Method "Delete" `
        -PathAndQuery "global_terminal_sync_receipts?id=eq.$createdSyncReceiptId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation"

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bSyncDelete) -eq 0) `
        -Message "Account B가 Account A sync receipt를 삭제하지 못함"

    $bAttentionUpdate = Invoke-SupabaseRest `
        -Method "Patch" `
        -PathAndQuery "global_terminal_attention_states?id=eq.$createdAttentionStateId" `
        -AccessToken $sessionB.AccessToken `
        -Prefer "return=representation" `
        -Body @{
            review_state = "acknowledged"
            version      = 999
            updated_at   = [DateTime]::UtcNow.ToString("o")
        }

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $bAttentionUpdate) -eq 0) `
        -Message "Account B가 Account A Attention state를 수정하지 못함"

    Invoke-ExpectedRlsDenial `
        -Message "Account B가 Account A tenant에 preference를 삽입하지 못함" `
        -Operation {
            Invoke-SupabaseRest `
                -Method "Post" `
                -PathAndQuery "global_terminal_workspace_preferences" `
                -AccessToken $sessionB.AccessToken `
                -Prefer "return=representation" `
                -Body @{
                    tenant_id      = $accountATenantId
                    owner_user_id  = $sessionB.UserId
                    preference_key = "phase6m-forbidden-$runId"
                    value          = @{
                        phase = "forbidden-insert"
                    }
                    version         = 1
                }
        }

    Write-Host ""
    Write-Host "========================================"
    Write-Host "6. Account A 데이터 무결성 재확인"
    Write-Host "========================================"

    $aPreferenceAfterB = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_workspace_preferences?select=*&id=eq.$createdPreferenceId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition (
            (Get-ResultCount -Value $aPreferenceAfterB) -eq 1 -and
            [int]$aPreferenceAfterB.version -eq 2
        ) `
        -Message "B의 공격 시도 후 A preference가 유지됨"

    $aWatchlistAfterB = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_watchlists?select=id&id=eq.$createdWatchlistId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aWatchlistAfterB) -eq 1) `
        -Message "B의 삭제 시도 후 A watchlist가 유지됨"

    $aSyncAfterB = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_sync_receipts?select=id&id=eq.$createdSyncReceiptId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aSyncAfterB) -eq 1) `
        -Message "B의 삭제 시도 후 A sync receipt가 유지됨"

    $aAttentionAfterB = Invoke-SupabaseRest `
        -Method "Get" `
        -PathAndQuery "global_terminal_attention_states?select=*&id=eq.$createdAttentionStateId" `
        -AccessToken $sessionA.AccessToken

    Assert-Condition `
        -Condition (
            (Get-ResultCount -Value $aAttentionAfterB) -eq 1 -and
            [string]$aAttentionAfterB.review_state -eq "reviewed"
        ) `
        -Message "B의 수정 시도 후 A Attention state가 유지됨"

    Write-Host ""
    Write-Host "========================================"
    Write-Host "7. Account A 테스트 데이터 정리"
    Write-Host "========================================"

    $aAttentionDelete = Invoke-SupabaseRest `
        -Method "Delete" `
        -PathAndQuery "global_terminal_attention_states?id=eq.$createdAttentionStateId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aAttentionDelete) -eq 1) `
        -Message "Account A Attention state 삭제"

    $createdAttentionStateId = $null

    $aSyncDelete = Invoke-SupabaseRest `
        -Method "Delete" `
        -PathAndQuery "global_terminal_sync_receipts?id=eq.$createdSyncReceiptId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aSyncDelete) -eq 1) `
        -Message "Account A sync receipt 삭제"

    $createdSyncReceiptId = $null

    $aWatchlistDelete = Invoke-SupabaseRest `
        -Method "Delete" `
        -PathAndQuery "global_terminal_watchlists?id=eq.$createdWatchlistId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aWatchlistDelete) -eq 1) `
        -Message "Account A watchlist 삭제"

    $createdWatchlistId = $null

    $aPreferenceDelete = Invoke-SupabaseRest `
        -Method "Delete" `
        -PathAndQuery "global_terminal_workspace_preferences?id=eq.$createdPreferenceId" `
        -AccessToken $sessionA.AccessToken `
        -Prefer "return=representation"

    Assert-Condition `
        -Condition ((Get-ResultCount -Value $aPreferenceDelete) -eq 1) `
        -Message "Account A preference 삭제"

    $createdPreferenceId = $null

    Write-Host ""
    Write-Host "========================================"
    Write-Host "최종 판정"
    Write-Host "========================================"
    Write-Host "PASS: Account A 자체 CRUD 성공" -ForegroundColor Green
    Write-Host "PASS: Account B의 Account A 조회 차단" -ForegroundColor Green
    Write-Host "PASS: Account B의 Account A 수정·삭제 차단" -ForegroundColor Green
    Write-Host "PASS: Account B의 Account A tenant 삽입 차단" -ForegroundColor Green
    Write-Host "PASS: 테스트 데이터 정리 완료" -ForegroundColor Green
    Write-Host ""
    Write-Host "Phase 6M 기본 A/B RLS CRUD 격리 시험 성공." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "시험 실패"
    Write-Host "========================================"
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "생성된 테스트 행이 남아 있을 수 있습니다."
    Write-Host "아래 ID를 기록하고 임의의 관리자 SQL로 삭제하지 마십시오."
    Write-Host "Preference ID: $createdPreferenceId"
    Write-Host "Watchlist ID: $createdWatchlistId"
    Write-Host "Sync Receipt ID: $createdSyncReceiptId"
    Write-Host "Attention State ID: $createdAttentionStateId"

    exit 1
}
finally {
    if ($sessionA) {
        $sessionA.AccessToken = $null
    }

    if ($sessionB) {
        $sessionB.AccessToken = $null
    }
}
