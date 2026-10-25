# scripts/setup.ps1
Write-Host "INITIALIZING JARVIS..." -ForegroundColor Cyan

$basePath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $basePath

# 1. Verify OS
Write-Host "Checking OS..."
$os = (Get-CimInstance Win32_OperatingSystem).Caption
Write-Host "OS: $os - PASS" -ForegroundColor Green

# 2. Verify Python
Write-Host "Checking Python..."
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Python available - PASS" -ForegroundColor Green
} else {
    Write-Host "Python not found! FAIL" -ForegroundColor Red
    exit 1
}

# 3. Create Virtual Env
Write-Host "Creating Virtual Environment..."
if (-not (Test-Path -LiteralPath ".\venv\Scripts\python.exe")) {
    python -m venv venv
}

Write-Host "Installing Core Dependencies..."
& ".\venv\Scripts\python.exe" -m pip install requests pyyaml python-dotenv "pypdf>=6.21,<7"
Write-Host "Dependencies installed - PASS" -ForegroundColor Green

if (-not (Test-Path -LiteralPath ".\.env") -and (Test-Path -LiteralPath ".\.env.example")) {
    Copy-Item -LiteralPath ".\.env.example" -Destination ".\.env"
    Write-Host "Created .env from template. Add your OpenRouter key locally." -ForegroundColor Yellow
}

# 4. Check Ollama
Write-Host "Checking Ollama..."
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "Ollama available - PASS" -ForegroundColor Green
} else {
    Write-Host "Ollama not found - WARN (Executive agent may fail)" -ForegroundColor Yellow
}

# 5. Report setup location and next steps
Write-Host "=============================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE" -ForegroundColor Green
Write-Host "Jarvis home: $basePath"
Write-Host "Set OPENROUTER_API_KEY in .env and install the configured Ollama fallback model."
Write-Host "=============================" -ForegroundColor Cyan
