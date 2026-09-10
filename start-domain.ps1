$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& "$PSScriptRoot/.venv/Scripts/python.exe" -m uvicorn app.domain_main:app --host 127.0.0.1 --port 8001
