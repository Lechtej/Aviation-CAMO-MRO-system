try {
  $info = docker info 2>$null
  if (-not $info) { exit 0 }
  $keep = @(
    "Server Version", "Operating System", "OSType", "Architecture",
    "CPUs", "Total Memory", "Name", "Docker Root Dir"
  )
  foreach ($line in $info) {
    foreach ($k in $keep) {
      if ($line -like "$k:*") { Write-Output $line }
    }
  }
  exit 0
} catch {
  exit 0
}
