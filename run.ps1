# Start the ATS webapp (no need to activate venv)
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe manage.py runserver
