param(
  [Parameter(Mandatory=$true)][string]$ApiBase
)

$ErrorActionPreference = "Stop"

$token = ($env:BEARER_TOKEN)
if ([string]::IsNullOrWhiteSpace($token)) {
  Write-Host "ERROR: Empty token (BEARER_TOKEN env var not set)"
  exit 3
}

$token = $token.Trim()

$headers = @{
  "Authorization" = ("Bearer " + $token)
  "X-Tenant-Id"   = "00000000-0000-0000-0000-000000000000"
}

try {
  $uri = ($ApiBase.TrimEnd('/') + "/v1/admin/bootstrap")
  $resp = Invoke-RestMethod -Method Post -Headers $headers -TimeoutSec 60 -Uri $uri -ErrorAction Stop
  $resp | ConvertTo-Json -Depth 10
  exit 0
} catch {
  Write-Host ("ERROR calling /v1/admin/bootstrap: " + $_.Exception.Message)
  exit 1
}
