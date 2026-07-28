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

function Invoke-PersonalTenantBootstrap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AccountLabel,

        [Parameter(Mandatory = $true)]
        [string]$Email,

        [Parameter(Mandatory = $true)]
        [string]$TenantName
    )

    Write-Host ""
    Write-Host "========================================"
    Write-Host "$AccountLabel bootstrap 시작"
    Write-Host "이메일: $Email"
    Write-Host "========================================"

    $securePassword = Read-Host "$AccountLabel 비밀번호" -AsSecureString

    $password = [System.Net.NetworkCredential]::new(
        "",
        $securePassword
    ).Password

    $accessToken = $null
    $loginResponse = $null

    try {
        Write-Host "1/3 Supabase 로그인 중..."

        $loginBody = @{
            email    = $Email
            password = $password
        } | ConvertTo-Json

        $loginRequest = @{
            Method      = "Post"
            Uri         = "$script:SupabaseUrl/auth/v1/token?grant_type=password"
            Headers     = @{
                apikey = $script:SupabasePublishableKey
            }
            ContentType = "application/json"
            Body        = $loginBody
        }

        $loginResponse = Invoke-RestMethod @loginRequest

        if (-not $loginResponse.access_token) {
            throw "로그인 응답에 access_token이 없습니다."
        }

        if (-not $loginResponse.user.id) {
            throw "로그인 응답에 사용자 UUID가 없습니다."
        }

        $accessToken = $loginResponse.access_token
        $userId = $loginResponse.user.id

        Write-Host "2/3 로그인 성공"
        Write-Host "사용자 UUID: $userId"

        Write-Host "3/3 Tenant bootstrap 함수 호출 중..."

        $rpcBody = @{
            requested_name = $TenantName
        } | ConvertTo-Json

        $rpcRequest = @{
            Method      = "Post"
            Uri         = "$script:SupabaseUrl/rest/v1/rpc/global_terminal_bootstrap_personal_tenant"
            Headers     = @{
                apikey        = $script:SupabasePublishableKey
                Authorization = "Bearer $accessToken"
            }
            ContentType = "application/json"
            Body        = $rpcBody
        }

        $tenantId = Invoke-RestMethod @rpcRequest

        if ([string]::IsNullOrWhiteSpace([string]$tenantId)) {
            throw "Bootstrap 응답에 Tenant UUID가 없습니다."
        }

        Write-Host ""
        Write-Host "성공" -ForegroundColor Green
        Write-Host "계정: $AccountLabel"
        Write-Host "이메일: $Email"
        Write-Host "사용자 UUID: $userId"
        Write-Host "Tenant UUID: $tenantId"
        Write-Host "Tenant 이름: $TenantName"

        return [PSCustomObject]@{
            AccountLabel = $AccountLabel
            Email        = $Email
            UserId       = $userId
            TenantId     = [string]$tenantId
            TenantName   = $TenantName
            Success      = $true
            Error        = $null
        }
    }
    catch {
        Write-Host ""
        Write-Host "$AccountLabel 처리 실패" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red

        return [PSCustomObject]@{
            AccountLabel = $AccountLabel
            Email        = $Email
            UserId       = $null
            TenantId     = $null
            TenantName   = $TenantName
            Success      = $false
            Error        = $_.Exception.Message
        }
    }
    finally {
        $password = $null
        $securePassword = $null
        $accessToken = $null
        $loginResponse = $null
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

Write-Host "Supabase 프로젝트:"
Write-Host $script:SupabaseUrl
Write-Host ""
Write-Host "API 키, 비밀번호, access token은 출력하지 않습니다."

$accountAEmail = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_A_EMAIL"
$accountBEmail = Get-DotEnvValue -Name "PHASE6M_TEST_ACCOUNT_B_EMAIL"
if ([string]::IsNullOrWhiteSpace($accountAEmail) -or [string]::IsNullOrWhiteSpace($accountBEmail)) {
    throw ".env에 PHASE6M_TEST_ACCOUNT_A_EMAIL 및 PHASE6M_TEST_ACCOUNT_B_EMAIL이 필요합니다."
}

$resultAParameters = @{
    AccountLabel = "Account A"
    Email        = $accountAEmail
    TenantName   = "Account A Personal Research"
}

$resultA = Invoke-PersonalTenantBootstrap @resultAParameters

$resultBParameters = @{
    AccountLabel = "Account B"
    Email        = $accountBEmail
    TenantName   = "Account B Personal Research"
}

$resultB = Invoke-PersonalTenantBootstrap @resultBParameters

Write-Host ""
Write-Host "========================================"
Write-Host "최종 결과"
Write-Host "========================================"

$results = @(
    $resultA
    $resultB
)

$results |
    Select-Object `
        AccountLabel,
        Email,
        UserId,
        TenantId,
        TenantName,
        Success |
    Format-Table -AutoSize

if ($resultA.Success -and $resultB.Success) {
    if ($resultA.UserId -eq $resultB.UserId) {
        Write-Host ""
        Write-Host "오류: Account A와 B의 사용자 UUID가 같습니다." `
            -ForegroundColor Red

        exit 1
    }

    if ($resultA.TenantId -eq $resultB.TenantId) {
        Write-Host ""
        Write-Host "오류: Account A와 B가 같은 Tenant를 사용합니다." `
            -ForegroundColor Red

        exit 1
    }

    Write-Host ""
    Write-Host "Account A/B bootstrap 및 Tenant 분리 성공." `
        -ForegroundColor Green

    exit 0
}
else {
    Write-Host ""
    Write-Host "하나 이상의 계정 bootstrap이 실패했습니다." `
        -ForegroundColor Red

    exit 1
}
