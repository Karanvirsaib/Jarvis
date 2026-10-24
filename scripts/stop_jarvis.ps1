$ErrorActionPreference = 'Stop'
$rootDir = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
$logs = Join-Path $rootDir 'logs'
foreach ($name in @('jarvis-web','hermes-gateway','ollama-local')) {
  $pidFile = Join-Path $logs "$name.pid"
  if (-not (Test-Path $pidFile)) { continue }
  $id = 0
  if (-not [int]::TryParse((Get-Content $pidFile -Raw).Trim(), [ref]$id)) { Remove-Item $pidFile -Force; continue }
  $process = Get-CimInstance Win32_Process -Filter "ProcessId = $id" -ErrorAction SilentlyContinue
  $expected = if ($name -eq 'hermes-gateway') { Join-Path $rootDir 'hermes-home\bin\hermes.exe' } elseif ($name -eq 'ollama-local') { (Get-Command ollama -ErrorAction Stop).Source } else { Join-Path $rootDir 'venv\Scripts\python.exe' }
  if ($name -eq 'hermes-gateway' -and $process -and $process.ExecutablePath -eq $expected) {
    $env:HERMES_HOME = Join-Path $rootDir 'hermes-home'
    & $expected gateway stop | Out-Null
    Start-Sleep -Milliseconds 800
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $id" -ErrorAction SilentlyContinue
  }
  if ($process -and $process.ExecutablePath -eq $expected) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue; Write-Host "Stopped $name ($id)." }
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
