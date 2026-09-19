param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot 'backups')
)

$ErrorActionPreference = 'Stop'
$DeployRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent $DeployRoot
$EnvFile = Join-Path $DeployRoot '.env'
if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw 'deploy/.env is missing'
}

$resolvedDeploy = [IO.Path]::GetFullPath($DeployRoot)
$resolvedOutput = [IO.Path]::GetFullPath($OutputRoot)
if (-not $resolvedOutput.StartsWith($resolvedDeploy, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Backup output must stay under deploy/: $resolvedOutput"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = Join-Path $resolvedOutput $stamp
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

function Require-Container([string]$Name) {
    $running = docker inspect -f '{{.State.Running}}' $Name 2>$null
    if ($LASTEXITCODE -ne 0 -or $running -ne 'true') {
        throw "Required container is not running: $Name"
    }
}

Require-Container 'mysql-wanwu'
Require-Container 'redis-wanwu'
Require-Container 'minio-wanwu'
Require-Container 'zhiyin-pami-frozen-pgvector-1'

docker exec mysql-wanwu sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --all-databases --single-transaction --routines --events > /tmp/zhiyin-all.sql'
if ($LASTEXITCODE -ne 0) { throw 'MySQL backup failed' }
docker cp mysql-wanwu:/tmp/zhiyin-all.sql (Join-Path $backupDir 'mysql-all.sql')

docker exec zhiyin-pami-frozen-pgvector-1 sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dumpall -U "$POSTGRES_USER" > /tmp/zhiyin-pgvector-all.sql'
if ($LASTEXITCODE -ne 0) { throw 'pgvector backup failed' }
docker cp zhiyin-pami-frozen-pgvector-1:/tmp/zhiyin-pgvector-all.sql (Join-Path $backupDir 'pgvector-all.sql')

$envMap = @{}
Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    $parts = $_ -split '=', 2
    $envMap[$parts[0]] = $parts[1]
}
docker exec redis-wanwu redis-cli -a $envMap['WANWU_REDIS_PASSWORD'] --no-auth-warning SAVE | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Redis SAVE failed' }
docker cp redis-wanwu:/data/dump.rdb (Join-Path $backupDir 'redis-dump.rdb')

$minioDir = Join-Path $backupDir 'minio-data'
New-Item -ItemType Directory -Path $minioDir | Out-Null
docker cp minio-wanwu:/data/. $minioDir
if ($LASTEXITCODE -ne 0) { throw 'MinIO backup failed' }

docker ps -a --format '{{json .}}' | Out-File -LiteralPath (Join-Path $backupDir 'containers.jsonl') -Encoding utf8
docker images --digests --format '{{json .}}' | Out-File -LiteralPath (Join-Path $backupDir 'images.jsonl') -Encoding utf8
git -C $RepoRoot rev-parse HEAD | Out-File -LiteralPath (Join-Path $backupDir 'git-commit.txt') -Encoding ascii

$required = 'mysql-all.sql', 'pgvector-all.sql', 'redis-dump.rdb'
foreach ($name in $required) {
    $path = Join-Path $backupDir $name
    if (-not (Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -eq 0) {
        throw "Backup artifact is empty: $name"
    }
}

$hashes = Get-ChildItem -LiteralPath $backupDir -Recurse -File |
    Where-Object Name -ne 'SHA256SUMS.txt' |
    ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $relative = [IO.Path]::GetRelativePath($backupDir, $_.FullName).Replace('\', '/')
        "$hash  $relative"
    }
$hashes | Out-File -LiteralPath (Join-Path $backupDir 'SHA256SUMS.txt') -Encoding ascii

[PSCustomObject]@{
    backup_dir = $backupDir
    files = (Get-ChildItem -LiteralPath $backupDir -Recurse -File).Count
    status = 'verified'
} | ConvertTo-Json | Write-Output

