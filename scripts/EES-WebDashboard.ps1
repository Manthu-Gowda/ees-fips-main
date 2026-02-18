# ====================================================
# EES HTML AUTO-REFRESH DASHBOARD
# ====================================================

$OutputFile = "EES_Task_Dashboard.html"
$TaskRoot = "EES"

$EESTasks = @(
    # "RunPdfZipAndSftp",
    # "RunPreOdrMailer",
    "RunMidNightCleanUp",
    "RunCitationDailyReport",
    "RunCitationSummary",
    "RunTattileUpload",
    "RunTattileReject",
    # "RunGeneratePdfCsv",
    # "RunCitationFirstMailer",
    "RunMailToLeahXbpCsv.xml",
    "RunVideoUpload.xml"
)

$Rows = ""

foreach ($Task in $EESTasks) {

    $TaskObj = Get-ScheduledTask -TaskName $Task -TaskPath "\EES\" -ErrorAction SilentlyContinue
    $Info = Get-ScheduledTaskInfo -TaskName $Task -TaskPath "\EES\" -ErrorAction SilentlyContinue

    if (!$TaskObj) {
        $Rows += "<tr><td>$Task</td><td style='color:red;'>Missing</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
        continue
    }

    # Status color
    switch ($TaskObj.State) {
        "Ready"    { $StateColor = "green" }
        "Running"  { $StateColor = "blue" }
        "Disabled" { $StateColor = "red" }
        default    { $StateColor = "orange" }
    }

    # Result color
    switch ($Info.LastTaskResult) {
        0       { $Result = "Success"; $ResultColor = "green" }
        267009  { $Result = "Running"; $ResultColor = "blue" }
        default { $Result = "Error ($($Info.LastTaskResult))"; $ResultColor = "red" }
    }

    $Trigger = $TaskObj.Triggers[0].StartBoundary

    $Rows += "
        <tr>
            <td>$Task</td>
            <td style='color:$StateColor;'>$($TaskObj.State)</td>
            <td>$($Info.LastRunTime)</td>
            <td>$($Info.NextRunTime)</td>
            <td style='color:$ResultColor;'>$Result</td>
            <td>$Trigger</td>
        </tr>
    "
}

# HTML Template
$HTML = @"
<html>
<head>
    <meta http-equiv='refresh' content='10'>
    <title>EES Task Dashboard</title>
    <style>
        body { font-family: Arial; background:#f3f3f3; }
        table { width:100%; border-collapse: collapse; background:white; }
        th, td { border:1px solid #ccc; padding:10px; text-align:left; }
        th { background:#222; color:white; }
        h2 { color:#0b5394; }
    </style>
</head>
<body>
    <h2>EES Scheduled Task Dashboard (Auto-Refresh)</h2>
    <p>Updated: $(Get-Date)</p>
    <table>
        <tr>
            <th>Task Name</th>
            <th>Status</th>
            <th>Last Run</th>
            <th>Next Run</th>
            <th>Last Result</th>
            <th>Trigger</th>
        </tr>
        $Rows
    </table>
</body>
</html>
"@

$HTML | Out-File -FilePath $OutputFile -Encoding UTF8

Write-Host "Dashboard generated: $OutputFile" -ForegroundColor Green

