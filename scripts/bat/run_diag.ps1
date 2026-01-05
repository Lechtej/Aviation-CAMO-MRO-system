param(
  [Parameter(Mandatory=$true)][string]$ComposeFile,
  [Parameter(Mandatory=$true)][string]$LogFile,
  [int]$ApiPort = 8000,
  [int]$KeycloakPort = 8080
)

$ErrorActionPreference = "Continue"

function TeeLine([string]$line) {
  $line | Tee-Object -FilePath $LogFile -Append
}

function TeeCmd([string]$title, [scriptblock]$cmd) {
  TeeLine $title
  try {
    & $cmd 2>&1 | Tee-Object -FilePath $LogFile -Append
  } catch {
    TeeLine ("ERROR: " + $_.Exception.Message)
  }
  TeeLine ""
}

TeeCmd "docker version:" { docker version }
TeeCmd "docker compose version:" { docker compose version }
TeeCmd "docker info (excerpt):" {
  $info = docker info 2>&1
  $info | Select-Object -First 60
}
TeeCmd "docker compose ps:" { docker compose -f $ComposeFile ps }

TeeLine "Port checks:"
foreach ($p in @($ApiPort, $KeycloakPort)) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect("127.0.0.1", $p, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(1500)
    $connected = $false
    if ($ok -and $client.Connected) {
      $client.EndConnect($iar) | Out-Null
      $connected = $true
    }
    $client.Close()
    TeeLine ("PORT {0} listening: {1}" -f $p, $connected)
  } catch {
    TeeLine ("PORT {0} listening: False" -f $p)
  }
}
TeeLine ""
