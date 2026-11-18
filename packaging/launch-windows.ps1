$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Test-PythonCommand {
    param([string]$Command, [string[]]$Prefix = @())
    try {
        $output = & $Command @Prefix -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $output) { return $null }
        $parts = ([string]$output).Trim().Split('.')
        if ($parts.Count -lt 2) { return $null }
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        if ($major -eq 3 -and $minor -ge 11) {
            return [pscustomobject]@{ Command = $Command; Prefix = $Prefix; Version = "$major.$minor" }
        }
    } catch { }
    return $null
}

$Python = $null

# Prefer the Python Launcher, but do not assume that a specific minor version exists.
$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PyLauncher) {
    foreach ($Version in @('3.13', '3.12', '3.11', '3')) {
        $Python = Test-PythonCommand -Command $PyLauncher.Source -Prefix @("-$Version")
        if ($Python) { break }
    }
}

# Fall back to python.exe / python3.exe on PATH.
if (-not $Python) {
    foreach ($Name in @('python', 'python3')) {
        $Candidate = Get-Command $Name -ErrorAction SilentlyContinue
        if ($Candidate) {
            $Python = Test-PythonCommand -Command $Candidate.Source
            if ($Python) { break }
        }
    }
}

# If Python is missing, offer a user-scoped installation through winget.
if (-not $Python) {
    $Winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $Winget) {
        throw @"
Python 3.11 ou supérieur est introuvable et winget n'est pas disponible.
Installe Python depuis https://www.python.org/downloads/windows/ (cocher l'ajout au PATH),
puis relance packaging\launch-windows.ps1.
"@
    }

    Write-Host "Python 3.11+ est absent. Le projet nécessite Python pour lancer l'interface PySide6." -ForegroundColor Yellow
    $Answer = Read-Host "Installer Python 3.12 pour l'utilisateur courant avec winget ? (O/N)"
    if ($Answer -notin @('O', 'o', 'Y', 'y')) {
        throw "Installation annulée. Installe Python 3.11+ puis relance ce script."
    }

    & $Winget.Source install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "L'installation de Python via winget a échoué (code $LASTEXITCODE). Installe Python manuellement puis relance le script."
    }

    # Refresh PATH for this process; winget's user install commonly uses LocalAppData.
    $UserPython = Join-Path $env:LocalAppData 'Programs\Python\Python312\python.exe'
    if (Test-Path $UserPython) {
        $Python = Test-PythonCommand -Command $UserPython
    }
    if (-not $Python) {
        $Candidate = Get-Command python -ErrorAction SilentlyContinue
        if ($Candidate) { $Python = Test-PythonCommand -Command $Candidate.Source }
    }
    if (-not $Python) {
        throw "Python a été installé, mais PowerShell ne le détecte pas encore. Ferme cette fenêtre, ouvre-en une nouvelle et relance le script."
    }
}

Write-Host "Python détecté : $($Python.Version)" -ForegroundColor Green
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    & $Python.Command @($Python.Prefix) -m venv (Join-Path $ProjectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw "Impossible de créer l'environnement virtuel (code $LASTEXITCODE)." }
}

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Échec de la mise à jour de pip." }
& $VenvPython -m pip install -r (Join-Path $ProjectRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "Échec de l'installation des dépendances Python." }
& $VenvPython -m app.main
if ($LASTEXITCODE -ne 0) { throw "K3s Deployment Studio s'est arrêté avec le code $LASTEXITCODE." }
