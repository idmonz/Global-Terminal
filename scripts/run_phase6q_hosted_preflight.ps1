param(
    [switch]$ProbeLinked,
    [switch]$ProbeGitHub,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$arguments = @("scripts/preflight_phase6q_hosted_deployment.py")
if ($ProbeLinked) { $arguments += "--probe-linked" }
if ($ProbeGitHub) { $arguments += "--probe-github" }
if ($Strict) { $arguments += "--strict" }

Push-Location $repoRoot
try {
    Write-Host "Phase 6Q hosted deployment preflight"
    Write-Host "This step is read-only and prints no key, account identifier, project reference, or provider payload."
    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 6Q deployment prerequisites are incomplete. Review only the redacted blocker codes above."
    }
    Write-Host "Redacted summary: review_workspace/phase6q_hosted_deployment_preflight_summary.json"
}
finally {
    Pop-Location
}
