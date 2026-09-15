$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
& .\.venv\Scripts\python.exe -m portgozu @args
