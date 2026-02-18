# ================================
# EES Scheduler Task Import Script
# ================================

Write-Host "Importing EES Automated Scheduler Tasks..." -ForegroundColor Cyan

# Directory containing XML files
$TaskFolder = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Task list
$Tasks = @(
    # "RunPdfZipAndSftp.xml",
    # "RunPreOdrMailer.xml",
    "RunMidNightCleanUp.xml",
    "RunCitationDailyReport.xml",
    "RunCitationSummary.xml",
    "RunTattileUpload.xml",
    "RunTattileReject.xml",
    # "RunGeneratePdfCsv.xml",
    # "RunCitationFirstMailer.xml",
    "RunMailToLeahXbpCsv.xml",
    "RunVideoUpload.xml",
    "MonitorDiagnosticTask.xml"
)

foreach ($task in $Tasks) {

    $xmlPath = Join-Path $TaskFolder $task

    if (Test-Path $xmlPath) {
        Write-Host "Importing task: $task ..." -ForegroundColor Yellow
        
        schtasks /Create /TN ("\EES\" + [System.IO.Path]::GetFileNameWithoutExtension($task)) `
            /XML $xmlPath /F | Out-Null

        Write-Host " → Imported successfully." -ForegroundColor Green
    }
    else {
        Write-Host "ERROR: File not found -> $xmlPath" -ForegroundColor Red
    }
}

Write-Host "`nAll available tasks imported into: Task Scheduler Library → EES" -ForegroundColor Cyan
