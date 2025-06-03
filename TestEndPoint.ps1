# Test queries for SharePoint Search API

param(
    [Parameter(Mandatory=$false)]
    [int]$targetUrlNumber = 0,

    [Parameter(Mandatory=$false)]
    [string]$targetUrl = "",

    [Parameter(Mandatory=$false)]
    [ValidateRange(1,2)]
    [int]$displayMode = 0
)

Clear-Host

# Read local URL from tasks.json
$tasksJsonPath = Join-Path $PSScriptRoot ".vscode\tasks.json"
$localUrl = "http://localhost:5000" # Default value
if (Test-Path $tasksJsonPath) {
    $tasksJson = Get-Content $tasksJsonPath | ConvertFrom-Json
    # Find the start command in tasks.json
    $startCommand = $tasksJson.tasks | Where-Object { $_.args -match 'start http' } | Select-Object -First 1
    if ($startCommand) {
        $localUrl = [regex]::Match($startCommand.args[1], 'start (.+)').Groups[1].Value
    }
}

# Read cloud URL from .env
$envPath = Join-Path $PSScriptRoot ".env"
$cloudUrl = "" # Default empty
if (Test-Path $envPath) {
    # Read and parse .env file
    $envContent = Get-Content $envPath | Where-Object { $_ -match '^AZURE_APP_NAME=(.+)$' }
    if ($envContent) {
        $appName = $matches[1].Trim()
        $cloudUrl = "https://$appName.azurewebsites.net"
    }
}

# Available target URLs
$targetUrls = @(
    @{ Name = "Local"; Url = $localUrl },
    @{ Name = "Cloud"; Url = $cloudUrl }
)

# Handle URL selection
$baseUrl = if ($targetUrl) {
    $targetUrl
    # set default display mode if not specified
    if ($displayMode -eq 0) { $displayMode = 1 }
} elseif ($targetUrlNumber -gt 0 -and $targetUrlNumber -le $targetUrls.Count) {
    $targetUrls[$targetUrlNumber - 1].Url
} else {
    # Display menu and get user selection
    Write-Host "`nSelect target environment:"
    1..$targetUrls.Count | ForEach-Object {
        $index = $_ - 1
        Write-Host "$_) $($targetUrls[$index].Name) - $($targetUrls[$index].Url)"
    }

    do {
        $selection = Read-Host "`nEnter selection (1-$($targetUrls.Count))"
        $index = [int]$selection - 1
    } while ($index -lt 0 -or $index -ge $targetUrls.Count)

    $targetUrls[$index].Url
}

# Handle display mode selection
if ($displayMode -eq 0) {
    Write-Host "`nSelect display mode:"
    Write-Host "1) Display test results only"
    Write-Host "2) Display full JSON requests and responses"

    do {
        $displayMode = Read-Host "`nEnter selection (1-2)"
    } while ([int]$displayMode -lt 1 -or [int]$displayMode -gt 2)
}

# Initialize test case counter and expected response type
$testCaseNumber = 1
$expectedMimeType = "application/json"

# Function to test endpoint with both GET and POST methods
function Invoke-EndpointTest {
    param (
        [string]$endpoint,
        [string]$method = "GET",
        [object]$body = $null
    )
    
    $uri = "$baseUrl$endpoint"
    $status = $null
    $mimeType = $null
    $jsonData = $null
    
    try {
        $params = @{
            Uri = $uri
            Method = $method
        }
        
        if ($method -eq "POST" -and $body) {
            $params.Body = $body | ConvertTo-Json -Depth 10
            $params.ContentType = "application/json"
        }
        
        $webRequest = Invoke-WebRequest @params
        $status = $webRequest.StatusCode
        $mimeType = $webRequest.Headers['Content-Type']
        $jsonData = $webRequest.Content | ConvertFrom-Json
    }
    catch {
        if ($_.Exception.Response) {
            $status = $_.Exception.Response.StatusCode.value__
            if ($_.Exception.Response.Headers) {
                $mimeType = $_.Exception.Response.Headers['Content-Type']
            }
        }
        
        # Handle connection errors (no response)
        if (-not $status) {
            $status = 503  # Service Unavailable
        }
        
        try {
            if ($_.ErrorDetails.Message) {
                $jsonData = $_.ErrorDetails.Message | ConvertFrom-Json
            }
        } catch {
            $jsonData = $null
        }
    }
    
    # Store the actual status code before displaying debug info
    $actualStatus = $status
    
    # Store response data before any output
    $responseData = @{
        Status = $status
        MimeType = $mimeType
        JsonData = $jsonData
    }
    
    # First return the data for test validation
    $result = @($responseData.Status, $responseData.MimeType, $responseData.JsonData)
    
    # Then display debug info if needed
    if ($displayMode -eq 2) {

        Write-Host "`nTest Details:"
        Write-Host "URL: $method $uri"
        Write-Host "Status: $($responseData.Status)"
        Write-Host "MIME: $($responseData.MimeType)"
        Write-Host "Response:"
        Write-Host "----------------- START RESPONSE -----------------------"
        if ($responseData.JsonData) {
            Write-Host ($responseData.JsonData | ConvertTo-Json -Depth 10)
        }
        Write-Host "----------------- END RESPONSE -------------------------"
    }
    
    return $result
}

# ======================================================================================================================
# Testing /alive endpoint
# ======================================================================================================================
Write-Host "`nTest Case $($testCaseNumber): GET /alive should return 200 - Service is alive"
$testCaseNumber++
$response = Invoke-EndpointTest -endpoint "/alive" -method "GET"
$status = $response[0]

if ($status -eq 200) {
    Write-Host "  SUCCESS! Got expected status code: 200" -ForegroundColor Green
} else {
    Write-Host "  ERROR! Expected status 200 but got $status" -ForegroundColor White -BackgroundColor Red
}

# ======================================================================================================================
# Testing /describe endpoint
# ======================================================================================================================
Write-Host "`nTest Case $($testCaseNumber): GET /describe should return 405 - HTTP GET not supported"
$testCaseNumber++
$response = Invoke-EndpointTest -endpoint "/describe" -method "GET"
$status = $response[0]

if ($status -eq 405) {
    Write-Host "  SUCCESS! Got expected status code: 405" -ForegroundColor Green
} else {
    Write-Host "  ERROR! Expected status 405 but got $status" -ForegroundColor White -BackgroundColor Red
}

Write-Host "`nTest Case $($testCaseNumber): POST /describe with empty payload should return 200 with valid response"
$testCaseNumber++
$response = Invoke-EndpointTest -endpoint "/describe" -method "POST" -body @{}
$status = $response[0]
$mime = if (-not $response[1]) { "[Empty]" } else { $response[1] }
$json = $response[2]

$valid = $true
if ($status -ne 200) {
    Write-Host "  ERROR! Expected status 200 but got $status" -ForegroundColor White -BackgroundColor Red
    $valid = $false
}

if ($mime -ne $expectedMimeType) {
    Write-Host "  ERROR! Expected MIME type '$expectedMimeType' but got '$mime'" -ForegroundColor White -BackgroundColor Red
    $valid = $false
}

if (-not $json.data -or -not $json.data.description) {
    Write-Host "  FAIL: Missing 'data.description' field" -ForegroundColor White -BackgroundColor Red
    $valid = $false
}
if (-not $json.data -or -not $json.data.domains -or $json.data.domains.Count -eq 0) {
    Write-Host "  FAIL: 'data.domains' array is empty" -ForegroundColor White -BackgroundColor Red
    $valid = $false
}
elseif (-not $json.data.domains[0].name -or -not $json.data.domains[0].description) {
    Write-Host "  FAIL: First domain missing name or description" -ForegroundColor White -BackgroundColor Red
    $valid = $false
}

if ($valid) {
    Write-Host "  PASS: Response contains all required fields" -ForegroundColor Green
}

# ======================================================================================================================
# Testing /query endpoint"
# ======================================================================================================================


Write-Host "`nTest Case $($testCaseNumber): GET /query should return 405 - HTTP GET not supported"
$testCaseNumber++
$response = Invoke-EndpointTest -endpoint "/query" -method "GET"
$status = $response[0]

if ($status -eq 405) {
    Write-Host "  SUCCESS! Got expected status code: 405" -ForegroundColor Green
} else {
    Write-Host "  ERROR! Expected status 405 but got $status" -ForegroundColor white -backgroundColor Red
}

Write-Host "`nTest Case $($testCaseNumber): POST /query with 'lorem ipsum' should return correct response from demodata.py"
$testCaseNumber++
$body = @{ data = @{ query = "lorem ipsum"; args = @{} }; auth = @{ oid = ""; groups = @() } }

$body.data.query = "lorem ipsum"
$response = Invoke-EndpointTest -endpoint "/query" -method "POST" -body $body
$status = $response[0]
$mime = if (-not $response[1]) { "[Empty]" } else { $response[1] }
$json = $response[2]

if ($status -ne 200) {
    Write-Host "  ERROR! Expected status 200 but got $status" -ForegroundColor White -BackgroundColor Red

} elseif ($mime -ne $expectedMimeType) {
    Write-Host "  ERROR! Expected MIME type '$expectedMimeType' but got '$mime'" -ForegroundColor White -BackgroundColor Red
} elseif (-not $json.data.answer -or -not $json.data.answer.StartsWith("Lorem ipsum dolor sit amet")) {
    Write-Host "  FAIL: Response does not match expected lorem ipsum answer from demodata.py" -ForegroundColor White -BackgroundColor Red
} else {
    Write-Host "  PASS: Response matches expected lorem ipsum answer" -ForegroundColor Green
}

Write-Host "`nTest Case $($testCaseNumber): POST /query with empty query should return empty response JSON"
$testCaseNumber++
$body.data.query = ""
$response = Invoke-EndpointTest -endpoint "/query" -method "POST" -body $body
$status = $response[0]
$mime = if (-not $response[1]) { "[Empty]" } else { $response[1] }
$json = $response[2]

if ($status -ne 200) {
    Write-Host "  ERROR! Expected status 200 but got $status" -ForegroundColor White -BackgroundColor Red

} elseif ($mime -ne $expectedMimeType) {
    Write-Host "  ERROR! Expected MIME type '$expectedMimeType' but got '$mime'" -ForegroundColor White -BackgroundColor Red
} elseif ($json.data.answer) {
    Write-Host "  FAIL: Empty query should return empty response" -ForegroundColor White -BackgroundColor Red
} else {
    Write-Host "  PASS: Empty query returns empty response" -ForegroundColor Green
}

Write-Host "`nTest Case $($testCaseNumber): POST /query with empty payload should return 400 - Bad Request"
$testCaseNumber++
$response = Invoke-EndpointTest -endpoint "/query" -method "POST" -body @{}
$status = $response[0]

if ($status -eq 400) {
    Write-Host "  SUCCESS! Got expected status code: 400" -ForegroundColor Green
} else {
    Write-Host "  ERROR! Expected status 400 but got $status" -ForegroundColor White -BackgroundColor Red
}
