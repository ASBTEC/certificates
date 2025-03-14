from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import shutil
import sys
import json
import subprocess

from googleapiclient.http import MediaFileUpload


# Read file passed as argument from secrets/ folder and return its content as string.
def read_secret(filename):
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", filename)
    try:
        with open(secrets_path, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Error: File {filename} not found ")
        exit(1)


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


# ['id', 'university', 'course', 'year', 'repetition', 'date_begin', 'date_end', 'date_text', 'credits',
# 'Material docent del curs', 'Carpeta Info Curs'],
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


def parse_certificate_data(row_number, row_data, course_metadata, metadata_university, metadata_courses):
    d = {}
    d["id"] = row_data[0]
    d["name"] = row_data[1].encode('utf-8').decode('utf-8')
    d["email"] = row_data[2]
    d["dni"] = row_data[3]
    d["cert_type"] = row_data[4]
    if d["cert_type"] == "ALUMNE_NOTA":
        d["mark"] = float(row_data[5])

    if d["cert_type"] == "ALUMNE_NOTA" or d["cert_type"] == "ALUMNE":
        d["cert_type_text"] = "participació"
        d["action_text"] = "la seva destacada participació al"
    elif d["cert_type"] == "PROFE":
        d["cert_type_text"] = "reconeixement"
        d["action_text"] = "haver impartit el"

    d["course_name"] = metadata_courses[course_metadata[2]][1].encode('utf-8').decode('utf-8')
    d["university_code"] = metadata_university[course_metadata[1]][0].encode('utf-8').decode('utf-8')
    d["university_name"] = metadata_university[course_metadata[1]][1].encode('utf-8').decode('utf-8')
    d["text_date"] = course_metadata[7].encode('utf-8').decode('utf-8')

    if d["cert_type"] == "ALUMNE_NOTA":
        d["credits"] = int(course_metadata[8])

    d["additional_logo_suffix_2"] = course_metadata[9].encode('utf-8').decode('utf-8')
    d["row_number"] = row_number.__str__()

    if d["cert_type"] == "ALUMNE_NOTA":
        d["student_nota_text"] = (", amb equivalència de " + d["credits"].__str__() + " crèdit(s) ECTS amb nota " +
                                  d["mark"].__str__()) + ", acreditat per la " + d["university_name"]
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
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cert_data_json, f)

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
            print("Error running script:", process.stderr.read())

    except Exception as e:
        print(f"Error executing script: {e}")


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


# Constants
SERVICE_ACCOUNT_INFO = json.loads(read_secret("SERVICE_REGISTRY.json"))
SPREADSHEET_ID = read_secret("SPREADSHEET_ID.txt")
PAGE_NAME = "certificates"
ROW_INI, ROW_END = parse_range_arguments()
PAGE_METADATA_NAME = "courses_implemented"
FOLDER_SENT_ID = read_secret("FOLDER_SENT_ID.txt")
GMAIL_USERNAME = read_secret("GMAIL_USERNAME.txt")
GMAIL_PASSWORD = read_secret("GMAIL_PASSWORD.txt")
TEST_EMAIL = read_secret("TEST_EMAIL.txt")

# Range end target. Empty rows are ignored
METADATA_MAX_ROW = 40

data = build_dict(filter_data(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, ROW_INI, ROW_END, 'A', 'I')))
metadata = build_dict(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_METADATA_NAME, 2, METADATA_MAX_ROW, 'A', 'K'))
metadata_university = build_dict(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "university", 2, METADATA_MAX_ROW, 'A', 'B'))
metadata_courses = build_dict(read_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "courses", 2, METADATA_MAX_ROW, 'A', 'B'))

r = ROW_INI
data_file_paths = {}
for row_data in data.values():
    print("* certificate-generator * Step 1: Parse row " + (r - ROW_INI + 1).__str__() + " out of " + data.values().__len__().__str__())
    course_metadata = metadata[get_id_course_from_id_cert(row_data[0])]
    cert_data = parse_certificate_data(r, row_data, course_metadata, metadata_university, metadata_courses)
    cert_data_json = json.dumps(cert_data)
    save_cert_data(cert_data_json)
    r += 1

run_script("node", "build-htmls.js", os.path.dirname(os.path.abspath(__file__)))
copy_template_files()
run_script("node", "build-pdfs.js", os.path.dirname(os.path.abspath(__file__)))

cert_num = 1
cert_total = data.keys().__len__()
for cert_id in data.keys():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", cert_id + ".json")
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs", cert_id + ".pdf")
    email = json.loads(open(json_path).read()).get("email")
    print("* certificate-generator * Step 8: Send email " + cert_num.__str__() + " out of " + cert_total.__str__())
    run_script("bash", "send-emails.sh", os.path.dirname(os.path.abspath(__file__)),
               [GMAIL_USERNAME, TEST_EMAIL, GMAIL_PASSWORD, cert_id.__str__(),
                json.loads(open(json_path).read()).get("course_name")])
    print("* certificate-generator * Step 9: Upload JSON to registry" + cert_num.__str__() + " out of " + cert_total.__str__())
    upload_file_to_drive(SERVICE_ACCOUNT_INFO, json_path, FOLDER_SENT_ID, os.path.basename(json_path))
    print("* certificate-generator * Step 10: Upload PDF to registry " + cert_num.__str__() + " out of " + cert_total.__str__())
    upload_file_to_drive(SERVICE_ACCOUNT_INFO, pdf_path, FOLDER_SENT_ID, os.path.basename(pdf_path))











