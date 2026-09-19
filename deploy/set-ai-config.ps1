param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [Parameter(Mandatory = $true)]
    [string]$ChatModel,
    [Parameter(Mandatory = $true)]
    [string]$EmbeddingModel
)

$ErrorActionPreference = 'Stop'
$EnvFile = Join-Path $PSScriptRoot '.env'
if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw 'deploy/.env is missing; run python deploy/init_env.py first'
}

$secureKey = Read-Host 'OpenAI-compatible API key' -AsSecureString
$credential = [pscredential]::new('local', $secureKey)
$apiKey = $credential.GetNetworkCredential().Password
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw 'API key cannot be empty'
}

$values = [ordered]@{
    WANWU_MODEL_BASE_URL = $BaseUrl.TrimEnd('/')
    WANWU_MODEL_API_KEY = $apiKey
    WANWU_CHAT_MODEL = $ChatModel
    WANWU_EMBEDDING_MODEL = $EmbeddingModel
    WANWU_EMBEDDING_DIMENSION = '1024'
}

$lines = [Collections.Generic.List[string]]::new()
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($line in Get-Content -LiteralPath $EnvFile) {
    $matched = $false
    foreach ($key in $values.Keys) {
        if ($line.StartsWith("$key=", [StringComparison]::Ordinal)) {
            $lines.Add("$key=$($values[$key])")
            [void]$seen.Add($key)
            $matched = $true
            break
        }
    }
    if (-not $matched) { $lines.Add($line) }
}
foreach ($key in $values.Keys) {
    if (-not $seen.Contains($key)) { $lines.Add("$key=$($values[$key])") }
}

$tempFile = "$EnvFile.tmp"
try {
    [IO.File]::WriteAllLines($tempFile, $lines, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tempFile -Destination $EnvFile -Force
}
finally {
    if (Test-Path -LiteralPath $tempFile) { Remove-Item -LiteralPath $tempFile -Force }
    $apiKey = $null
    $credential = $null
    $secureKey.Dispose()
}

Write-Output 'Updated deploy/.env with real model settings; the API key was not printed.'
