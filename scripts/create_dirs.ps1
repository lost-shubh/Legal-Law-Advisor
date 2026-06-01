$root = Split-Path -Parent $PSScriptRoot
$dirs = @(
  "data\raw",
  "data\processed",
  "data\tmp",
  "logs"
)

foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $root $dir) | Out-Null
}

Write-Host "Created local data directories under $root"

