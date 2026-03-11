# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check for Node.js
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js (npm) is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

$backendDir = Join-Path $PSScriptRoot "backend"
$frontendDir = Join-Path $PSScriptRoot "frontend"

# --- Backend Setup ---
Write-Host "Setting up Backend..." -ForegroundColor Cyan
Push-Location $backendDir

# Create venv if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv venv
}

# Install requirements
Write-Host "Installing backend requirements..."
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Start Backend
Write-Host "Starting Backend Server..." -ForegroundColor Green
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn main:app --reload --host 0.0.0.0 --port 8000" -WorkingDirectory $backendDir -WindowStyle Normal

Pop-Location

# --- Frontend Setup ---
Write-Host "Setting up Frontend..." -ForegroundColor Cyan
Push-Location $frontendDir

# Install dependencies
Write-Host "Installing frontend dependencies..."
npm install

# Start Frontend
Write-Host "Starting Frontend Server..." -ForegroundColor Green
Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory $frontendDir -WindowStyle Normal

Pop-Location

Write-Host "Project is running!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
