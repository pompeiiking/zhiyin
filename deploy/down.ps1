$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $DeployRoot
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
docker compose --project-directory $RepoRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose down
