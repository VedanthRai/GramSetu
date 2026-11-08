# Build the frontend and start GramSetu on http://127.0.0.1:8000 (Windows PowerShell).
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
$py = if ($env:GRAMSETU_PYTHON) { $env:GRAMSETU_PYTHON } elseif (Test-Path "$root\.venv\Scripts\python.exe") { "$root\.venv\Scripts\python.exe" } else { "python" }
Push-Location frontend; npm install --silent; npm run build --silent; Pop-Location
Set-Location "$root\backend"
& $py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
