$ErrorActionPreference = 'Stop'
Write-Host 'WAKING JARVIS...' -ForegroundColor Cyan
$rootDir = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
Set-Location $rootDir
$hermesHome = Join-Path $rootDir 'hermes-home'
$hermesExe = Join-Path $hermesHome 'bin\hermes.exe'
$python = Join-Path $rootDir 'venv\Scripts\python.exe'
$logs = Join-Path $rootDir 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
if (-not (Test-Path $python)) { throw 'Run scripts/setup.ps1 first; the Jarvis Python environment is missing.' }
if (-not (Test-Path $hermesExe)) { throw 'Hermes Agent is not installed under D:\Jarvis\hermes-home.' }
$env:HERMES_HOME = $hermesHome
$env:OLLAMA_MODELS = Join-Path $rootDir 'data\models\ollama'
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:PATH = (Join-Path $hermesHome 'bin') + ';' + $env:PATH
$ollamaUrl = 'http://127.0.0.1:11435'
try { Invoke-WebRequest "$ollamaUrl/api/tags" -TimeoutSec 2 | Out-Null }
catch {
  $ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
  if ($ollama) {
    $local = Start-Process -FilePath $ollama -ArgumentList 'serve' -WorkingDirectory $rootDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'ollama-local.out.log') -RedirectStandardError (Join-Path $logs 'ollama-local.err.log')
    Set-Content -Path (Join-Path $logs 'ollama-local.pid') -Value $local.Id -Encoding ascii
    for ($attempt = 0; $attempt -lt 20; $attempt++) { Start-Sleep -Milliseconds 400; try { Invoke-WebRequest "$ollamaUrl/api/tags" -TimeoutSec 1 | Out-Null; break } catch { } }
  }
}
$hermesUrl = 'http://127.0.0.1:8642'
try { Invoke-WebRequest "$hermesUrl/health" -TimeoutSec 2 | Out-Null; Write-Host 'Hermes is already running.' -ForegroundColor Green }
catch {
  Write-Host 'Starting Hermes Agent gateway...' -ForegroundColor Cyan
  $proc = Start-Process -FilePath $hermesExe -ArgumentList 'gateway','run' -WorkingDirectory $rootDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'hermes-gateway.out.log') -RedirectStandardError (Join-Path $logs 'hermes-gateway.err.log')
  Set-Content -Path (Join-Path $logs 'hermes-gateway.pid') -Value $proc.Id -Encoding ascii
  $ready = $false
  for ($attempt = 0; $attempt -lt 60; $attempt++) {
    Start-Sleep -Milliseconds 500
    try { Invoke-WebRequest "$hermesUrl/health" -TimeoutSec 1 | Out-Null; $ready = $true; break } catch { }
    if ($proc.HasExited) { break }
  }
  if (-not $ready) { throw "Hermes gateway did not become ready. Inspect $logs\hermes-gateway.err.log and configure an OpenRouter key or local Ollama model." }
}
$port = if ($env:JARVIS_PORT) { $env:JARVIS_PORT } else { '8765' }
$url = "http://127.0.0.1:$port"
try { Invoke-WebRequest "$url/api/status" -TimeoutSec 2 | Out-Null; Write-Host "Jarvis is already running at $url" -ForegroundColor Green }
catch {
  $web = Start-Process -FilePath $python -ArgumentList '-m','apps.jarvis.server' -WorkingDirectory $rootDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'jarvis-web.out.log') -RedirectStandardError (Join-Path $logs 'jarvis-web.err.log')
  Set-Content -Path (Join-Path $logs 'jarvis-web.pid') -Value $web.Id -Encoding ascii
  $ready = $false
  for ($attempt = 0; $attempt -lt 30; $attempt++) { Start-Sleep -Milliseconds 400; try { Invoke-WebRequest "$url/api/status" -TimeoutSec 1 | Out-Null; $ready = $true; break } catch { } }
  if (-not $ready) { throw "Jarvis web server did not start. Inspect $logs\jarvis-web.err.log." }
}
Start-Process $url
Write-Host "Jarvis is ready at $url" -ForegroundColor Green
