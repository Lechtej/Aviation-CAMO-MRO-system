param(
  [Parameter(Mandatory=$true)][string]$KeycloakBase,
  [Parameter(Mandatory=$true)][string]$Realm,
  [Parameter(Mandatory=$true)][string]$ClientId,
  [Parameter(Mandatory=$true)][string]$Username,
  [Parameter(Mandatory=$true)][string]$Password
)

$tokenUrl = "{0}/realms/{1}/protocol/openid-connect/token" -f $KeycloakBase.TrimEnd('/'), $Realm
$body = @{
  grant_type = "password"
  client_id  = $ClientId
  username   = $Username
  password   = $Password
}

try {
  $resp = Invoke-RestMethod -Method Post -Uri $tokenUrl -Body $body -ContentType "application/x-www-form-urlencoded" -TimeoutSec 15 -ErrorAction Stop
  $t = [string]$resp.access_token
  if ([string]::IsNullOrWhiteSpace($t)) { exit 1 }
  Write-Output $t.Trim()
  exit 0
} catch {
  exit 1
}
