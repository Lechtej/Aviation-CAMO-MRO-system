param(
  [Parameter(Mandatory=$true)][string]$Url,
  [int]$TimeoutSec = 60,
  [int]$IntervalSec = 2
)

$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
      Write-Output ("OK {0} {1}" -f $resp.StatusCode, $Url)
      exit 0
    }
  } catch {
  }
  Start-Sleep -Seconds $IntervalSec
}
Write-Output ("TIMEOUT {0}" -f $Url)
exit 1
