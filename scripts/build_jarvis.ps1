$ErrorActionPreference = 'Stop'
$rootDir = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
$required = @(
  'Jarvis.spec',
  'scripts\jarvis_launcher.py',
  'scripts\start_jarvis.ps1',
  'scripts\stop_jarvis.ps1',
  'apps\jarvis\server.py',
  'ui\index.html'
)
foreach ($relative in $required) {
  if (-not (Test-Path (Join-Path $rootDir $relative) -PathType Leaf)) {
    throw "Cannot build Jarvis.exe. Required runtime file missing: $relative"
  }
}

$pyInstaller = Get-Command pyinstaller.exe -ErrorAction SilentlyContinue
if (-not $pyInstaller) {
  throw 'PyInstaller is missing. Install PyInstaller 6 in the build Python, then run this script again.'
}

$distDir = Join-Path $rootDir 'build\jarvis-dist'
$workDir = Join-Path $rootDir 'build\jarvis-release'
New-Item -ItemType Directory -Force -Path $distDir, $workDir | Out-Null
Push-Location $rootDir
try {
  & $pyInstaller.Source --clean --noconfirm --distpath $distDir --workpath $workDir (Join-Path $rootDir 'Jarvis.spec')
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }
} finally {
  Pop-Location
}

$builtExe = Join-Path $distDir 'Jarvis.exe'
if (-not (Test-Path $builtExe -PathType Leaf)) { throw 'PyInstaller completed without producing Jarvis.exe.' }
$targetExe = Join-Path $rootDir 'Jarvis.exe'
Copy-Item -LiteralPath $builtExe -Destination $targetExe -Force
Write-Host "Updated launcher: $targetExe"
Write-Host 'Jarvis.exe launches the runtime files beside it. Keep Jarvis.exe and the Jarvis folder together.'
