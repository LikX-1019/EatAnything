[CmdletBinding()]
param(
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Start',
    [string]$ServerHost = '121.43.97.186',
    [string]$SshUser = 'root',
    [string]$IdentityFile = (Join-Path $env:USERPROFILE '.ssh\codex_eatanything_temp_ed25519'),
    [string]$PostgresContainer = 'eatanything-test-postgres-1',
    [int]$LocalPostgresPort = 5433,
    [int]$LocalMinioPort = 9000
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$statePath = Join-Path ([System.IO.Path]::GetTempPath()) 'eatanything-server-tunnel.json'
$stdoutPath = Join-Path ([System.IO.Path]::GetTempPath()) 'eatanything-server-tunnel.out.log'
$stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) 'eatanything-server-tunnel.err.log'
$backendDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Get-TunnelState {
    if (-not (Test-Path -LiteralPath $statePath)) { return $null }
    try {
        return Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Get-RunningTunnelProcess {
    $state = Get-TunnelState
    if ($null -eq $state -or -not $state.pid) { return $null }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($state.pid)" -ErrorAction SilentlyContinue
    if ($null -eq $process -or $process.Name -notlike 'ssh*' -or $process.CommandLine -notlike "*$ServerHost*") {
        return $null
    }
    return $process
}

function Remove-StateFiles {
    foreach ($path in @($statePath, $stdoutPath, $stderrPath)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }
}

function Test-LocalPortAvailable([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        $listener.Stop()
    }
}

function Wait-LocalPort([int]$Port) {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $task = $client.ConnectAsync([System.Net.IPAddress]::Loopback, $Port)
            if ($task.Wait(250) -and $client.Connected) { return $true }
        }
        catch {
            # SSH 进程可能仍在启动。
        }
        finally {
            $client.Dispose()
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Invoke-ConnectionVerification {
    Push-Location $backendDir
    try {
        python 'scripts\verify_server_tunnel.py'
        if ($LASTEXITCODE -ne 0) {
            throw "连接验证失败，退出码：$LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

if ($Action -eq 'Status') {
    $process = Get-RunningTunnelProcess
    if ($null -eq $process) {
        Write-Output '服务器隧道未运行。'
        exit 1
    }
    Write-Output "服务器隧道正在运行（PID $($process.ProcessId)）。"
    Invoke-ConnectionVerification
    exit 0
}

if ($Action -eq 'Stop') {
    $process = Get-RunningTunnelProcess
    if ($null -ne $process) {
        Stop-Process -Id $process.ProcessId -Force
        Write-Output "已停止服务器隧道（PID $($process.ProcessId)）。"
    }
    else {
        Write-Output '服务器隧道原本未运行。'
    }
    Remove-StateFiles
    exit 0
}

$existingProcess = Get-RunningTunnelProcess
if ($null -ne $existingProcess) {
    Write-Output "服务器隧道已在运行（PID $($existingProcess.ProcessId)）。"
    Invoke-ConnectionVerification
    exit 0
}
Remove-StateFiles

if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw "未找到 SSH 身份密钥文件：$IdentityFile"
}
if ($PostgresContainer -notmatch '^[A-Za-z0-9_.-]+$') {
    throw 'PostgresContainer 包含不支持的字符。'
}
if (-not (Test-LocalPortAvailable $LocalPostgresPort)) {
    throw "本机 PostgreSQL 端口 $LocalPostgresPort 已被占用。"
}
if (-not (Test-LocalPortAvailable $LocalMinioPort)) {
    throw "本机 MinIO 端口 $LocalMinioPort 已被占用。"
}

$sshBaseArguments = @(
    '-i', $IdentityFile,
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'ConnectTimeout=8'
)
$remotePostgresIp = (& ssh @sshBaseArguments "$SshUser@$ServerHost" "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $PostgresContainer").Trim()
if ($LASTEXITCODE -ne 0 -or -not [System.Net.IPAddress]::TryParse($remotePostgresIp, [ref]$null)) {
    throw '无法解析服务器 PostgreSQL 容器地址。'
}

$sshArguments = @(
    $sshBaseArguments
    '-o', 'ExitOnForwardFailure=yes'
    '-o', 'ServerAliveInterval=30'
    '-o', 'ServerAliveCountMax=3'
    '-N'
    '-L', "127.0.0.1:${LocalPostgresPort}:${remotePostgresIp}:5432"
    '-L', "127.0.0.1:${LocalMinioPort}:127.0.0.1:9000"
    "$SshUser@$ServerHost"
)

$process = Start-Process -FilePath 'ssh.exe' -ArgumentList $sshArguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
try {
    if (-not (Wait-LocalPort $LocalPostgresPort) -or -not (Wait-LocalPort $LocalMinioPort)) {
        if ($process.HasExited -and (Test-Path -LiteralPath $stderrPath)) {
            $details = Get-Content -Raw -LiteralPath $stderrPath
            throw "SSH 隧道在就绪前退出：$details"
        }
        throw 'SSH 隧道未能在规定时间内就绪。'
    }

    [System.IO.File]::WriteAllText(
        $statePath,
        (@{
            pid = $process.Id
            server = $ServerHost
            postgres_port = $LocalPostgresPort
            minio_port = $LocalMinioPort
            started_at = [DateTimeOffset]::Now.ToString('o')
        } | ConvertTo-Json),
        [System.Text.UTF8Encoding]::new($false)
    )
    Invoke-ConnectionVerification
    Write-Output "服务器隧道已就绪（PID $($process.Id)）。"
    Write-Output "PostgreSQL: 127.0.0.1:$LocalPostgresPort"
    Write-Output "MinIO:      127.0.0.1:$LocalMinioPort"
}
catch {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    Remove-StateFiles
    throw
}
