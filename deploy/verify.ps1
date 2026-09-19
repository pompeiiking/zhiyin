$ErrorActionPreference = 'Stop'
$DeployRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $DeployRoot
$WanwuRoot = Join-Path $RepoRoot 'platform\wanwu'
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $RepoRoot 'platform\wanwu\docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
docker compose --project-directory $WanwuRoot --env-file $EnvFile -f $WanwuCompose -f $OverrideCompose config --quiet
$Wanwu = Invoke-RestMethod -Uri 'http://127.0.0.1:8081/user/api/v1/base/custom' -TimeoutSec 15 -NoProxy
$Zhiyin = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/healthz' -TimeoutSec 15 -NoProxy
$Bootstrap = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/v1/app/bootstrap' -TimeoutSec 15 -NoProxy
if (-not $Wanwu) { throw 'Wanwu business readiness failed' }
if ($Zhiyin.status -ne 'ok') {
    throw "zhiyin health check is not strict-ready: $($Zhiyin.status)"
}
if ($Bootstrap.code -ne 0 -or -not $Bootstrap.data) {
    throw 'zhiyin bootstrap business readiness failed'
}
Write-Output 'unified deployment baseline is ready'
