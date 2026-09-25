from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import shutil
import sys
import json
import subprocess
from datetime import datetime

from googleapiclient.http import MediaFileUpload

from translations import format_days, get_translation, normalize_language


# Read file passed as argument from secrets/ folder and return its content as string.
def read_secret(filename):
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", filename)
    try:
        with open(secrets_path, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"Error: File {filename} not found")


def parse_range_arguments():
    if len(sys.argv) < 3:
        raise ValueError("Two arguments are required.")
    try:
        n1 = int(sys.argv[1])
        n2 = int(sys.argv[2])
        if n1 < 1 or n2 < 1:
            raise ValueError("Both numbers must be natural numbers (greater than 0).")

        n3 = 0
        # Swap arguments if n1 is bigger than n2
        if n1 > n2:
            n3 = n2
            n2 = n1
            n1 = n3

        if n1 == 1:
            raise ValueError("First row must not be included in parsing range.")
        return n1, n2
    except ValueError as e:
        raise ValueError(f"Invalid input: {e}")


def build_google_service(service_account_info, scopes, service_name, version):
    # Authentication with service account (Google cloud)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
        # Change to 'readwrite' if you also want to write
    )

    # Build API service
    service = build(service_name, version, credentials=credentials)

    return service


def read_rows(service_account_info, spreadsheet_id, page, initial_row, end_row, initial_column, end_column):
    range_name = f"{page}!" + initial_column + initial_row.__str__() + ":" + end_column + end_row.__str__()

    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/spreadsheets.readonly"], "sheets", "v4")

    try:
        # API call
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()

        values = result.get('values', [])

        if not values:
            raise ValueError("No values found")
        else:
            return values

    except HttpError as err:
        raise HttpError(f"An error occurred while reading the range: {err}")


# Reads a whole tab and returns its rows as dicts keyed by the header row (row 1). Empty rows are skipped.
def read_table(service_account_info, spreadsheet_id, page, required_columns):
    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/spreadsheets.readonly"], "sheets", "v4")

    try:
        values = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=page).execute().get('values', [])
    except HttpError as err:
        raise RuntimeError(f"An error occurred while reading the tab {page}: {err}")

    if not values:
        raise ValueError(f"No values found in tab {page}")

    header = [column.strip() for column in values[0]]
    missing = [column for column in required_columns if column not in header]
    if missing:
        raise ValueError(f"Tab {page} is missing the column(s) {missing}. Found columns: {header}")

    rows = []
    for row in values[1:]:
        if not any(cell.strip() for cell in row):
            continue
        # The Sheets API omits trailing empty cells
        rows.append({column: (row[i].strip() if i < len(row) else "") for i, column in enumerate(header)})
    return rows


# Joins dates_intermediate -> dates -> days_intermediate -> days and returns {course_id: [datetime.date, ...]}.
def build_course_days(dates_intermediate, dates, days_intermediate, days):
    date_ids = {row["id"] for row in dates}

    day_by_id = {}
    for row in days:
        try:
            day_by_id[row["id"]] = datetime.strptime(row["date"], "%d/%m/%Y").date()
        except ValueError:
            raise ValueError(f"Day {row['id']} has date \"{row['date']}\", expected format DD/MM/YYYY")

    days_by_date = {}
    for row in days_intermediate:
        if row["date_id"] not in date_ids:
            raise ValueError(f"days_intermediate references unknown date_id \"{row['date_id']}\"")
        if row["day_id"] not in day_by_id:
            raise ValueError(f"days_intermediate references unknown day_id \"{row['day_id']}\"")
        days_by_date.setdefault(row["date_id"], set()).add(day_by_id[row["day_id"]])

    course_days = {}
    for row in dates_intermediate:
        if row["date_id"] not in date_ids:
            raise ValueError(f"dates_intermediate references unknown date_id \"{row['date_id']}\"")
        course_days.setdefault(row["course_id"], set()).update(days_by_date.get(row["date_id"], set()))

    return {course_id: sorted(course_day_set) for course_id, course_day_set in course_days.items()}


def write_cell(service_account_info, spreadsheet_id, page, column, row, value):
    cell = f"{column}{row}"
    range_name = f"{page}!{cell}"

    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/spreadsheets"], "sheets",
                                   "v4")

    try:
        sheet = service.spreadsheets()
        body = {'values': [[value]]}  # Wrap in double list to match Sheets API format

        result = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body
        ).execute()

        return result

    except HttpError as err:
        raise HttpError(f"An error occurred while writing to the cell: {err}")


# num_cert	name	dni	email	cert_type	mark	ready?	created?	sent?
# Removes rows that do not follow rules for certificate generation
def filter_data(data):
    filtered_data = []
    for row in data:
        # Ignore not ready rows
        if row[6] == "no":
            continue
        filtered_data.append(row)

    return filtered_data


def build_dict(metadata):
    d = {}
    for row in metadata:
        d[row[0]] = row
    return d


def get_id_course_from_id_cert(id_cert):
    try:
        return "-".join(row_data[0].split("-")[0:4])
    except ValueError:
        raise ValueError("the id course could not have been computed from id cert \"" + id_cert + "\"")


# Resolves a signature id of a course into the name, translated position and image of the signer.
def build_signature(signature_id, signatures, translation):
    if signature_id not in signatures:
        raise ValueError(f"Unknown signature id \"{signature_id}\" in courses_implemented")
    signature = signatures[signature_id]
    if signature["sign_as"] not in translation["sign_as"]:
        raise ValueError(f"Signature {signature_id} has unknown sign_as \"{signature['sign_as']}\". "
                         f"Supported values: {', '.join(translation['sign_as'].keys())}")
    image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "template_files",
                              signature["signature_image"])
    if not os.path.isfile(image_path):
        raise ValueError(f"Signature {signature_id} image \"{signature['signature_image']}\" not found in template_files")
    return {"name": signature["name"], "position": translation["sign_as"][signature["sign_as"]],
            "image": signature["signature_image"]}


def parse_certificate_data(row_number, row_data, course_metadata, metadata_university, metadata_courses, course_days,
                           signatures):
    d = {}
    d["id"] = row_data[0]
    d["name"] = row_data[1].encode('utf-8').decode('utf-8')
    d["email"] = row_data[2]
    d["dni"] = row_data[3]
    d["cert_type"] = row_data[4]
    if d["cert_type"] == "ALUMNE_NOTA":
        d["mark"] = float(row_data[5])

    d["language"] = normalize_language(course_metadata["language"])
    translation = get_translation(d["language"])
    d["i18n"] = {key: value for key, value in translation.items() if key not in ("cert_types", "student_nota_text", "dates", "sign_as")}
    d["signature1"] = build_signature(course_metadata["signature1"], signatures, translation)
    d["signature2"] = build_signature(course_metadata["signature2"], signatures, translation)

    if d["cert_type"] in translation["cert_types"]:
        d["cert_type_text"] = translation["cert_types"][d["cert_type"]]["title"]
        d["action_text"] = translation["cert_types"][d["cert_type"]]["action"]

    d["course_name"] = metadata_courses[course_metadata["course"]][1].encode('utf-8').decode('utf-8')
    d["university_code"] = metadata_university[course_metadata["university"]][0].encode('utf-8').decode('utf-8')
    d["university_name"] = metadata_university[course_metadata["university"]][1].encode('utf-8').decode('utf-8')

    if course_metadata["id"] not in course_days:
        raise ValueError(f"Course {course_metadata['id']} has no days in dates_intermediate / days_intermediate")
    d["text_date"] = format_days(course_days[course_metadata["id"]], d["language"])

    if d["cert_type"] == "ALUMNE_NOTA":
        d["credits"] = int(course_metadata["credits"])

    d["additional_logo_suffix_2"] = course_metadata["Additional_logo_suffix"].encode('utf-8').decode('utf-8')
    d["event_type"] = course_metadata["event_type"].encode('utf-8').decode('utf-8')
    d["row_number"] = row_number.__str__()

    if d["cert_type"] == "ALUMNE_NOTA":
        d["student_nota_text"] = translation["student_nota_text"].format(credits=d["credits"], mark=d["mark"],
                                                                         university_name=d["university_name"])
    elif d["cert_type"] == "PROFE" or d["cert_type"] == "ALUMNE":
        d["student_nota_text"] = ""
    return d


def save_cert_data(cert_data):
    try:
        # Ensure data/ folder exists
        os.makedirs("data", exist_ok=True)

        # Parse JSON string into dictionary
        cert_data_json = json.loads(cert_data)

        # Get the id and email field
        id = cert_data_json.get("id")
        if not id:
            raise ValueError("Missing 'id' field in cert_data")
        email = cert_data_json.get("email")
        if not email:
            raise ValueError("Missing 'email' field in cert_data")

        # Define the file path
        file_path = os.path.join("data", f"{id}.json")

        # Save the JSON data to the file
        with open(file_path, "w") as f:
            f.write(json.dumps(cert_data_json, indent=4).encode('utf-8').decode('unicode_escape'))

        print(f"Saved certificate data to {file_path}")
        return file_path

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error processing cert_data: {e}")


def run_script(binary, file_name, wd, args=None):
    if args is None:
        args = []
    try:
        print(f"Running {file_name} with {wd}")

        # Path to the JavaScript file
        js_file = os.path.join(wd, file_name)

        # Run the Node.js script and stream the output in real-time
        process = subprocess.Popen([binary, js_file] + args, cwd=wd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Print output line by line
        for line in process.stdout:
            print(line, end="")
        for line in process.stderr:
            print(line, end="")

        # Wait for the process to complete
        process.wait()

        # Check for errors
        if process.returncode != 0:
            raise RuntimeError(f"Error running script with return code " + process.returncode.__str__() + " :" + process.stderr.read())

    except Exception as e:
        raise RuntimeError(f"Error executing script: {e}")


def copy_template_files():
    try:
        # Define source and destination paths
        source = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "template_files")
        destination = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "certs", "template_files")

        # Ensure the destination directory exists
        os.makedirs(destination, exist_ok=True)

        # Copy the entire folder
        shutil.copytree(source, destination, dirs_exist_ok=True)

        print(f"Successfully copied '{source}' to '{destination}'")

    except Exception as e:
        print(f"Error copying files: {e}")


def upload_file_to_drive(service_account_info, file_path, folder_id, file_name=""):
    """Uploads a file to a specified Google Drive folder using a service account."""
    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/drive.file"], "drive", "v3")

    # If empty, get file name from path
    if file_name == "":
        file_name = os.path.basename(file_path)

    # File metadata
    file_metadata = {
        "name": file_name,
        "parents": [folder_id]  # Upload to the specified folder
    }

    # Upload file
    media = MediaFileUpload(file_path, mimetype='*/*',
                            chunksize=1024 * 1024, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True, supportsTeamDrives=True).execute()
    print(f"File uploaded successfully! File ID: {file.get('id')}")
    return file.get("id")


# Function to move a file
def move_file(service_account_info, file_id, new_folder_id, origin_folder_id):
    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/drive.file"], "drive", "v3")

    try:
        # Get the current file's metadata
        file = service.files().get(fileId=file_id, fields='id, parents', supportsAllDrives=True, supportsTeamDrives=True).execute()

        previous_parents = ",".join(file.get('parents'))
        print("preious parent is " + previous_parents)

        # Move the file to the new folder by updating its parent
        updated_file = service.files().update(
            fileId=file_id,
            addParents=new_folder_id,
            removeParents=previous_parents,
            fields='id, parents',
            supportsAllDrives=True,
            supportsTeamDrives=True
        ).execute()

        print(f"File moved to folder with ID: {new_folder_id}")
    except HttpError as error:
        print(f"An error occurred: {error}")


def add_email_to_filename(filename, email):
    parts = filename.split(".")
    return parts[0] + "_" + email + "." + parts[1]


# Constants
SERVICE_ACCOUNT_INFO = json.loads(read_secret("SERVICE_REGISTRY.json"))

SPREADSHEET_ID = read_secret("SPREADSHEET_ID.txt")
PAGE_NAME = "_certificate_history"
PAGE_METADATA_NAME = "courses_implemented"

FOLDER_CREATED_ID = read_secret("FOLDER_CREATED_ID.txt")
FOLDER_SENT_ID = read_secret("FOLDER_SENT_ID.txt")
GMAIL_USERNAME = read_secret("GMAIL_USERNAME.txt")
GMAIL_PASSWORD = read_secret("GMAIL_PASSWORD.txt")
TEST_EMAIL = read_secret("TEST_EMAIL.txt")
GMAIL_FROM = read_secret("GMAIL_FROM.txt")

ROW_INI, ROW_END = parse_range_arguments()

# Range end target. Empty rows are ignored
METADATA_MAX_ROW = 40

data = build_dict(filter_data(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, ROW_INI, ROW_END, 'A', 'I')))
metadata = {row["id"]: row for row in read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_METADATA_NAME,
                                                 ["id", "university", "course", "credits", "Additional_logo_suffix",
                                                  "event_type", "language", "signature1", "signature2"])}
signatures = {row["id"]: row for row in read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "signatures",
                                                   ["id", "sign_as", "signature_image", "name"])}
metadata_university = build_dict(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "university", 2, METADATA_MAX_ROW, 'A', 'B'))
metadata_courses = build_dict(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "courses", 2, METADATA_MAX_ROW, 'A', 'B'))
course_days = build_course_days(
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "dates_intermediate", ["course_id", "date_id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "dates", ["id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "days_intermediate", ["date_id", "day_id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "days", ["id", "date"]))

r = ROW_INI
data_file_paths = {}
for row_data in data.values():
    print("* certificate-generator * Step 1: Parse row " + (r - ROW_INI + 1).__str__() + " out of " + data.values().__len__().__str__())
    course_metadata = metadata[get_id_course_from_id_cert(row_data[0])]
    cert_data = parse_certificate_data(r, row_data, course_metadata, metadata_university, metadata_courses, course_days, signatures)
    cert_data_json = json.dumps(cert_data)
    save_cert_data(cert_data_json)
    r += 1

run_script("node", "build-htmls.js", os.path.dirname(os.path.abspath(__file__)))
run_script("node", "build-pdfs.js", os.path.dirname(os.path.abspath(__file__)))

cert_num = 1
cert_total = data.keys().__len__()
for cert_id in data.keys():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", cert_id + ".json")
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs", cert_id + ".pdf")
    email = json.loads(open(json_path).read()).get("email")  # Uncomment this to send it to the real destination (prod)
    #email = "someone@asbtec.cat"  # You can uncomment and / or modify this line to send to a reviewer the certificates
    email = "certificats@asbtec.cat"  # You can uncomment and / or modify this line to send to a reviewer the certificates

    print("* certificate-generator * Step 8: Upload PDF to created registry " + cert_num.__str__() + " out of " + cert_total.__str__())
    pdf_id = upload_file_to_drive(SERVICE_ACCOUNT_INFO, pdf_path, FOLDER_CREATED_ID, add_email_to_filename(os.path.basename(pdf_path), email))
    write_cell(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, "I", json.loads(open(json_path).read()).get("row_number"), "yes")

    print("* certificate-generator * Step 9: Send email " + cert_num.__str__() + " out of " + cert_total.__str__())
    try:
        run_script("bash", "send-emails.sh", os.path.dirname(os.path.abspath(__file__)),
                   [GMAIL_USERNAME, email, GMAIL_PASSWORD, cert_id.__str__(),
                    json.loads(open(json_path).read()).get("course_name"), json.loads(open(json_path).read()).get("name"), GMAIL_FROM,
                    json.loads(open(json_path).read()).get("language")])
    except Exception:
        print("Could not send PDF " + os.path.basename(pdf_path))

    write_cell(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, "J", json.loads(open(json_path).read()).get("row_number"), "yes")
    write_cell(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, "K", json.loads(open(json_path).read()).get("row_number"), f"https://drive.google.com/file/d/{str(pdf_id)}")

    # Reaching this instruction implies that we have sent the PDF, so we can move from folder
    print("* certificate-generator * Step 10: Move PDF from created registry to sent registry " + cert_num.__str__() + " out of " + cert_total.__str__())
    move_file(SERVICE_ACCOUNT_INFO, pdf_id, FOLDER_SENT_ID, FOLDER_CREATED_ID)
    cert_num += 1
