param(
    [Parameter(Mandatory=$true)][string]$App,
    [Parameter(Mandatory=$true)][string]$Server,
    [ValidateRange(1,600)][int]$TimeoutSeconds = 30
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows required' }
$App = (Resolve-Path -LiteralPath $App).ProviderPath
$Server = (Resolve-Path -LiteralPath $Server).ProviderPath
foreach ($path in @($App,$Server)) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Executable missing' }
}
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('tb smoke ' + [guid]::NewGuid())
[void](New-Item -ItemType Directory -Path $fixture)
function Invoke-Probe([string]$Exe,[string]$Arguments,[string]$WorkingDirectory,[string]$Label) {
    $stdout = Join-Path $fixture ($Label + '.out')
    $stderr = Join-Path $fixture ($Label + '.err')
    $process = $null
    try {
        $process = Start-Process -FilePath $Exe -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
        if (!$process.WaitForExit($TimeoutSeconds * 1000)) {
            & "$env:SystemRoot\System32\taskkill.exe" /PID $process.Id /T /F | Out-Null
            throw "$Label timed out"
        }
        $process.Refresh()
        $exit = $process.ExitCode
        Write-Output "$Label exit=$exit"
        if ($exit -ne 0) { throw "$Label failed" }
        if (((Get-Item -LiteralPath $stdout).Length + (Get-Item -LiteralPath $stderr).Length) -eq 0) {
            throw "$Label returned no output"
        }
    } catch {
        # No raw stdout/stderr or private command paths in shared logs.
        $cause = $_.Exception
        while ($cause.InnerException) { $cause = $cause.InnerException }
        if ($cause -is [ComponentModel.Win32Exception]) {
            Write-Output "$Label winerror=$($cause.NativeErrorCode)"
        }
        throw "$Label probe failed; repeat the direct command for private diagnostics"
    } finally {
        if ($process) { $process.Dispose() }
    }
}
try {
    foreach ($entry in @(@{Path=$App;Name='app'},@{Path=$Server;Name='server'})) {
        $hash = (Get-FileHash -LiteralPath $entry.Path -Algorithm SHA256).Hash
        $length = (Get-Item -LiteralPath $entry.Path).Length
        Write-Output "$($entry.Name) sha256=$hash bytes=$length"
    }
    Invoke-Probe $App '--help' $fixture 'app-help'
    Invoke-Probe $App ('doctor --project "' + $fixture + '"') $fixture 'app-doctor'
    Invoke-Probe $Server '--version' (Split-Path -Parent $Server) 'server-version'
    Invoke-Probe $Server '--help' (Split-Path -Parent $Server) 'server-help'
    Invoke-Probe $Server '--version' $fixture 'server-unrelated-cwd'
    Write-Output 'Model-free smoke passed. No inference or clean-machine claim.'
} finally {
    foreach ($label in @('app-help','app-doctor','server-version','server-help','server-unrelated-cwd')) {
        foreach ($suffix in @('.out','.err')) {
            $file = Join-Path $fixture ($label + $suffix)
            if (Test-Path -LiteralPath $file -PathType Leaf) { Remove-Item -LiteralPath $file }
        }
    }
    # Never recurse: unexpected fixture files remain for private inspection.
    if (!(Get-ChildItem -LiteralPath $fixture -Force)) { Remove-Item -LiteralPath $fixture }
}
