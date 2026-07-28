param(
    [string]$BackupPath = '/tmp/recruiting-workflows-before-subworkflow-repair.json',
    [string]$RepairedPath = '/tmp/recruiting-email-monitoring-repaired.json'
)

$ErrorActionPreference = 'Stop'

function Invoke-RecruitingCompose {
    param([string[]]$ComposeArgs)

    & docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($ComposeArgs -join ' ') failed with exit code $LASTEXITCODE."
    }
}

Invoke-RecruitingCompose @('exec', '-T', 'n8n', 'n8n', 'export:workflow', '--all', "--output=$BackupPath")
$summaryJson = & docker compose exec -T n8n node /workflows/repair-subworkflow-references.mjs $BackupPath $RepairedPath
if ($LASTEXITCODE -ne 0) {
    throw 'The sub-workflow reference repair could not create a repaired parent workflow.'
}

$summary = $summaryJson | ConvertFrom-Json
if ($summary.active) {
    throw '01 Email Monitoring is active. Deactivate it in n8n, rerun this script, then reactivate it after reviewing the repaired workflow.'
}

Invoke-RecruitingCompose @('exec', '-T', 'n8n', 'n8n', 'import:workflow', "--input=$RepairedPath")
Write-Output "Repaired $($summary.workflowName) ($($summary.workflowId)). Backup: $BackupPath"
