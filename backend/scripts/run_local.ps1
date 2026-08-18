[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'D:\develop\anaconda3\python.exe'
$env:PYTHONPATH = $projectRoot

$arguments = @('-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', $Port)
if ($Reload) { $arguments += '--reload' }
& $python @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
