$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pywebview pillow
python packaging/make_icon.py
python -m PyInstaller packaging/portgozu.spec --noconfirm --distpath dist --workpath build
if (-not (Test-Path "dist\FenixPortChecker.exe")) {
  throw "PyInstaller FenixPortChecker.exe uretemedi"
}
if (-not (Test-Path "packaging\portgozu.ico")) {
  throw "portgozu.ico yok"
}

dotnet tool restore
dotnet tool run wix -- build packaging/FenixPortChecker.wxs -o dist/FenixPortChecker-0.1.1.msi -arch x64
if (-not (Test-Path "dist\FenixPortChecker-0.1.1.msi")) {
  throw "MSI uretilemedi"
}
Get-Item dist\FenixPortChecker.exe, dist\FenixPortChecker-0.1.1.msi | Format-Table Name, Length
