# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "You need to run this script as an Administrator. Right-click PowerShell and select 'Run as Administrator'."
    pause
    exit
}

# Get the current system PATH
$currentPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')

# Add Sublime Text to the PATH (only if it's not already there)
$sublimePath = "C:\Program Files\Sublime Text"

# Check if Sublime Text directory exists
if (-NOT (Test-Path $sublimePath)) {
    Write-Warning "Sublime Text directory not found at $sublimePath"
    pause
    exit
}

if ($currentPath -notlike "*$sublimePath*") {
    $newPath = $currentPath + ";$sublimePath"
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'Machine')
    Write-Host "Sublime Text has been successfully added to the system PATH"
} else {
    Write-Host "Sublime Text is already in the system PATH"
}

Write-Host "`nPress any key to exit..."
pause 