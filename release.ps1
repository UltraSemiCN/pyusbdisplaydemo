# Build UsbDisplayHud.exe + themes/ + photos/ entirely under .\release\
# Usage:
#   .\release.ps1
#   .\release.ps1 -Clean

[CmdletBinding()]
param(
    [switch]$Clean,
    [string]$Version = "0.0.1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvCandidates = @(
    (Join-Path $Root ".venv"),
    (Join-Path (Split-Path -Parent $Root) ".venv")
)
$VenvDir = $VenvCandidates | Where-Object { Test-Path (Join-Path $_ "Scripts\python.exe") } | Select-Object -First 1
if (-not $VenvDir) {
    throw "Missing .venv. Run from repo root: python -m venv .venv ; .\.venv\Scripts\pip install -r pyusbdisplaydemo\requirements.txt"
}
$Python = Join-Path $VenvDir "Scripts\python.exe"
$PyInstaller = Join-Path $VenvDir "Scripts\pyinstaller.exe"
$ReleaseDir = Join-Path $Root "release"
$WorkDir = Join-Path $ReleaseDir "_build"
$DistTmp = Join-Path $ReleaseDir "_dist"
$AppName = "UsbDisplayHud"
Write-Host ("Using venv: " + $VenvDir)

Write-Host "==> Ensure packaging deps"
& $Python -m pip install -q -r requirements.txt
if (-not (Test-Path $PyInstaller)) {
    & $Python -m pip install -q pyinstaller
}

# Avoid file locks from a running packaged app.
Get-Process -Name $AppName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 400

if ($Clean) {
    Write-Host "==> Clean release/ and legacy root build outputs"
    if (Test-Path $ReleaseDir) {
        Remove-Item -Recurse -Force $ReleaseDir
    }
    foreach ($legacy in @("build", "dist")) {
        $p = Join-Path $Root $legacy
        if (Test-Path $p) {
            Remove-Item -Recurse -Force $p
        }
    }
    $spec = Join-Path $Root ($AppName + ".spec")
    if (Test-Path $spec) {
        Remove-Item -Force $spec
    }
    Get-ChildItem -Path $Root -Filter "$AppName-*.zip" -File -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -Force $_.FullName
    }
}

New-Item -ItemType Directory -Force -Path $WorkDir, $DistTmp | Out-Null

Write-Host "==> PyInstaller onefile (intermediate output under release/_build, release/_dist)"
$AssetsDir = Join-Path $Root "assets"
$AddData = "$AssetsDir;assets"
& $PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name $AppName `
    --collect-all msdisplay `
    --hidden-import app.themes.base `
    --hidden-import app.themes.draw_utils `
    --hidden-import app.themes.loader `
    --hidden-import app.core.metrics `
    --hidden-import app.core.orientation `
    --hidden-import app.core.slideshow `
    --hidden-import app.i18n `
    --add-data $AddData `
    --paths $Root `
    --distpath $DistTmp `
    --workpath $WorkDir `
    --specpath $WorkDir `
    (Join-Path $Root "run_app.py")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$BuiltExe = Join-Path $DistTmp ($AppName + ".exe")
if (-not (Test-Path $BuiltExe)) {
    throw "Build failed: exe not found at $BuiltExe"
}

Write-Host "==> Assemble release/ (exe + themes + photos)"
$ExeOut = Join-Path $ReleaseDir ($AppName + ".exe")
Copy-Item -Path $BuiltExe -Destination $ExeOut -Force

$ThemesSrc = Join-Path $Root "themes"
$ThemesDst = Join-Path $ReleaseDir "themes"
if (Test-Path $ThemesDst) {
    Remove-Item -Recurse -Force $ThemesDst
}
New-Item -ItemType Directory -Force -Path $ThemesDst | Out-Null
if (-not (Test-Path $ThemesSrc)) {
    throw "Assemble failed: missing themes/ source"
}
Get-ChildItem -Path $ThemesSrc -File | Where-Object {
    ($_.Extension -eq ".py" -or $_.Extension -eq ".txt" -or $_.Extension -eq ".md") -and
    ($_.Name -notlike "*.pyc")
} | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $ThemesDst -Force
}

$PhotosSrc = Join-Path $Root "photos"
$PhotosDst = Join-Path $ReleaseDir "photos"
if (Test-Path $PhotosDst) {
    Remove-Item -Recurse -Force $PhotosDst
}
New-Item -ItemType Directory -Force -Path $PhotosDst | Out-Null
if (Test-Path $PhotosSrc) {
    Get-ChildItem -Path $PhotosSrc -File | Where-Object {
        $_.Extension -match '^\.(jpg|jpeg|png|bmp|webp|txt|md)$'
    } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $PhotosDst -Force
    }
}
$PhotoCount = @(Get-ChildItem -Path $PhotosDst -File | Where-Object {
    $_.Extension -match '^\.(jpg|jpeg|png|bmp|webp)$'
}).Count
if ($PhotoCount -eq 0) {
    $PhotosReadme = Join-Path $PhotosDst "README.txt"
    if (-not (Test-Path $PhotosReadme)) {
        @(
            "Put image files here for Photo Slideshow mode.",
            "Supported: jpg / jpeg / png / bmp / webp."
        ) | Set-Content -Path $PhotosReadme -Encoding utf8
    }
}

Write-Host "==> Remove PyInstaller intermediates"
foreach ($tmp in @($WorkDir, $DistTmp)) {
    if (Test-Path $tmp) {
        Remove-Item -Recurse -Force $tmp
    }
}
foreach ($legacy in @("build", "dist")) {
    $p = Join-Path $Root $legacy
    if (Test-Path $p) {
        Remove-Item -Recurse -Force $p
    }
}

$ThemeSample = Join-Path $ThemesDst "classic_portrait.py"
if (-not (Test-Path $ExeOut)) {
    throw "Assemble failed: missing exe"
}
if (-not (Test-Path $ThemeSample)) {
    throw "Assemble failed: themes incomplete"
}

$ExeSizeMb = [math]::Round((Get-Item $ExeOut).Length / 1MB, 1)

Write-Host "==> Zip release/ -> UsbDisplayHud-$Version.zip"
$ZipName = "$AppName-$Version.zip"
$ZipPath = Join-Path $Root $ZipName
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}
Compress-Archive -Path (Join-Path $ReleaseDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal
$ZipSizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)

Write-Host ""
Write-Host ("OK: " + $ReleaseDir)
Write-Host ("  - " + $AppName + ".exe  (" + $ExeSizeMb + " MB)")
Write-Host "  - themes\"
Get-ChildItem -Path $ThemesDst | ForEach-Object { Write-Host ("      " + $_.Name) }
Write-Host ("  - photos\  (" + $PhotoCount + " images)")
Get-ChildItem -Path $PhotosDst | ForEach-Object { Write-Host ("      " + $_.Name) }
Write-Host ("  - ..\" + $ZipName + "  (" + $ZipSizeMb + " MB)")
Write-Host ""
Write-Host ("Run: .\release\" + $AppName + ".exe")
