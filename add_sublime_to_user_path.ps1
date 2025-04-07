# Get the current user PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

# Define Sublime Text path
$sublimePath = "C:\Program Files\Sublime Text"

# Check if the path already exists in user PATH
if ($userPath -notlike "*$sublimePath*") {
    # Add Sublime Text to user PATH
    $newUserPath = $userPath + ";" + $sublimePath
    
    # Set the new PATH
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    
    Write-Host "Sublime Text has been added to your user PATH successfully."
} else {
    Write-Host "Sublime Text is already in your user PATH."
}

# Refresh the current session's PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")