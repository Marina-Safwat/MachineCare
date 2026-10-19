$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python backend/start_manager_demo.py
if ($LASTEXITCODE -ne 0) { throw 'Demo startup failed. See the message above; no installed records were changed.' }
