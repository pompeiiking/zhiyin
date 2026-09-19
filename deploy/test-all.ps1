param(
    [ValidateSet('real', 'service')]
    [string]$AiMode = 'real',
    [bool]$KeepProbeData = $false
)

$ErrorActionPreference = 'Stop'
$DeployRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent $DeployRoot
$WanwuRoot = Join-Path $RepoRoot 'platform\wanwu'
$EnvFile = Join-Path $DeployRoot '.env'
$WanwuCompose = Join-Path $WanwuRoot 'docker-compose.yaml'
$OverrideCompose = Join-Path $DeployRoot 'compose.yaml'
$RunId = 'zhiyin-smoke-' + (Get-Date -Format 'yyyyMMddHHmmss')
$ReportDir = Join-Path $DeployRoot "reports\$RunId"
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$ComposeArgs = @(
    'compose', '--project-directory', $WanwuRoot, '--env-file', $EnvFile,
    '-f', $WanwuCompose, '-f', $OverrideCompose
)
$results = [Collections.Generic.List[object]]::new()

function Add-Result([string]$Service, [string]$Probe, [string]$Status, [double]$DurationMs, [string]$Detail) {
    $results.Add([PSCustomObject]@{
        service = $Service
        probe = $Probe
        status = $Status
        duration_ms = [math]::Round($DurationMs, 1)
        detail = $Detail
    })
}

function Invoke-Probe([string]$Service, [string]$Probe, [scriptblock]$Action) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $savedErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5 turns native stderr into ErrorRecord objects.  A
        # number of healthy Docker/Kafka commands write progress to stderr, so
        # use the process exit code as the native-command source of truth.
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = 0
        $detail = & $Action 2>&1 | Out-String
        if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
            throw "command exited with ${LASTEXITCODE}: $detail"
        }
        Add-Result $Service $Probe 'passed' $timer.Elapsed.TotalMilliseconds $detail.Trim()
    }
    catch {
        Add-Result $Service $Probe 'failed' $timer.Elapsed.TotalMilliseconds $_.Exception.Message
    }
    finally {
        $ErrorActionPreference = $savedErrorActionPreference
        $timer.Stop()
    }
}

function Compose([string[]]$Arguments) {
    & docker @ComposeArgs @Arguments
}

function Test-InternalPort([string]$Service, [int]$Port) {
    Compose @('exec', '-T', 'zhiyin-api', 'python', '-c', "import socket; s=socket.create_connection(('$Service',$Port),5); s.close()")
}

function Invoke-LocalJson([string]$Uri) {
    $raw = & curl.exe --noproxy '*' --fail --silent --show-error $Uri
    if ($LASTEXITCODE -ne 0) { throw "HTTP request failed for $Uri" }
    return ($raw | ConvertFrom-Json)
}

$portMap = [ordered]@{
    mysql = 3306; redis = 6379; minio = 9000; kafka = 9092; es = 9200
    'bff-service' = 6668; 'iam-service' = 8888; 'model-service' = 8989
    'mcp-service' = 9898; 'knowledge-service' = 8889; 'rag-service' = 9640
    'assistant-service' = 8890; 'app-service' = 9988; agentscope = 6672
    rag = 8681; agent = 7258; nginx = 8081; pgvector = 5432
    'zhiyin-api' = 8000; 'zhiyin-web' = 8080
}

try {
    Invoke-Probe 'compose' 'render' { Compose @('config', '--quiet') }
    foreach ($entry in $portMap.GetEnumerator()) {
        Invoke-Probe $entry.Key 'tcp-readiness' { Test-InternalPort $entry.Key $entry.Value }
    }

    Invoke-Probe 'mysql' 'create/read/update/delete' {
        $code = "import os,pymysql; c=pymysql.connect(host='mysql',user='root',password=os.environ['WANWU_MYSQL_PASSWORD'],database='zhiyin_service',autocommit=True); q=c.cursor(); q.execute('CREATE TABLE IF NOT EXISTS smoke_probe(id VARCHAR(80) PRIMARY KEY, value VARCHAR(80))'); q.execute('INSERT INTO smoke_probe VALUES (%s,%s) ON DUPLICATE KEY UPDATE value=%s',(os.environ['ZHIYIN_SMOKE_RUN_ID'],'created','created')); q.execute('UPDATE smoke_probe SET value=%s WHERE id=%s',('updated',os.environ['ZHIYIN_SMOKE_RUN_ID'])); q.execute('SELECT value FROM smoke_probe WHERE id=%s',(os.environ['ZHIYIN_SMOKE_RUN_ID'],)); assert q.fetchone()[0]=='updated'; q.execute('DELETE FROM smoke_probe WHERE id=%s',(os.environ['ZHIYIN_SMOKE_RUN_ID'],)); c.close()"
        Compose @('exec', '-T', '--env', "ZHIYIN_SMOKE_RUN_ID=$RunId", 'zhiyin-api', 'python', '-c', $code)
    }
    Invoke-Probe 'redis' 'create/read/ttl/delete' {
        $line = Get-Content $EnvFile | Where-Object { $_ -like 'WANWU_REDIS_PASSWORD=*' } | Select-Object -First 1
        $secret = ($line -split '=', 2)[1]
        docker exec redis-wanwu redis-cli -a $secret --no-auth-warning SET $RunId ok EX 60 | Out-Null
        $value = docker exec redis-wanwu redis-cli -a $secret --no-auth-warning GET $RunId
        if ($value -ne 'ok') { throw 'Redis probe value mismatch' }
        docker exec redis-wanwu redis-cli -a $secret --no-auth-warning DEL $RunId | Out-Null
    }
    Invoke-Probe 'kafka' 'create/produce/consume/delete' {
        $payload = "$RunId-payload"
        $keep = if ($KeepProbeData) { '1' } else { '0' }
        $script = @'
set -euo pipefail
cfg=/tmp/zhiyin-smoke-client.properties
printf 'security.protocol=SASL_PLAINTEXT\nsasl.mechanism=PLAIN\nsasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username="%s" password="%s";\n' "$KAFKA_CLIENT_USERS" "$KAFKA_CLIENT_PASSWORD" > "$cfg"
trap 'rm -f "$cfg"' EXIT
/opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --command-config "$cfg" --create --if-not-exists --topic __TOPIC__ --partitions 1 --replication-factor 1
printf '%s\n' '__PAYLOAD__' | /opt/bitnami/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --producer.config "$cfg" --topic __TOPIC__
value=$(/opt/bitnami/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --consumer.config "$cfg" --topic __TOPIC__ --from-beginning --max-messages 1 --timeout-ms 15000)
test "$value" = '__PAYLOAD__'
if [ '__KEEP__' = 0 ]; then
  /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --command-config "$cfg" --delete --topic __TOPIC__
fi
'@
        $script = $script.Replace('__TOPIC__', $RunId).Replace('__PAYLOAD__', $payload).Replace('__KEEP__', $keep)
        docker exec kafka-wanwu bash -lc $script
    }
    Invoke-Probe 'pgvector/minio/mysql/redis' 'runtime-crud' {
        Compose @('--profile', 'verify', 'run', '--rm', 'zhiyin-runtime-verify')
    }
    $healthProbe = if ($AiMode -eq 'real') { 'strict-health' } else { 'service-health' }
    Invoke-Probe 'zhiyin-api' $healthProbe {
        $health = Invoke-LocalJson 'http://127.0.0.1:8080/healthz'
        if ($AiMode -eq 'real' -and $health.status -ne 'ok') { throw "health status is $($health.status)" }
        if ($AiMode -eq 'service' -and $health.status -notin @('ok', 'degraded')) { throw "invalid health status: $($health.status)" }
        $health | ConvertTo-Json -Depth 8
    }
    Invoke-Probe 'zhiyin-api' 'bootstrap' {
        $body = Invoke-LocalJson 'http://127.0.0.1:8080/api/v1/app/bootstrap'
        if ($body.code -ne 0 -or -not $body.data) { throw 'bootstrap response is not successful' }
        'bootstrap=ok'
    }
    Invoke-Probe 'nginx' 'wanwu-routes' {
        $wanwu = Invoke-LocalJson 'http://127.0.0.1:8081/user/api/v1/base/custom'
        if ($wanwu.code -ne 0 -or -not $wanwu.data) { throw 'Wanwu business readiness failed' }
        'wanwu-route=ok'
    }
    Invoke-Probe 'wanwu-business-services' 'real-object-create/read/update/delete/cleanup' {
        Compose @(
            'exec', '-T',
            '--env', "ZHIYIN_SMOKE_RUN_ID=$RunId",
            'zhiyin-api', 'python', 'scripts/verify_wanwu_business.py'
        )
    }

    if ($AiMode -eq 'real') {
        Invoke-Probe 'pami-ai' 'real-llm-embedding-rag' {
            $required = 'WANWU_MODEL_BASE_URL', 'WANWU_MODEL_API_KEY', 'WANWU_CHAT_MODEL', 'WANWU_EMBEDDING_MODEL', 'ZHIYIN_PAMI_AGENT_API_KEY', 'ZHIYIN_PAMI_RAG_API_KEY', 'ZHIYIN_PAMI_EMBEDDING_MODEL_ID'
            $map = @{}
            Get-Content $EnvFile | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object { $p = $_ -split '=', 2; $map[$p[0]] = $p[1] }
            $missing = $required | Where-Object { [string]::IsNullOrWhiteSpace($map[$_]) }
            if ($missing) { throw ('Missing real AI configuration: ' + ($missing -join ', ')) }
            Compose @('exec', '-T', 'zhiyin-api', 'python', 'scripts/verify_pami_runtime.py')
        }
    }
}
finally {
    $jsonPath = Join-Path $ReportDir 'results.json'
    $results | ConvertTo-Json -Depth 6 | Out-File -LiteralPath $jsonPath -Encoding utf8
    $failed = @($results | Where-Object status -eq 'failed')
    $summary = @(
        "# $RunId"
        ''
        "- passed: $(@($results | Where-Object status -eq 'passed').Count)"
        "- failed: $($failed.Count)"
        ''
        '| service | probe | status | detail |'
        '| --- | --- | --- | --- |'
    )
    foreach ($item in $results) {
        $detail = ($item.detail -replace '[\r\n]+', ' ') -replace '\|', '\|'
        $summary += "| $($item.service) | $($item.probe) | $($item.status) | $detail |"
    }
    $summary | Out-File -LiteralPath (Join-Path $ReportDir 'summary.md') -Encoding utf8
    Compose @('ps', '-a') 2>&1 | Out-File -LiteralPath (Join-Path $ReportDir 'compose-ps.txt') -Encoding utf8
    if ($failed.Count -gt 0) {
        Compose @('logs', '--tail', '200') 2>&1 | Out-File -LiteralPath (Join-Path $ReportDir 'compose-logs.txt') -Encoding utf8
        Write-Error "$($failed.Count) probes failed; report: $ReportDir"
    }
    Write-Output "all probes passed; report: $ReportDir"
}
