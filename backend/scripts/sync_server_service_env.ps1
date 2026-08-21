[CmdletBinding()]
param(
    [string]$ServerHost = '121.43.97.186',
    [string]$SshUser = 'root',
    [string]$IdentityFile = (Join-Path $env:USERPROFILE '.ssh\codex_eatanything_temp_ed25519'),
    [string]$ApiContainer = 'eatanything-test-api-1',
    [string]$EnvFile = (Join-Path $PSScriptRoot '..\..\.env')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw "未找到 SSH 身份密钥文件：$IdentityFile"
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "未找到环境变量文件：$EnvFile"
}
if ($ApiContainer -notmatch '^[A-Za-z0-9_.-]+$') {
    throw 'ApiContainer 包含不支持的字符。'
}

$sshArguments = @(
    '-i', $IdentityFile,
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'ConnectTimeout=8'
)

# 容器环境变量仅保存在内存中，禁止写入文件或输出到终端。
$remoteEnvironment = @(& ssh @sshArguments "$SshUser@$ServerHost" "docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' $ApiContainer")
if ($LASTEXITCODE -ne 0) {
    throw '无法读取服务器 API 容器的环境变量。'
}

function Get-RemoteValue([string]$Name) {
    $prefix = "$Name="
    $entry = $remoteEnvironment | Where-Object { $_.StartsWith($prefix, [StringComparison]::Ordinal) } | Select-Object -First 1
    if ($null -eq $entry) {
        throw "服务器缺少必需配置：$Name"
    }
    $value = $entry.Substring($prefix.Length)
    if ([string]::IsNullOrWhiteSpace($value) -or $value.Contains("`r") -or $value.Contains("`n") -or $value.Contains([char]0)) {
        throw "服务器配置包含不支持的值：$Name"
    }
    return $value
}

function ConvertTo-DotEnvLiteral([string]$Value) {
    return "'" + $Value.Replace('\', '\\').Replace("'", "\'") + "'"
}

$updates = [ordered]@{
    POSTGRES_HOST = '127.0.0.1'
    POSTGRES_PORT = '5433'
    POSTGRES_DB = Get-RemoteValue 'POSTGRES_DB'
    POSTGRES_USER = Get-RemoteValue 'POSTGRES_USER'
    POSTGRES_PASSWORD = Get-RemoteValue 'POSTGRES_PASSWORD'
    MINIO_ENDPOINT = '127.0.0.1:9000'
    MINIO_ACCESS_KEY = Get-RemoteValue 'MINIO_ACCESS_KEY'
    MINIO_SECRET_KEY = Get-RemoteValue 'MINIO_SECRET_KEY'
    MINIO_BUCKET = Get-RemoteValue 'MINIO_BUCKET'
    MINIO_SECURE = 'false'
    MINIO_PUBLIC_URL = 'http://127.0.0.1:9000'
}

$resolvedEnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
$original = [System.IO.File]::ReadAllText($resolvedEnvFile, [System.Text.Encoding]::UTF8)
$updated = $original
foreach ($item in $updates.GetEnumerator()) {
    $pattern = "(?m)^$([regex]::Escape($item.Key))=.*$"
    if (-not [regex]::IsMatch($updated, $pattern)) {
        throw "本地缺少环境配置：$($item.Key)"
    }
    $replacement = "$($item.Key)=$(ConvertTo-DotEnvLiteral ([string]$item.Value))"
    $updated = [regex]::Replace($updated, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement }, 1)
}

$temporaryPath = "$resolvedEnvFile.server-sync"
try {
    [System.IO.File]::WriteAllText($temporaryPath, $updated, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporaryPath -Destination $resolvedEnvFile -Force
}
catch {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Force
    }
    throw
}

Write-Output ('已同步服务器连接配置：' + (($updates.Keys) -join ', '))
