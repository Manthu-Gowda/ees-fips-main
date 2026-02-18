import os
import pdfkit
from decouple import config as ENV_CONFIG
from django.template.loader import get_template
from PyPDF2 import PdfReader
from ees.utils import upload_to_s3

template = get_template("pdf_final.html")
template_maryland = get_template("maryland-pdf.html")
template_first_mailer = get_template("pre_odr_mailer_notice_pdf.html")
template_second_mailer = get_template("pre_odr_second_mailer_notice_pdf.html")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
options = {"page-size": "Letter"}
template_reminder_hud_c = get_template("reminder-mail-hud-c.html")
template_kersey = get_template("kersey-pdf.html")
template_hudson = get_template("hudson-pdf.html")
template_walsenburg = get_template("wals-pdf.html")
template_fairplay = get_template("fairplay-pdf.html")

BASE_DIR = ENV_CONFIG("BASE_DIR")
TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
TEMP_PRE_ODR_FIRST_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_SECOND_MAILER_PDFS")
TEMP_REMINDER_PDF_DIR = ENV_CONFIG("TEMP_REMINDER_PDF_DIR")
TEMP_REMINDER_PDF_ZIPPED_DIR = ENV_CONFIG("TEMP_REMINDER_PDF_ZIPPED_DIR")

def is_valid_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            reader.pages[0]
        return True
    except Exception as e:
        return False

def create_pdf(filename, data, station_name):
    if station_name in ['FED-M']:
        html = template_maryland.render(data)
    elif station_name in ['KRSY-C']:
        html = template_kersey.render(data)
    elif station_name in ['HUD-C']:
        html = template_hudson.render(data)
    elif station_name in ['WALS']:
        html = template_walsenburg.render(data)
    elif station_name in ['FPLY-C']:
        html = template_fairplay.render(data)
    else:
        html = template.render(data)
    # html = template.render(data)
    # location = BASE_DIR + "/media/" + filename
    location = os.path.join(BASE_DIR, "media", filename)
    pdfkit.from_string(html, location, configuration=config, options=options)

    with open(location, "rb") as pdf_file:
        upload_to_s3(pdf_file, filename, "pdfs")
        os.remove(location)


def save_pdf(filename, station_name, data,date_type):
    
    if station_name in ['FED-M']:
        html = template_maryland.render(data)
    elif station_name in ['KRSY-C']:
        html = template_kersey.render(data)
    elif station_name in ['HUD-C']:
        html = template_hudson.render(data)
    elif station_name in ['WALS']:
        html = template_walsenburg.render(data)
    elif station_name in ['FPLY-C']:
        html = template_fairplay.render(data) 
    else:
        html = template.render(data)
    
    # pdf_path = TEMP_PDF_DIR + f"/{station_name}/"
    if date_type == 1:
        pdf_path = os.path.join(TEMP_PDF_DIR, station_name, "Original")
    else:
        pdf_path = os.path.join(TEMP_PDF_DIR, station_name, "Edited")
    save_to = os.path.join(pdf_path, filename)

    if not os.path.exists(pdf_path):
        os.makedirs(pdf_path)

    pdfkit.from_string(html, save_to, configuration=config, options=options)

    if os.path.exists(save_to) and is_valid_pdf(save_to):
        return True
    else:
        return False

def save_pdf_manual(filename, station_name, data):
    if station_name in ['FED-M']:
        html = template_maryland.render(data)
    elif station_name in ['KRSY-C']:
        html = template_kersey.render(data)
    elif station_name in ['HUD-C']:
        html = template_hudson.render(data)
    else:
        html = template.render(data)
    location = "/Users/EM/Documents/manual_pdfs"
    pdf_path = os.path.join(location, station_name)
    save_to = os.path.join(pdf_path, filename)

    if not os.path.exists(pdf_path):
        os.makedirs(pdf_path)

    pdfkit.from_string(html, save_to, configuration=config, options=options)

def manual_pdf(location, filename, data):
    html = template.render(data)
    loc = location + filename
    pdfkit.from_string(html, loc, configuration=config, options=options)

def create_pre_odr_mailer_notice_pdf(filename, context):
    """
    Generates the first mailer notice PDF with data from Citation and UnpaidCitation models.
    Ensures the directory exists before saving the PDF.
    """
    try:
        # Render the HTML template with combined context data
        print("Creating")
        html = template_first_mailer.render(context) if "first-mailer" in filename else template_second_mailer.render(context)

        # Path to save the temporary PDF
        directory = os.path.join(BASE_DIR, "media")
        location = os.path.join(directory, filename)

        # Ensure the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory)  # Create the directory if it doesn't exist
            print(f"Created directory: {directory}")

        print(f"PDF will be saved at: {location}")

        # Generate PDF from the HTML
        pdfkit.from_string(html, location, configuration=config, options=options)

        print("PDF successfully generated.")
        with open(location, "rb") as pdf_file:
            if "first-mailer" in filename:
                upload_to_s3(pdf_file, filename, "pre_odr_first_mailer_pdfs")
                os.remove(location)
            elif "second-mailer" in filename:
                upload_to_s3(pdf_file, filename, "pre_odr_second_mailer_pdfs")
                os.remove(location)
            else:
                print("Invalid filename. Please provide a valid filename.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

def save_pre_odr_mailer_notice_pdf(filename,station_name, context):
    """
    Generates the first mailer notice PDF with data from Citation and UnpaidCitation models.
    Ensures the directory exists before saving the PDF.
    """
    try:
        # Render the HTML template with combined context data
        print("Creating")
        html = template_first_mailer.render(context) if 'first-mailer' in filename else template_second_mailer.render(context)
        if 'first-mailer' in filename:
            pdf_path = os.path.join(TEMP_PRE_ODR_FIRST_MAILER_PDFS,station_name,filename)
        elif 'second-mailer' in filename:
            pdf_path = os.path.join(TEMP_PRE_ODR_SECOND_MAILER_PDFS,station_name,filename)

        directory = os.path.dirname(pdf_path)
        if not os.path.exists(directory):
            os.makedirs(directory)  # Create the directory if it doesn't exist
            print(f"Created directory: {directory}")


        # Generate PDF from the HTML
        pdfkit.from_string(html, pdf_path, configuration=config, options=options)

        if os.path.exists(pdf_path) and is_valid_pdf(pdf_path):
            return True
        else:
            return False

    except Exception as e:
        print(f"An error occurred: {str(e)}")


def save_pre_odr_mailer_notice_pdf_manual(filename,station_name, context):
    """
    Generates the first mailer notice PDF with data from Citation and UnpaidCitation models.
    Ensures the directory exists before saving the PDF.
    """
    try:
        # Render the HTML template with combined context data
        print("Creating")
        html = template_first_mailer.render(context)
        if 'first-mailer' in filename:
            pdf_path = os.path.join(TEMP_PRE_ODR_FIRST_MAILER_PDFS,station_name,filename)
        elif 'second-mailer' in filename:
            pdf_path = os.path.join(TEMP_PRE_ODR_SECOND_MAILER_PDFS,station_name,filename)

        directory = os.path.dirname(pdf_path)
        if not os.path.exists(directory):
            os.makedirs(directory)  # Create the directory if it doesn't exist
            print(f"Created directory: {directory}")


        # Generate PDF from the HTML
        pdfkit.from_string(html, pdf_path, configuration=config, options=options)

        if os.path.exists(pdf_path) and is_valid_pdf(pdf_path):
            return True
        else:
            return False

    except Exception as e:
        print(f"An error occurred: {str(e)}")


def save_reminder_hudc_pdf(filename, station_name, data):
    
    html = template_reminder_hud_c.render(data)
    
    # pdf_path = TEMP_PDF_DIR + f"/{station_name}/"
    pdf_path = os.path.join(TEMP_REMINDER_PDF_DIR, station_name)
    save_to = os.path.join(pdf_path, filename)

    if not os.path.exists(pdf_path):
        os.makedirs(pdf_path)

    pdfkit.from_string(html, save_to, configuration=config, options=options)

    if os.path.exists(save_to) and is_valid_pdf(save_to):
        return True
    else:
        return False
    
def save_combined_pdf(cit_id, station_name, data_initial, data_reminder):
    """
    Generate one combined PDF (reminder + initial citation) in a single file.
    Page 1 = reminder, Page 2 = initial citation
    """

    # Render reminder
    html_reminder = template_reminder_hud_c.render(data_reminder)

    # Render initial citation
    if station_name in ['FED-M']:
        html_initial = template_maryland.render(data_initial)
    elif station_name in ['KRSY-C']:
        html_initial = template_kersey.render(data_initial)
    elif station_name in ['HUD-C']:
        html_initial = template_hudson.render(data_initial)
    else:
        html_initial = template.render(data_initial)

    # Wrap both templates in isolated containers
    html_combined = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}
            .page-break {{
                page-break-before: always;
            }}

            /* Scope reminder CSS */
            .reminder-section table, 
            .reminder-section th, 
            .reminder-section td {{
                border: 1px solid black;
                border-collapse: collapse;
                padding: 4px;
            }}

            /* Scope initial citation CSS */
            .initial-section table,
            .initial-section th,
            .initial-section td {{
                border: 1px solid black;
                border-collapse: collapse;
                padding: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="reminder-section">
            {html_reminder}
        </div>
        <div class="initial-section">
            {html_initial}
        </div>
    </body>
    </html>
    """

    # File Path
    base_path = r"C:\Users\EM\Documents\reminder_initial_pdfs"
    pdf_path = os.path.join(base_path, station_name)
    if not os.path.exists(pdf_path):
        os.makedirs(pdf_path)

    filename = f"{cit_id}reminder.pdf"
    save_to = os.path.join(pdf_path, filename)

    # Generate PDF
    pdfkit.from_string(html_combined, save_to, configuration=config, options=options)

    return os.path.exists(save_to)