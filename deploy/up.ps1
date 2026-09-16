$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $DeployRoot
$WanwuRoot = Join-Path $RepoRoot 'platform\wanwu'
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw 'deploy/.env is missing; run python deploy/init_env.py first'
}
if (-not (docker network ls --format '{{.Name}}' | Select-String -SimpleMatch 'wanwu-net')) {
    docker network create wanwu-net | Out-Null
}
docker compose --project-directory $WanwuRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose up -d --build
