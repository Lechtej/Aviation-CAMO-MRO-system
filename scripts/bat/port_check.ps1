param(
  [Parameter(Mandatory=$true)][int]$Port,
  [string]$HostName = "127.0.0.1"
)

function Test-Port([string]$host, [int]$port) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($host, $port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(1000, $false)
    if (-not $ok) { $client.Close(); return $false }
    $client.EndConnect($iar) | Out-Null
    $client.Close()
    return $true
  } catch {
    return $false
  }
}

$open = Test-Port -host $HostName -port $Port
Write-Output ("PORT {0} listening: {1}" -f $Port, $open)
exit 0
