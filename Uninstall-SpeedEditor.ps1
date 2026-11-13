param([switch]$RemoveSettings)

$ErrorActionPreference = 'Stop'
$Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$Principal = [Security.Principal.WindowsPrincipal]::new($Identity)
if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $Arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $MyInvocation.MyCommand.Path))
    if ($RemoveSettings) { $Arguments += '-RemoveSettings' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $Arguments -Wait
    exit $LASTEXITCODE
}
if (Get-Process -Name 'Adobe Premiere Pro' -ErrorAction SilentlyContinue) {
    throw 'Chiudi Adobe Premiere Pro prima della disinstallazione.'
}

$PremiereRoot = 'C:\Program Files\Adobe'
Get-ChildItem -LiteralPath $PremiereRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^Adobe Premiere Pro (20\d{2}|\(Beta\))$' } |
    ForEach-Object {
        $SurfaceDir = Join-Path $_.FullName 'PlugIns\ControlSurface'
        Remove-Item -LiteralPath (Join-Path $SurfaceDir 'SpeedEditorPremiere.acsrf') -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $SurfaceDir 'SpeedEditorPremiere.cmd') -Force -ErrorAction SilentlyContinue
    }

$Upia = 'C:\Program Files\Common Files\Adobe\Adobe Desktop Common\RemoteComponents\UPI\UnifiedPluginInstallerAgent\UnifiedPluginInstallerAgent.exe'
if (Test-Path -LiteralPath $Upia) {
    & $Upia /remove 'com.codex.speededitor.premiere.settings'
}
if ($RemoveSettings) {
    $RuntimeDir = Join-Path $env:LOCALAPPDATA 'SpeedEditorPremiere'
    if (Test-Path -LiteralPath $RuntimeDir) {
        Remove-Item -LiteralPath $RuntimeDir -Recurse -Force
    }
}
Write-Host 'Plug-in disinstallato. Le impostazioni personali sono state conservate salvo uso di -RemoveSettings.' -ForegroundColor Green
Read-Host 'Premi Invio per chiudere'
