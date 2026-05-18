# Run Django management commands with the project venv when present.
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root 'venv\Scripts\python.exe'
$ManagePy = Join-Path $Root 'manage.py'

if (Test-Path $VenvPython) {
    & $VenvPython $ManagePy @args
} else {
    Write-Warning 'venv not found — using system python. Run: python -m venv venv; .\venv\Scripts\pip install -r requirements.txt'
    & python $ManagePy @args
}
exit $LASTEXITCODE
