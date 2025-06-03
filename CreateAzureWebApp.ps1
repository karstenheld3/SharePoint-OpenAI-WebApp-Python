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

$envPath = Join-Path $PSScriptRoot  ".env"
if (!(Test-Path $envPath)) { throw "File '$($envPath)' not found."  }
$config = Read-EnvFile -Path ($envPath)

### Overwrite .env variables if needed
# $config.AZURE_TENANT_ID = ""
# $config.AZURE_SUBSCRIPTION_ID = ""
# $config.AZURE_RESOURCE_GROUP = ""
# $config.AZURE_AZURE_LOCATION = ""
# $config.AZURE_APP_NAME = ""
# $config.AZURE_PYTHON_VERSION = ""
# $config.AZURE_APP_SERVICE_PLAN = ""

### Define default values
$config.OS = "Linux"
$config.AZURE_LOCATION = "swedencentral"
$config.AZURE_APP_SERVICE_PLAN_TIER = "Basic"
$config.AZURE_APP_SERVICE_PLAN_SIZE = "Small"
$config.AZURE_APP_SERVICE_PLAN_WORKER_COUNT = 1

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
$subscription = Connect-AzAccount -Tenant "$($config.AZURE_TENANT_ID)" -Subscription "$($config.AZURE_SUBSCRIPTION_ID)"
if ($null -eq $subscription) { throw "ERROR: Failed to connect to Azure subscription: '$($config.AZURE_SUBSCRIPTION_ID)'" }

# Set the Azure CLI subscription
az account set --subscription "$($config.AZURE_SUBSCRIPTION_ID)"


# === Create Resource Group ===
$rg = Get-AzResourceGroup -Name $config.AZURE_RESOURCE_GROUP -ErrorAction SilentlyContinue
if (-not $rg) {
  Write-Host "Creating resource group '$($config.AZURE_RESOURCE_GROUP)'..."
  New-AzResourceGroup -Name $config.AZURE_RESOURCE_GROUP -Location $config.AZURE_LOCATION
}

# === Create App Service Plan ===
$appServicePlan = Get-AzAppServicePlan -ResourceGroupName $config.AZURE_RESOURCE_GROUP -Name $config.AZURE_APP_SERVICE_PLAN -ErrorAction SilentlyContinue
if (-not $appServicePlan) {
  Write-Host "Creating app service plan '$($config.AZURE_APP_SERVICE_PLAN)'..."
  if ($config.OS -eq "Linux") {
    $appServicePlan = New-AzAppServicePlan -Name $config.AZURE_APP_SERVICE_PLAN `
      -ResourceGroupName $config.AZURE_RESOURCE_GROUP `
      -Location $config.AZURE_LOCATION `
      -Tier $config.AZURE_APP_SERVICE_PLAN_TIER `
      -NumberofWorkers $config.AZURE_APP_SERVICE_PLAN_WORKER_COUNT `
      -WorkerSize $config.AZURE_APP_SERVICE_PLAN_SIZE `
      -Linux
  } else {
    $appServicePlan = New-AzAppServicePlan -Name $config.AZURE_APP_SERVICE_PLAN `
      -ResourceGroupName $config.AZURE_RESOURCE_GROUP `
      -Location $config.AZURE_LOCATION `
      -Tier $config.AZURE_APP_SERVICE_PLAN_TIER `
      -NumberofWorkers $config.AZURE_APP_SERVICE_PLAN_WORKER_COUNT `
      -WorkerSize $config.AZURE_APP_SERVICE_PLAN_SIZE
  }
  if (-not $appServicePlan){
    Write-Host "Error creating app service plan '$($config.AZURE_APP_SERVICE_PLAN)'!" -ForegroundColor White -BackgroundColor red; exit 1
  } else {
    Write-Host "Created new app service plan ID = '$($appServicePlan.Id)'."
  }
} else {
  Write-Host "Using existing app service plan '$($config.AZURE_APP_SERVICE_PLAN)'."
}

# === Create/Update Web App ===
$webApp = Get-AzWebApp -ResourceGroupName $config.AZURE_RESOURCE_GROUP -Name $config.AZURE_APP_NAME -ErrorAction SilentlyContinue
if (-not $webApp) {
  Write-Host "Creating web app '$($config.AZURE_APP_NAME)'..."

  $webApp = New-AzWebApp -Name $config.AZURE_APP_NAME `
    -ResourceGroupName $config.AZURE_RESOURCE_GROUP `
    -Location $config.AZURE_LOCATION `
    -AppServicePlan $config.AZURE_APP_SERVICE_PLAN
    if (-not $webApp){
      Write-Host "Error creating web app '$($config.AZURE_APP_NAME)'!" -ForegroundColor White -BackgroundColor red; exit 1
    } else {
      Write-Host "Created new web app ID = '$($webApp.Id)'."
    }
  } else {
  Write-Host "Using existing web app '$($config.AZURE_APP_NAME)'"
}  

# === Configure App Settings and Runtime ===

# If you see this error in the console, it's OK. That's just the AZ CLI distribution of Python, not yours.
# D:\a\_work\1\s\build_scripts\windows\artifacts\cli\Lib\site-packages\cryptography/hazmat/backends/openssl/backend.py:8: UserWarning: You are using cryptography on a 32-bit Python on a 64-bit Windows Operating System. Cryptography will be significantly faster if you switch to using a 64-bit Python.
if ($config.OS -eq "Linux") {
  # For Linux, configure via az cli
  $linuxFxVersion = 'PYTHON|' + $config.AZURE_PYTHON_VERSION
  $appConfig = az webapp config set --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP --linux-fx-version "`"$linuxFxVersion`""
} else {
  # For Windows, configure via az cli
  $appConfig = az webapp config set --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP --python-version $config.AZURE_PYTHON_VERSION
  
  # Configure basic settings via PowerShell
  $appSettings = Set-AzWebApp -Name $config.AZURE_APP_NAME `
    -ResourceGroupName $config.AZURE_RESOURCE_GROUP `
    -WebSocketsEnabled $true `
    -PhpVersion "OFF" `
    -NetFrameworkVersion "v6.0"
}

Write-Host "Waiting for startup command to apply..."
Start-Sleep -Seconds 10

Write-Host "Configuring logging..."
$retVal = az webapp log config --name $config.AZURE_APP_NAME --resource-group $config.AZURE_RESOURCE_GROUP --application-logging filesystem


# === Output Results ===
$webAppUrl = "https://$($config.AZURE_APP_NAME).azurewebsites.net"
Write-Host "`nDeployment completed successfully!"
Write-Host "Web App URL: $webAppUrl"
Write-Host "`nTo deploy your code:"
Write-Host "1. Open an Administrator PowerShell window"
Write-Host "2. Navigate to your project directory:"
Write-Host "   cd $PSScriptRoot"
Write-Host "3. Run the deployment command:"
Write-Host "   az webapp up --name $($config.AZURE_APP_NAME) --resource-group $($config.AZURE_RESOURCE_GROUP) --runtime 'PYTHON:$($config.AZURE_PYTHON_VERSION)'"
Write-Host "4. Access the deployment tools and docker logs:"
Write-Host "   https://$($config.AZURE_APP_NAME).scm.azurewebsites.net" -ForegroundColor Cyan
Write-Host "   https://$($config.AZURE_APP_NAME).scm.azurewebsites.net/api/logs/docker/zip" -ForegroundColor Cyan
