param(
  [Parameter(Mandatory=$true)][string]$Url,
  [Parameter(Mandatory=$true)][string]$Token
)

try {
  Add-Type -AssemblyName System.Net.Http | Out-Null
  $handler = New-Object System.Net.Http.HttpClientHandler
  $client  = New-Object System.Net.Http.HttpClient($handler)
  $client.Timeout = [TimeSpan]::FromSeconds(20)
  $client.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", $Token)

  $resp = $client.GetAsync($Url).GetAwaiter().GetResult()
  $content = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()

  if (-not $resp.IsSuccessStatusCode) {
    Write-Output ("HTTP {0} {1}" -f [int]$resp.StatusCode, $Url)
    if ($content) { Write-Output $content }
    exit 1
  }

  if ($content) { Write-Output $content }
  exit 0
} catch {
  Write-Output $_.Exception.Message
  exit 1
}
