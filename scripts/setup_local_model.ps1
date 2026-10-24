$ErrorActionPreference = 'Stop'
$root = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
$ollama = (Get-Command ollama -ErrorAction Stop).Source
$modelDir = Join-Path $root 'data\models\ollama'
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $modelDir,$logs | Out-Null
$env:OLLAMA_MODELS = $modelDir
$env:OLLAMA_HOST = '127.0.0.1:11435'
$uri = 'http://127.0.0.1:11435/api/tags'
try { Invoke-RestMethod $uri -TimeoutSec 2 | Out-Null }
catch {
  $server = Start-Process -FilePath $ollama -ArgumentList 'serve' -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'ollama-local.out.log') -RedirectStandardError (Join-Path $logs 'ollama-local.err.log')
  Set-Content (Join-Path $logs 'ollama-local.pid') $server.Id -Encoding ascii
  $ready = $false
  for ($i=0; $i -lt 30; $i++) { Start-Sleep -Seconds 1; try { Invoke-RestMethod $uri -TimeoutSec 2 | Out-Null; $ready=$true;break } catch { } }
  if (-not $ready) { throw 'D: Ollama server failed to start. Check logs\ollama-local.err.log.' }
}
$installed = (Invoke-RestMethod $uri -TimeoutSec 5).models | Where-Object { $_.name -eq 'qwen3.5:4b' }
if (-not $installed) { & $ollama pull qwen3.5:4b; if ($LASTEXITCODE -ne 0) { throw 'Ollama model download failed.' } }
Write-Host "Qwen 3.5 4B is available at $modelDir through $($env:OLLAMA_HOST)."
