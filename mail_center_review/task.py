def generate_mailcenter_pdfs_and_csvs(citation_ids, date_type):
    from .mail_center_review_utils import create_csv_and_pdf_data_for_agencies

    create_csv_and_pdf_data_for_agencies(
        citationid=citation_ids,
        date_type=date_type
    )