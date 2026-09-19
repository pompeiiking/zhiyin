$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $DeployRoot '..\..\..')
$WanwuRoot = Join-Path $RepoRoot 'platform\wanwu'
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
docker compose --project-directory $WanwuRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose config --quiet
$Wanwu = Invoke-RestMethod -Uri 'http://127.0.0.1:8081/user/api/v1/base/custom' -TimeoutSec 15
$Zhiyin = docker compose --project-directory $WanwuRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose exec -T zhiyin-api python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz')))"
if (-not $Wanwu) { throw 'Wanwu business readiness failed' }
if (-not $Zhiyin) { throw 'zhiyin health check failed' }
Write-Output 'unified deployment baseline is ready'
