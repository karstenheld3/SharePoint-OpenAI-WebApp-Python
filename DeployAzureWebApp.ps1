# Reads an .env file and returns a hashtable of key-value pairs
function Read-EnvFile {
  param([Parameter(Mandatory=$true)] [string]$Path)
  $envVars = @{}  
  if (!(Test-Path $Path)) { throw "File '$($Path)' not found."  }
  Get-Content $Path | ForEach-Object {
    # ([^=]+)=([^#]*) captures key-value pairs separated by '=' in group 1 and 2
    # (?:#.*)?$ optionally matches comments after '#' in group 3
    if ($_ -match '^(?!#)([^=]+)=([^#]*)(?:#.*)?$') {
      $key = $matches[1].Trim(); $value = $matches[2].Trim()
      $envVars[$key] = $value
    }
  }
  return $envVars
}

Clear-Host

$deployZipFilename = "deploy.zip"
$envPath = Join-Path $PSScriptRoot  ".env"
if (!(Test-Path $envPath)) { throw "File '$($envPath)' not found."  }
$config = Read-EnvFile -Path ($envPath)

$ignoreFilesAndFoldersForDeployment = @('.git','*.bat', '*.ps1', $deployZipFilename, '.vscode', '__pycache__', '*.md', '.env', 'LICENSE', '.gitignore')

# https://learn.microsoft.com/en-us/azure/app-service/configure-language-python
# "BUILD_FLAGS=UseExpressBuild" -> will use fast deployment
$webAppSettings = @("SCM_DO_BUILD_DURING_DEPLOYMENT=1", "ENABLE_ORYX_BUILD=false", "BUILD_FLAGS=UseExpressBuild", "PYTHON_ENABLE_GUNICORN=true")
# Exclude deployment variables from .env file to NOT being set in Azure Web App
$excludeVarsFromEnvFile = @( "AZURE_RESOURCE_GROUP", "AZURE_LOCATION", "AZURE_APP_NAME", "AZURE_PYTHON_VERSION", "AZURE_APP_SERVICE_PLAN")
$webAppStartupCommand = "gunicorn --bind=0.0.0.0:8000 app:app"

### Overwrite .env variables if needed
# $config.AZURE_OPENAI_ENDPOINT = ""
# $config.AZURE_OPENAI_API_KEY = ""
# $config.AZURE_TENANT_ID = ""
# $config.AZURE_CLIENT_ID = ""
# $config.AZURE_CLIENT_SECRET = ""

# === Check for required tools ===
# Check Az PowerShell module
if (-not (Get-Module -Name Az -ListAvailable)) {
  Write-Host "Installing Az module..."
  Install-Module -Name Az -Scope CurrentUser -Force -AllowClobber
}

# Make sure Azure CLI is installed
try { $null = az --version }
catch {
  Write-Host "Installing Azure CLI..."
  $installerUrl = "https://aka.ms/installazurecliwindows"
  $installerPath = "$env:TEMP\AzureCLI.msi"  
  # Download the installer
  Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
  # Install Azure CLI
  Start-Process msiexec.exe -Wait -ArgumentList "/I $installerPath /quiet"
  # Clean up
  Remove-Item $installerPath
  # Verify installation
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
  try { $null = az --version; Write-Host "Azure CLI installation successful"}
  catch {
    Write-Error "Azure CLI installation failed. Please install manually from: $installerUrl" -ForegroundColor White -BackgroundColor Red
    exit 1
  }
}

# === Login to Azure ===
Write-Host "Connecting to Azure..."
# Clear any existing contexts first
Clear-AzContext -Force

# Connect with both tenant and subscription in one command
$errorMessage = "ERROR: Failed to connect to Azure subscription '$($config.AZURE_SUBSCRIPTION_ID)'"
try {$subscription = Connect-AzAccount -Tenant "$($config.AZURE_TENANT_ID)" -Subscription "$($config.AZURE_SUBSCRIPTION_ID)"}
catch {throw "$($_.Exception.Message)"}
if ($null -eq $subscription) { throw $errorMessage }

# Set the Azure CLI subscription
az account set --subscription "$($config.AZURE_SUBSCRIPTION_ID)"

Set-Location $PSScriptRoot

# Check if web app exists
Write-Host "Checking if web app '$($config.AZURE_APP_NAME)' exists..."
$errorMessage = "ERROR: Web app not found '$($config.AZURE_APP_NAME)'"
try { $retVal = az webapp show --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP }
catch {throw "$($_.Exception.Message)"}
if ($null -eq $retVal) { throw $errorMessage }

Write-Host "Access the web app here:"
Write-Host "   https://$($config.AZURE_APP_NAME).azurewebsites.net" -ForegroundColor Cyan
Write-Host "Access the deployment tools and docker logs:"
Write-Host "   https://$($config.AZURE_APP_NAME).scm.azurewebsites.net" -ForegroundColor Cyan
Write-Host "   https://$($config.AZURE_APP_NAME).scm.azurewebsites.net/deploymentlogs/" -ForegroundColor Cyan
Write-Host "   https://$($config.AZURE_APP_NAME).scm.azurewebsites.net/api/logs/docker/zip" -ForegroundColor Cyan

# Stop the script if any command fails
$ErrorActionPreference = 'Stop'

# Configure the web app settings and environment variables
Write-Host "Configuring web app settings and environment variables..."

$envVarsToSet = $webAppSettings.Clone()
# Set environment variables from .env file
Write-Host "Getting environment variables from .env file:"
foreach ($key in $config.Keys | Sort-Object) {
    if ($key -notin $excludeVarsFromEnvFile) {
        $envVarsToSet += "$key=$($config[$key])"
    }
}

if ($envVarsToSet.Count -gt 0) {
    Write-Host "Setting Azure Web App environment variables..."    
    # Set the app settings
    $retVal = az webapp config appsettings set `
        --name $config.AZURE_APP_NAME `
        --resource-group $config.AZURE_RESOURCE_GROUP `
        --settings $envVarsToSet
        
    # Verify the settings were set
    Write-Host "Verifying environment variables in Azure Web App:"
    $currentSettings = az webapp config appsettings list `
        --name $config.AZURE_APP_NAME `
        --resource-group $config.AZURE_RESOURCE_GROUP | ConvertFrom-Json 
        
    # Convert $envVarsToSet into a hashtable for easier lookup
    $expectedVars = @{}
    $envVarsToSet | ForEach-Object {
        $name, $value = $_ -split '='
        $expectedVars[$name] = $value
    }

    foreach ($name in $expectedVars.Keys) {
        $setting = $currentSettings | Where-Object { $_.name -eq $name }
        if ($setting) {
            if ($setting.value -eq $expectedVars[$name]) {
                Write-Host "  ✓ $name = $($setting.value)" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ $name has different value. Expected: '$($expectedVars[$name])', Actual: '$($setting.value)'" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ✗ $name is missing from Azure" -ForegroundColor Red
        }
    }
}

Write-Host "Setting startup command to '$($webAppStartupCommand)'..."
$retVal = az webapp config set --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP --startup-file $webAppStartupCommand

Write-Host "Configuring logging..."
$retVal = az webapp log config --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP --application-logging filesystem

# Delete old zip file if it exists
If (Test-Path "$PSScriptRoot\$deployZipFilename") { Remove-Item "$PSScriptRoot\$deployZipFilename" -Force }

# Deploy the application using zip deploy for more reliable deployment
Write-Host "Creating deployment package..."
# Create deployment package excluding unnecessary files
$sourcePath = Join-Path $PSScriptRoot "src"
$zipPath = Join-Path $PSScriptRoot $deployZipFilename
Get-ChildItem -Path $sourcePath -Exclude $ignoreFilesAndFoldersForDeployment | Compress-Archive -DestinationPath $zipPath -Force

Write-Host "Deploying application..."
$retVal = az webapp deploy --resource-group $config.AZURE_RESOURCE_GROUP --name $config.AZURE_APP_NAME --src-path $zipPath --type zip

Write-Host "Deleting '$zipPath'..."
if (Test-Path "$PSScriptRoot\$deployZipFilename") { Remove-Item "$PSScriptRoot\$deployZipFilename" -Force }

# https://learn.microsoft.com/en-us/cli/azure/webapp/log?view=azure-cli-latest
# az webapp log tail --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP
