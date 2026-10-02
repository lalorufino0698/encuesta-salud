$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& "$PSScriptRoot/.venv/Scripts/python.exe" -m uvicorn app.domain_main:app --host 0.0.0.0 --port 8001
