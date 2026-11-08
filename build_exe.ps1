# Build MineLineQuest-2D.exe (run from anywhere).
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath 'icon.ico')) {
    python tools\make_icon.py
}

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name 'MineLineQuest-2D' `
    --icon 'icon.ico' `
    --add-data 'legacy;legacy' `
    main.py

Write-Host ''
Write-Host 'Built: dist\MineLineQuest-2D.exe'
