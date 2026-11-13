param([switch]$Elevated)

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload = Join-Path $PackageRoot 'payload'
$RuntimeDir = Join-Path $env:LOCALAPPDATA 'SpeedEditorPremiere'
$PremiereRoot = 'C:\Program Files\Adobe'

function Test-Administrator {
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = [Security.Principal.WindowsPrincipal]::new($Identity)
    return $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    $Arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $MyInvocation.MyCommand.Path),
        '-Elevated'
    )
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $Arguments -Wait
    exit $LASTEXITCODE
}

if (Get-Process -Name 'Adobe Premiere Pro' -ErrorAction SilentlyContinue) {
    throw 'Chiudi Adobe Premiere Pro prima di installare o aggiornare il plug-in.'
}

$Required = @(
    'SpeedEditorBridge.exe',
    'premiere_mapping.default.json',
    'SpeedEditorPremiere.acsrf',
    'SpeedEditorPremiere.cmd',
    'SpeedEditorControls-1.1.0.ccx',
    'THIRD_PARTY_NOTICES.md'
)
foreach ($Name in $Required) {
    if (-not (Test-Path -LiteralPath (Join-Path $Payload $Name))) {
        throw "File mancante nel pacchetto: $Name"
    }
}

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Payload 'SpeedEditorBridge.exe') -Destination $RuntimeDir -Force
Copy-Item -LiteralPath (Join-Path $Payload 'THIRD_PARTY_NOTICES.md') -Destination $RuntimeDir -Force
$UserConfig = Join-Path $RuntimeDir 'premiere_mapping.json'
if (-not (Test-Path -LiteralPath $UserConfig)) {
    Copy-Item -LiteralPath (Join-Path $Payload 'premiere_mapping.default.json') -Destination $UserConfig
}

$PremiereInstalls = @(
    Get-ChildItem -LiteralPath $PremiereRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^Adobe Premiere Pro (20\d{2}|\(Beta\))$' } |
        Sort-Object Name
)
if (-not $PremiereInstalls) {
    throw "Nessuna installazione di Adobe Premiere Pro trovata in $PremiereRoot"
}
foreach ($Premiere in $PremiereInstalls) {
    $SurfaceDir = Join-Path $Premiere.FullName 'PlugIns\ControlSurface'
    New-Item -ItemType Directory -Path $SurfaceDir -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $Payload 'SpeedEditorPremiere.acsrf') -Destination $SurfaceDir -Force
    Copy-Item -LiteralPath (Join-Path $Payload 'SpeedEditorPremiere.cmd') -Destination $SurfaceDir -Force
    Write-Host "Control Surface installata in $($Premiere.Name)"
}

$Upia = 'C:\Program Files\Common Files\Adobe\Adobe Desktop Common\RemoteComponents\UPI\UnifiedPluginInstallerAgent\UnifiedPluginInstallerAgent.exe'
if (Test-Path -LiteralPath $Upia) {
    & $Upia /install (Join-Path $Payload 'SpeedEditorControls-1.1.0.ccx')
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Il pannello UXP non e stato installato automaticamente. Fai doppio clic sul file CCX nella cartella payload.'
    }
} else {
    Write-Warning 'Adobe UPIA non trovato. Fai doppio clic sul file CCX nella cartella payload.'
}

Write-Host ''
Write-Host 'Installazione completata.' -ForegroundColor Green
Write-Host 'In Premiere: Modifica > Preferenze > Superficie di controllo > Aggiungi > DaVinci Speed Editor.'
Write-Host 'Pannello: Finestra > UXP Plugins > Speed Editor.'
Read-Host 'Premi Invio per chiudere'
