# Task Timing Verification Table
| **#** | **Task Name**                  | **Python Function**           | **Run Time (24 hr)** | **Description**                        |
| ----- | ------------------------------ | ----------------------------- | -------------------- | -------------------------------------- |
| 1     | **RunPdfZipAndSftp.xml**       | `run_pdf_zip_and_sftp()`      | **04:30**            | Daily PDF ZIP + SFTP distribution      |
| 2     | **RunPreOdrMailer.xml**        | `run_pre_odr_mailer()`        | **00:51**            | First mailer PRE-ODR PDF distribution  |
| 3     | **RunMidNightCleanUp.xml**     | `run_midnight_cleanup()`      | **23:50**            | Midnight cleanup (adj & sup removal)   |
| 4     | **RunCitationDailyReport.xml** | `run_daily_report()`          | **04:01**            | Daily citation report generation       |
| 5     | **RunCitationSummary.xml**     | `run_citation_summary()`      | **08:01**            | Citation summary processing            |
| 6     | **RunTattileUpload.xml**       | `run_tattile_upload()`        | **01:30**            | Tattile JSON upload                    |
| 7     | **RunTattileReject.xml**       | `run_tattile_reject()`        | **02:01**            | Tattile reject record upload           |
| 8     | **RunGeneratePdfCsv.xml**      | `run_generate_pdf_csv()`      | **02:30**            | Midnight CSV + PDF generation          |
| 9     | **RunCitationFirstMailer.xml** | `run_citation_first_mailer()` | **07:10**            | First mailer citation unpaid reporting |
| 10     | **RunMailToLeahXbpCsv.xml** | `run_mail_to_leah_xbp_csv()` | **23:40**            | Share mail to Leah CSV and Payment CSV upload reporting |
| 11     | **RunVideoUpload.xml** | `run_video_upload()` | **23:40**            | Upload all Docked video to server reporting |