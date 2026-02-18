import os, csv,shutil

from video.models import QuickPD

def xpress_csv(input_file, fine, issuing_agency):
    try:
        col = ['id', 'offense_date', 'offense_time', 'ticket_num', 'first_name', 'middle', 'last_name', 'generation', 'address',
               'city', 'state', 'zip', 'dob', 'race', 'sex', 'height', 'weight', 'ssn', 'dl', 'dl_state', 'accident',
               'comm', 'vehder', 'arraignment_date', 'actual_speed', 'posted_speed', 'officer_badge', 'street1_id',
               'street2_id', 'street1_name', 'street2_name', 'bac', 'test_type', 'plate_num', 'plate_state', 'vin',
               'phone_number', 'radar', 'state_rs1', 'state_rs2', 'state_rs3', 'state_rs4', 'state_rs5', 'warning',
               'notes', 'dl_class', 'station_id', 'fine', 'issuing_agency']

        print(len(col))

        with open(input_file, 'r') as initial_csv:
            reader = csv.reader(initial_csv)
            data = [row for row in reader]

            for row in data:
                if len(row) < len(col) - 3:
                    row.extend([''] * (len(col) - 3 - len(row)))
                id_num = QuickPD.objects.get(ticket_num =row[2])
                row.insert(0,id_num.id)
                row.append(str(fine))
                row.append(issuing_agency)

        with open(input_file, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(col)
            csv_writer.writerows(data)
        print("Successfully generated for Xpress Bill Pay")

    except Exception as e:
        print(e)
    
file_path = r'C:\Users\EM\test_script\HUD-C-Citations-12152024.csv'
xpress_csv(file_path,40.00, "Hudson Colorado")