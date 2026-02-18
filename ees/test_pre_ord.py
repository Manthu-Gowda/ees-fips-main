import os
import csv
from openpyxl import Workbook
from datetime import datetime
from typing import List

def process_and_validate_data(SFTP_STATIONS: List[str]):
    """
    Process .imp files for specified stations and cross-check values.
    Store results in an Excel file with separate sheets for each station.
    """
    try:
        # Create an Excel workbook
        workbook = Workbook()
        
        for index, station in enumerate(SFTP_STATIONS, start=1):
            # Define the local directory to check for processed files
            local_dir = f"C:\\Users\\EM\\Documents\\paid_payment_files\\{station}"
            if not os.path.exists(local_dir):
                print(f"Directory {local_dir} does not exist. Skipping station {station}.")
                continue

            # Create a worksheet for the station
            if index == 1:
                worksheet = workbook.active
                worksheet.title = f"{station}"
            else:
                worksheet = workbook.create_sheet(title=f"{station}")

            # Write the header row
            worksheet.append([
                "Transaction Date", "Citation ID", "Full Name", "Paid Amount", "Transaction ID", "File Name"
            ])

            # Look for .imp files in the directory
            imp_files = [
                f for f in os.listdir(local_dir) if f.endswith(".imp") or f.endswith(".txt")
            ]
            for imp_file in imp_files:
                imp_file_path = os.path.join(local_dir, imp_file)
                try:
                    with open(imp_file_path, "r") as f:
                        reader = csv.reader(f)
                        for row in reader:
                            try:
                                # Assuming .imp file format: date, citation_id, full_name, paid_amount, transaction_id
                                transaction_date = datetime.strptime(row[0], "%m/%d/%Y").date()
                                citation_id = row[1]
                                full_name = row[2]
                                paid_amount = float(row[3])
                                transaction_id = row[4]

                                # Append the processed row to the Excel sheet
                                worksheet.append([
                                    transaction_date, citation_id, full_name, paid_amount, transaction_id, imp_file
                                ])

                            except Exception as e:
                                print(f"Error processing row {row} in file {imp_file}: {e}")
                                continue

                except Exception as e:
                    print(f"Error reading file {imp_file_path}: {e}")

        # Save the Excel workbook
        excel_output_path = "C:\\Users\\EM\\Documents\\paid_payment_files\\Processed_Paid_Citations.xlsx"
        workbook.save(excel_output_path)
        print(f"Excel file with processed data saved to {excel_output_path}.")

    except Exception as e:
        print(f"Error occurred while processing and validating data: {e}")

# Specify the stations to process
stations = ["FED-M","WBR2"]
process_and_validate_data(stations)