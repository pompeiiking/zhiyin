param(
    [int]$StageTimeoutSeconds = 900,
    [switch]$SkipBuild
)

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

$ComposeBase = @(
    'compose', '--project-directory', $WanwuRoot, '--env-file', $EnvFile,
    '-f', $WanwuCompose, '-f', $OverrideCompose
)

function Compose([string[]]$Arguments) {
    & docker @ComposeBase @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
}

function Wait-Service([string]$Service, [string]$Expected = 'healthy') {
    $deadline = (Get-Date).AddSeconds($StageTimeoutSeconds)
    $unhealthySince = $null
    do {
        $containerId = ((@(& docker @ComposeBase 'ps' '--all' '-q' $Service)) -join '').Trim()
        if ($containerId) {
            $state = docker inspect $containerId --format '{{.State.Status}}'
            $health = docker inspect $containerId --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}'
            if ($Expected -eq 'completed' -and $state -eq 'exited') {
                $exitCode = docker inspect $containerId --format '{{.State.ExitCode}}'
                if ($exitCode -eq '0') { return }
                throw "$Service exited with code $exitCode"
            }
            if ($Expected -eq 'running' -and $state -eq 'running') { return }
            if ($Expected -eq 'healthy' -and $health -eq 'healthy') { return }
            if ($state -eq 'exited') {
                throw "$Service failed while waiting: state=$state health=$health"
            }
            if ($health -eq 'unhealthy') {
                if ($null -eq $unhealthySince) { $unhealthySince = Get-Date }
                if (((Get-Date) - $unhealthySince).TotalSeconds -ge 60) {
                    throw "$Service remained unhealthy for 60 seconds: state=$state"
                }
            } else {
                $unhealthySince = $null
            }
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Service to become $Expected"
}

if (-not $SkipBuild) {
    Compose @('build', 'pgvector', 'zhiyin-api', 'zhiyin-web')
}

$stages = @(
    @{ Name = 'data'; Services = @('mysql', 'redis', 'minio', 'kafka', 'es-setup', 'es', 'pgvector'); Wait = @('mysql', 'redis', 'minio', 'kafka', 'es', 'pgvector'); Completed = @('es-setup') },
    @{ Name = 'init'; Services = @('mysql-worker', 'zhiyin-mysql-init', 'zhiyin-migrate'); Completed = @('mysql-worker', 'zhiyin-mysql-init', 'zhiyin-migrate') },
    @{ Name = 'wanwu-services'; Services = @('iam-service', 'model-service', 'mcp-service', 'knowledge-service', 'rag-service', 'assistant-service', 'app-service', 'bff-service'); Wait = @('iam-service', 'model-service', 'mcp-service', 'knowledge-service', 'rag-service', 'assistant-service', 'app-service', 'bff-service') },
    @{ Name = 'ai-engines'; Services = @('agentscope', 'rag', 'agent'); Wait = @('agentscope', 'rag', 'agent') },
    @{ Name = 'entrypoints'; Services = @('nginx', 'zhiyin-api', 'zhiyin-web'); Wait = @('nginx', 'zhiyin-api', 'zhiyin-web') }
)

foreach ($stage in $stages) {
    Write-Output "starting deployment stage: $($stage.Name)"
    Compose (@('up', '-d', '--no-build') + $stage.Services)
    if ($stage.ContainsKey('Wait')) {
        foreach ($service in $stage.Wait) { Wait-Service $service }
    }
    if ($stage.ContainsKey('Running')) {
        foreach ($service in $stage.Running) { Wait-Service $service 'running' }
    }
    if ($stage.ContainsKey('Completed')) {
        foreach ($service in $stage.Completed) { Wait-Service $service 'completed' }
    }
}

Write-Output 'all deployment stages started successfully'
