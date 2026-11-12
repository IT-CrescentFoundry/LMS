<#
.SYNOPSIS
    Runs every automated quality check for the Crescent Foundry LMS.

.DESCRIPTION
    Backend:  ruff lint, ruff format check, mypy (strict), pytest
    Frontend: TypeScript check, ESLint, Vitest, production build

    Stops at the first failing step and exits with a non-zero code.
    Does not connect to any database and does not modify source files.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\check.ps1
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'LMS_Backend'
$frontend = Join-Path $root 'LMS_Frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "Backend virtual environment not found at $python. See README.md (Backend setup)."
}
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Error "Frontend dependencies not installed. Run 'npm ci' in LMS_Frontend."
}

function Invoke-Step {
    param([string]$Name, [string]$WorkingDirectory, [scriptblock]$Command)
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    Push-Location $WorkingDirectory
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED: $Name (exit code $LASTEXITCODE)" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step 'Backend: ruff check' $backend { & $python -m ruff check . }
Invoke-Step 'Backend: ruff format --check' $backend { & $python -m ruff format --check . }
Invoke-Step 'Backend: mypy (strict)' $backend { & $python -m mypy }
Invoke-Step 'Backend: pytest' $backend { & $python -m pytest }

Invoke-Step 'Frontend: TypeScript' $frontend { npm run typecheck }
Invoke-Step 'Frontend: ESLint' $frontend { npm run lint }
Invoke-Step 'Frontend: Vitest' $frontend { npm test }
Invoke-Step 'Frontend: production build' $frontend { npm run build }

Write-Host ""
Write-Host "All checks passed." -ForegroundColor Green
