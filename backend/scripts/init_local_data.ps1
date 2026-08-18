[CmdletBinding()]
param(
    [string]$EnvFile = (Join-Path $PSScriptRoot '..\..\.env')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Read-DotEnv {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Environment file not found: $Path"
    }

    $values = @{}
    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        if ($line -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            throw "Malformed environment entry for key-safe parser: $rawLine"
        }

        $key = $matches[1]
        $value = $matches[2].Trim()
        if ($value.Length -ge 2 -and (($value[0] -eq '"' -and $value[-1] -eq '"') -or ($value[0] -eq "'" -and $value[-1] -eq "'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$key] = $value
    }
    return $values
}

function Require-Value {
    param([hashtable]$Values, [string]$Key)
    if (-not $Values.ContainsKey($Key) -or [string]::IsNullOrWhiteSpace($Values[$Key])) {
        throw "Missing required environment variable: $Key"
    }
    return [string]$Values[$Key]
}

function Invoke-Docker {
    param([Parameter(Mandatory)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed with exit code $LASTEXITCODE"
    }
}

function Copy-And-RunSql {
    param(
        [string]$Container,
        [string]$Database,
        [string]$User,
        [string]$LocalPath,
        [string]$ContainerPath
    )

    Invoke-Docker @('cp', $LocalPath, "${Container}:${ContainerPath}")
    try {
        Invoke-Docker @('exec', $Container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $User, '-d', $Database, '-f', $ContainerPath)
    }
    finally {
        & docker exec $Container rm -f $ContainerPath | Out-Null
    }
}

function ConvertTo-SqlLiteral {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return 'NULL' }
    return "'" + ([string]$Value).Replace("'", "''") + "'"
}

function Save-RemoteAsset {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$Destination
    )

    $temporaryPath = "$Destination.download"
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $temporaryPath -TimeoutSec 30 -Headers @{'User-Agent' = 'EatAnything/1.0 local-seed'}
            $downloaded = Get-Item -LiteralPath $temporaryPath
            if ($downloaded.Length -lt 10000) {
                throw "Downloaded image is unexpectedly small: $($downloaded.Length) bytes"
            }
            Move-Item -LiteralPath $temporaryPath -Destination $Destination -Force
            return
        }
        catch {
            if (Test-Path -LiteralPath $temporaryPath) {
                Remove-Item -LiteralPath $temporaryPath -Force
            }
            if ($attempt -eq 4) { throw }
            Start-Sleep -Seconds ([Math]::Pow(2, $attempt))
        }
    }
}

$resolvedEnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
$envValues = Read-DotEnv -Path $resolvedEnvFile
$database = Require-Value $envValues 'POSTGRES_DB'
$pgUser = Require-Value $envValues 'POSTGRES_USER'
$bucket = Require-Value $envValues 'MINIO_BUCKET'
$minioAccessKey = Require-Value $envValues 'MINIO_ACCESS_KEY'
$minioSecretKey = Require-Value $envValues 'MINIO_SECRET_KEY'
$postgresContainer = if ($envValues.ContainsKey('POSTGRES_CONTAINER')) { $envValues.POSTGRES_CONTAINER } else { 'it_heima-postgres-1' }
$minioContainer = if ($envValues.ContainsKey('MINIO_CONTAINER')) { $envValues.MINIO_CONTAINER } else { 'it_heima-minio-1' }

if ($database -notmatch '^[A-Za-z_][A-Za-z0-9_]{0,62}$') {
    throw 'POSTGRES_DB must contain only letters, numbers, and underscores, and cannot start with a number.'
}
if ($pgUser -notmatch '^[A-Za-z_][A-Za-z0-9_]{0,62}$') {
    throw 'POSTGRES_USER must contain only letters, numbers, and underscores, and cannot start with a number.'
}
if ($bucket -notmatch '^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$') {
    throw 'MINIO_BUCKET is not a valid S3 bucket name.'
}

Invoke-Docker @('inspect', $postgresContainer) | Out-Null
Invoke-Docker @('inspect', $minioContainer) | Out-Null

$exists = & docker exec $postgresContainer psql -U $pgUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$database'"
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect PostgreSQL databases.' }
if (($exists | Out-String).Trim() -ne '1') {
    Write-Host "Creating PostgreSQL database: $database"
    Invoke-Docker @('exec', $postgresContainer, 'createdb', '-U', $pgUser, $database)
}
else {
    Write-Host "PostgreSQL database already exists: $database"
}

$databaseDir = (Resolve-Path (Join-Path $PSScriptRoot '..\database')).Path
$backendDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$assetDir = Join-Path $backendDir 'seed_assets'
$manifestPath = Join-Path $databaseDir 'seed_assets.json'
New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
$assets = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json

Write-Host 'Configuring MinIO and uploading seed images...'
Invoke-Docker @('exec', $minioContainer, 'mc', 'alias', 'set', 'eatanything-local', 'http://127.0.0.1:9000', $minioAccessKey, $minioSecretKey) | Out-Null
Invoke-Docker @('exec', $minioContainer, 'mc', 'mb', '--ignore-existing', "eatanything-local/$bucket") | Out-Null

Add-Type -AssemblyName System.Drawing
$mediaRows = New-Object System.Collections.Generic.List[string]
foreach ($asset in $assets) {
    $localPath = Join-Path $assetDir $asset.file
    Write-Host "Downloading $($asset.file)"
    Save-RemoteAsset -Uri $asset.download_url -Destination $localPath

    $tempPath = "/tmp/eat-anything-$($asset.file)"
    Invoke-Docker @('cp', $localPath, "${minioContainer}:${tempPath}")
    try {
        Invoke-Docker @('exec', $minioContainer, 'mc', 'cp', $tempPath, "eatanything-local/$bucket/$($asset.object_key)") | Out-Null
    }
    finally {
        & docker exec $minioContainer rm -f $tempPath | Out-Null
    }

    $fileInfo = Get-Item -LiteralPath $localPath
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localPath).Hash.ToLowerInvariant()
    $image = [System.Drawing.Image]::FromFile($localPath)
    try {
        $width = $image.Width
        $height = $image.Height
    }
    finally {
        $image.Dispose()
    }

    $mediaRows.Add("(" + (@(
        (ConvertTo-SqlLiteral $bucket),
        (ConvertTo-SqlLiteral $asset.object_key),
        (ConvertTo-SqlLiteral $asset.file),
        (ConvertTo-SqlLiteral 'image/jpeg'),
        $fileInfo.Length,
        $width,
        $height,
        (ConvertTo-SqlLiteral $hash),
        (ConvertTo-SqlLiteral $asset.source_provider),
        (ConvertTo-SqlLiteral $asset.source_url),
        (ConvertTo-SqlLiteral $asset.license_name),
        (ConvertTo-SqlLiteral $asset.license_url),
        (ConvertTo-SqlLiteral $asset.attribution_text)
    ) -join ', ') + ")")
}

$generatedSqlPath = Join-Path ([System.IO.Path]::GetTempPath()) ("eat-anything-media-" + [guid]::NewGuid().ToString('N') + '.sql')
$mediaSql = @"
BEGIN;
INSERT INTO media_objects (
    bucket, object_key, original_filename, content_type, size_bytes, width, height,
    checksum_sha256, source_provider, source_url, license_name, license_url, attribution_text
) VALUES
$($mediaRows -join ",`n")
ON CONFLICT (bucket, object_key) DO UPDATE SET
    original_filename = EXCLUDED.original_filename,
    content_type = EXCLUDED.content_type,
    size_bytes = EXCLUDED.size_bytes,
    width = EXCLUDED.width,
    height = EXCLUDED.height,
    checksum_sha256 = EXCLUDED.checksum_sha256,
    source_provider = EXCLUDED.source_provider,
    source_url = EXCLUDED.source_url,
    license_name = EXCLUDED.license_name,
    license_url = EXCLUDED.license_url,
    attribution_text = EXCLUDED.attribution_text;
COMMIT;
"@

try {
    [System.IO.File]::WriteAllText($generatedSqlPath, $mediaSql, [System.Text.UTF8Encoding]::new($false))
    Copy-And-RunSql -Container $postgresContainer -Database $database -User $pgUser -LocalPath (Join-Path $databaseDir '001_schema.sql') -ContainerPath '/tmp/eat-anything-001-schema.sql'
    Copy-And-RunSql -Container $postgresContainer -Database $database -User $pgUser -LocalPath $generatedSqlPath -ContainerPath '/tmp/eat-anything-media.sql'
    Copy-And-RunSql -Container $postgresContainer -Database $database -User $pgUser -LocalPath (Join-Path $databaseDir '002_seed.sql') -ContainerPath '/tmp/eat-anything-002-seed.sql'
}
finally {
    if (Test-Path -LiteralPath $generatedSqlPath) {
        Remove-Item -LiteralPath $generatedSqlPath -Force
    }
}

Write-Host 'Initialization completed successfully.'
