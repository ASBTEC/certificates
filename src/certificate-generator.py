from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import argparse
import os
import shutil
import sys
import json
import subprocess
import time
from datetime import datetime

from googleapiclient.http import MediaFileUpload

from mailer import Mailer, build_certificate_email
from translations import format_days, format_organisers, get_translation, normalize_language


# Read file passed as argument from secrets/ folder and return its content as string.
def read_secret(filename):
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", filename)
    try:
        with open(secrets_path, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"Error: File {filename} not found")


# Parses the command line: the range of _certificate_history rows to generate, the mode and --force.
#   --production / --prod: upload to Drive, send the email to the address in the spreadsheet and write url_cert, sent
#                           and commit_SHA_ID. Asks for confirmation unless --force is given.
#   --test:                 send the email to secrets/TEST_EMAIL. Nothing is uploaded or written to the spreadsheet.
#   --dev / --develop:      send the email to secrets/DEV_EMAIL. Nothing is uploaded or written to the spreadsheet.
#                           Default mode.
# certificats@asbtec.cat always receives a copy (see mailer.py).
def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate ASBTEC certificates from the rows of _certificate_history.")
    parser.add_argument("first_row", type=int, help="first spreadsheet row to generate (2 or greater)")
    parser.add_argument("last_row", type=int, help="last spreadsheet row to generate")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--production", "--prod", dest="mode", action="store_const", const="production",
                      help="send the certificates to their recipients and archive them in Drive")
    mode.add_argument("--test", dest="mode", action="store_const", const="test",
                      help="send every certificate to secrets/TEST_EMAIL, without archiving")
    mode.add_argument("--dev", "--develop", dest="mode", action="store_const", const="dev",
                      help="send every certificate to secrets/DEV_EMAIL, without archiving (default)")
    parser.set_defaults(mode="dev")
    parser.add_argument("-f", "--force", action="store_true", help="skip the confirmation of the production mode")
    args = parser.parse_args()

    # Swap arguments if first_row is bigger than last_row
    first_row, last_row = sorted((args.first_row, args.last_row))
    if first_row < 1:
        parser.error("Both rows must be natural numbers (greater than 0).")
    if first_row == 1:
        parser.error("First row must not be included in parsing range.")
    return first_row, last_row, args.mode, args.force


# Asks the user to confirm a production run, which sends emails to the real recipients.
def confirm_production(certificate_count, first_row, last_row, commit_sha):
    print(f"PRODUCTION mode: {certificate_count} certificate(s) from rows {first_row} to {last_row} will be uploaded to "
          f"Drive and emailed to their recipients. Commit: {commit_sha}")
    try:
        answer = input("Type 'yes' to continue: ")
    except EOFError:
        answer = ""
    if answer.strip().lower() != "yes":
        sys.exit("Aborted. Use --force to skip this confirmation.")


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


# Validates the header of a tab and converts its rows into dicts keyed by header name. Empty rows are skipped. Each row
# also gets its spreadsheet row number under "row_number", starting at first_row_number for the first row of rows.
def rows_to_dicts(page, header_values, rows, required_columns, first_row_number):
    header = [column.strip() for column in header_values]
    missing = [column for column in required_columns if column not in header]
    if missing:
        raise ValueError(f"Tab {page} is missing the column(s) {missing}. Found columns: {header}")

    result = []
    for offset, row in enumerate(rows):
        if not any(cell.strip() for cell in row):
            continue
        # The Sheets API omits trailing empty cells
        d = {column: (row[i].strip() if i < len(row) else "") for i, column in enumerate(header)}
        d["row_number"] = first_row_number + offset
        result.append(d)
    return header, result


# Reads a whole tab and returns its rows as dicts keyed by the header row (row 1).
def read_table(service_account_info, spreadsheet_id, page, required_columns):
    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/spreadsheets.readonly"], "sheets", "v4")

    try:
        values = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=page).execute(num_retries=GOOGLE_API_RETRIES).get('values', [])
    except HttpError as err:
        raise RuntimeError(f"An error occurred while reading the tab {page}: {err}")

    if not values:
        raise ValueError(f"No values found in tab {page}")

    return rows_to_dicts(page, values[0], values[1:], required_columns, 2)[1]


# Reads the header row (row 1) and the rows first_row..last_row of a tab. Returns the header, used to locate columns
# when writing, and the rows as dicts keyed by header with their spreadsheet row number under "row_number".
def read_table_rows(service_account_info, spreadsheet_id, page, first_row, last_row, required_columns):
    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/spreadsheets.readonly"], "sheets", "v4")

    try:
        value_ranges = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id, ranges=[f"{page}!1:1", f"{page}!{first_row}:{last_row}"]).execute(num_retries=GOOGLE_API_RETRIES).get("valueRanges", [])
    except HttpError as err:
        raise RuntimeError(f"An error occurred while reading the tab {page}: {err}")

    header_values = value_ranges[0].get("values", [[]])[0]
    rows = value_ranges[1].get("values", [])
    if not rows:
        raise ValueError(f"No values found in rows {first_row} to {last_row} of tab {page}")

    return rows_to_dicts(page, header_values, rows, required_columns, first_row)


# Returns the column letter (A, B, ..., Z, AA, ...) of the column with the given header name.
def column_letter(header, column_name):
    if column_name not in header:
        raise ValueError(f"Column {column_name} not found. Found columns: {header}")
    index = header.index(column_name) + 1
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


# Returns the SHA of the commit checked out in this repository, with a "-dirty" suffix if tracked files have
# uncommitted changes, so that each certificate can be traced back to the code that rendered it.
def get_commit_sha():
    repository_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository_path, capture_output=True, text=True,
                         check=True).stdout.strip()
    changes = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repository_path,
                             capture_output=True, text=True, check=True).stdout.strip()
    return sha + "-dirty" if changes else sha


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


# Joins organizers_intermediate -> organizers and returns {course_id: [organizer name, ...]}, keeping the order of the
# organizers_intermediate rows and skipping repeated organizers of a course.
def build_course_organisers(organizers_intermediate, organizers):
    name_by_id = {row["id"]: row["name"] for row in organizers}
    course_organisers = {}
    for row in organizers_intermediate:
        if row["organizer_id"] not in name_by_id:
            raise ValueError(f"organizers_intermediate references unknown organizer_id \"{row['organizer_id']}\"")
        names = course_organisers.setdefault(row["course_id"], [])
        if name_by_id[row["organizer_id"]] not in names:
            names.append(name_by_id[row["organizer_id"]])
    return course_organisers


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
        ).execute(num_retries=GOOGLE_API_RETRIES)

        return result

    except HttpError as err:
        raise RuntimeError(f"An error occurred while writing to the cell {range_name}: {err}")


def get_id_course_from_id_cert(id_cert):
    try:
        return "-".join(id_cert.split("-")[0:4])
    except ValueError:
        raise ValueError("the id course could not have been computed from id cert \"" + id_cert + "\"")


# Resolves a signature id of a course into the name, translated position and image of the signer. The image is used
# as is as the image source in the template: a file name inside templates/ or a URL.
def build_signature(signature_id, signatures, translation):
    if signature_id not in signatures:
        raise ValueError(f"Unknown signature id \"{signature_id}\" in courses_implemented")
    signature = signatures[signature_id]
    if signature["sign_as"] not in translation["sign_as"]:
        raise ValueError(f"Signature {signature_id} has unknown sign_as \"{signature['sign_as']}\". "
                         f"Supported values: {', '.join(translation['sign_as'].keys())}")
    return {"name": signature["name"], "position": translation["sign_as"][signature["sign_as"]],
            "image": signature["signature_image"]}


# Returns a logo cell value, used as is as the image source in the template: a file name inside templates/ or a URL.
# An empty cell (or the legacy "-") renders the transparent placeholder EMPTY_LOGO.
def get_logo_file(logo):
    if logo in ("", "-"):
        return EMPTY_LOGO
    return logo


def parse_certificate_data(certificate_row, course_metadata, metadata_university, metadata_courses, course_days,
                           signatures, course_organisers):
    d = {}
    d["id"] = certificate_row["id"]
    d["name"] = certificate_row["name"]
    d["email"] = certificate_row["email"]
    d["dni"] = certificate_row["NIF"]
    d["cert_type"] = certificate_row["cert_type"]
    if d["cert_type"] == "ALUMNE_NOTA":
        d["mark"] = float(certificate_row["mark"])

    d["language"] = normalize_language(course_metadata["language"])
    translation = get_translation(d["language"])
    d["i18n"] = {key: value for key, value in translation.items() if key not in ("cert_types", "student_nota_text", "dates", "sign_as", "event_types",
                                                             "email_subject", "email_body", "organised_by",
                                                             "and_before_i")}
    d["signature1"] = build_signature(course_metadata["signature1"], signatures, translation)
    d["signature2"] = build_signature(course_metadata["signature2"], signatures, translation)

    if d["cert_type"] in translation["cert_types"]:
        d["cert_type_text"] = translation["cert_types"][d["cert_type"]]["title"]
        d["action_text"] = translation["cert_types"][d["cert_type"]]["action"]

    d["course_name"] = metadata_courses[course_metadata["course"]]["name"]
    d["university_code"] = metadata_university[course_metadata["university"]]["id"]
    d["university_logo"] = get_logo_file(metadata_university[course_metadata["university"]]["logo_file"])
    d["university_name"] = metadata_university[course_metadata["university"]]["name"]

    if course_metadata["id"] not in course_days:
        raise ValueError(f"Course {course_metadata['id']} has no days in dates_intermediate / days_intermediate")
    d["text_date"] = format_days(course_days[course_metadata["id"]], d["language"])

    if course_metadata["id"] not in course_organisers:
        raise ValueError(f"Course {course_metadata['id']} has no organizers in organizers_intermediate")
    d["organised_by"] = format_organisers(course_organisers[course_metadata["id"]], d["language"])

    if d["cert_type"] == "ALUMNE_NOTA":
        d["credits"] = int(course_metadata["credits"])

    d["additional_logo"] = get_logo_file(course_metadata["additional_logo_file"])
    d["event_type"] = course_metadata["event_type"]
    if d["event_type"] not in translation["event_types"]:
        raise ValueError(f"Course {course_metadata['id']} has unknown event_type \"{d['event_type']}\". "
                         f"Supported values: {', '.join(translation['event_types'].keys())}")
    # Word written just before the course name, e.g. curs "Biotecnologia"
    d["course_type"] = translation["event_types"][d["event_type"]]
    d["row_number"] = certificate_row["row_number"].__str__()

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


# Escapes a value to be used inside single quotes in a Google Drive search query.
def escape_drive_query(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


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

    media = MediaFileUpload(file_path, mimetype='*/*',
                            chunksize=1024 * 1024, resumable=True)

    # If a file with the same name already exists in the folder, overwrite its content. It keeps its id, so links to it
    # stay valid, and Drive keeps the previous content in the file's version history
    query = (f"name = '{escape_drive_query(file_name)}' and '{folder_id}' in parents and "
             f"mimeType != 'application/vnd.google-apps.folder' and trashed = false")
    existing_files = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True,
                                          includeItemsFromAllDrives=True).execute(num_retries=GOOGLE_API_RETRIES).get("files", [])
    if existing_files:
        if len(existing_files) > 1:
            print(f"Warning: {len(existing_files)} files named {file_name} found, overwriting {existing_files[0]['id']}")
        file = service.files().update(fileId=existing_files[0]["id"], media_body=media, fields="id",
                                      supportsAllDrives=True).execute(num_retries=GOOGLE_API_RETRIES)
        print(f"File overwritten successfully! File ID: {file.get('id')}")
        return file.get("id")

    file = service.files().create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True, supportsTeamDrives=True).execute(num_retries=GOOGLE_API_RETRIES)
    print(f"File uploaded successfully! File ID: {file.get('id')}")
    return file.get("id")


# Returns the id of the subfolder with the given name inside parent_folder_id, creating it if it does not exist.
# Results are cached in folder_cache to avoid repeated API calls for certificates of the same course.
def get_or_create_folder(service_account_info, parent_folder_id, name, folder_cache):
    if (parent_folder_id, name) in folder_cache:
        return folder_cache[(parent_folder_id, name)]

    service = build_google_service(service_account_info, ["https://www.googleapis.com/auth/drive.file"], "drive", "v3")
    query = (f"name = '{escape_drive_query(name)}' and '{parent_folder_id}' in parents and "
             f"mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    folders = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True,
                                   includeItemsFromAllDrives=True).execute(num_retries=GOOGLE_API_RETRIES).get("files", [])
    if folders:
        folder_id = folders[0]["id"]
    else:
        folder_metadata = {"name": name, "parents": [parent_folder_id], "mimeType": "application/vnd.google-apps.folder"}
        folder_id = service.files().create(body=folder_metadata, fields="id", supportsAllDrives=True).execute(num_retries=GOOGLE_API_RETRIES).get("id")
        print(f"Created folder {name} with ID: {folder_id}")

    folder_cache[(parent_folder_id, name)] = folder_id
    return folder_id


def add_email_to_filename(filename, email):
    parts = filename.split(".")
    return parts[0] + "_" + email + "." + parts[1]


# Constants
SERVICE_ACCOUNT_INFO = json.loads(read_secret("SERVICE_REGISTRY.json"))

SPREADSHEET_ID = read_secret("SPREADSHEET_ID.txt")
PAGE_NAME = "_certificate_history"
PAGE_METADATA_NAME = "courses_implemented"
EMPTY_LOGO = "logo_empty.png"
# Retries of Google Drive and spreadsheet requests on rate limit (403 userRateLimitExceeded / rateLimitExceeded, 429) and server (5xx)
# errors. The client library waits a random time between 0 and 2^n seconds before retry n (exponential backoff), so 8
# retries wait up to ~8.5 minutes in total in the worst case.
GOOGLE_API_RETRIES = 8
# Email sending. All emails share one SMTP login (see mailer.py). Pause between emails, and retry temporary failures
# waiting EMAIL_RETRY_BASE_SECONDS * 2^n (+ jitter) before retry n, i.e. ~30 s, 1, 2, 4 and 8 min (~16 min in total in
# the worst case).
EMAIL_DELAY_SECONDS = 2
EMAIL_RETRIES = 5
EMAIL_RETRY_BASE_SECONDS = 30

FOLDER_SENT_ID = read_secret("FOLDER_SENT_ID.txt")
GMAIL_USERNAME = read_secret("GMAIL_USERNAME.txt")
GMAIL_PASSWORD = read_secret("GMAIL_PASSWORD.txt")
GMAIL_FROM = read_secret("GMAIL_FROM.txt")

ROW_INI, ROW_END, MODE, FORCE = parse_arguments()
# Recipient of every certificate in test and dev modes. Production uses the email of each spreadsheet row
MODE_EMAIL = {"test": "TEST_EMAIL", "dev": "DEV_EMAIL"}
OVERRIDE_EMAIL = read_secret(MODE_EMAIL[MODE]) if MODE in MODE_EMAIL else None

COMMIT_SHA = get_commit_sha()

HISTORY_HEADER, certificate_rows = read_table_rows(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, ROW_INI, ROW_END,
                                                   ["id", "name", "email", "NIF", "cert_type", "mark", "assisted", "ready",
                                                    "sent", "url_cert", "commit_SHA_ID"])
# Ignore rows of people that did not assist and rows not ready to be generated
data = {row["id"]: row for row in certificate_rows if row["assisted"] != "no" and row["ready"] != "no"}

print(f"* certificate-generator * Mode: {MODE}")
if MODE == "production" and not FORCE:
    confirm_production(len(data), ROW_INI, ROW_END, COMMIT_SHA)
metadata = {row["id"]: row for row in read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_METADATA_NAME,
                                                 ["id", "university", "course", "credits", "additional_logo_file",
                                                  "event_type", "language", "signature1", "signature2"])}
signatures = {row["id"]: row for row in read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "signatures",
                                                   ["id", "sign_as", "signature_image", "name"])}
metadata_university = {row["id"]: row for row in read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "university", ["id", "name", "logo_file"])}
metadata_courses = {row["id"]: row for row in read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "courses", ["id", "name"])}
course_days = build_course_days(
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "dates_intermediate", ["course_id", "date_id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "dates", ["id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "days_intermediate", ["date_id", "day_id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "days", ["id", "date"]))
course_organisers = build_course_organisers(
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "organizers_intermediate", ["course_id", "organizer_id"]),
    read_table(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, "organizers", ["id", "name"]))

row_num = 1
for certificate_row in data.values():
    print("* certificate-generator * Step 1: Parse row " + row_num.__str__() + " out of " + data.values().__len__().__str__())
    course_metadata = metadata[get_id_course_from_id_cert(certificate_row["id"])]
    cert_data = parse_certificate_data(certificate_row, course_metadata, metadata_university, metadata_courses, course_days, signatures, course_organisers)
    cert_data_json = json.dumps(cert_data)
    save_cert_data(cert_data_json)
    row_num += 1

run_script("node", "build-htmls.js", os.path.dirname(os.path.abspath(__file__)))
run_script("node", "build-pdfs.js", os.path.dirname(os.path.abspath(__file__)))

folder_cache = {}
mailer = Mailer(GMAIL_USERNAME, GMAIL_PASSWORD, GMAIL_FROM, EMAIL_RETRIES, EMAIL_RETRY_BASE_SECONDS)
cert_num = 1
cert_total = data.keys().__len__()
for cert_id in data.keys():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", cert_id + ".json")
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs", cert_id + ".pdf")
    email = json.loads(open(json_path).read()).get("email") if MODE == "production" else OVERRIDE_EMAIL

    # Only production records the certificate in the spreadsheet and archives the PDF in Drive
    if MODE == "production":
        write_cell(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, column_letter(HISTORY_HEADER, "commit_SHA_ID"), json.loads(open(json_path).read()).get("row_number"), COMMIT_SHA)
        print("* certificate-generator * Step 8: Upload PDF to sent registry " + cert_num.__str__() + " out of " + cert_total.__str__())
        course_sent_folder_id = get_or_create_folder(SERVICE_ACCOUNT_INFO, FOLDER_SENT_ID, get_id_course_from_id_cert(cert_id), folder_cache)
        pdf_id = upload_file_to_drive(SERVICE_ACCOUNT_INFO, pdf_path, course_sent_folder_id, add_email_to_filename(os.path.basename(pdf_path), email))
        write_cell(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, column_letter(HISTORY_HEADER, "url_cert"), json.loads(open(json_path).read()).get("row_number"), f"https://drive.google.com/file/d/{str(pdf_id)}")

    print("* certificate-generator * Step 9: Send email to " + email + " " + cert_num.__str__() + " out of " + cert_total.__str__())
    try:
        mailer.send(build_certificate_email(email, json.loads(open(json_path).read()).get("name"),
                                            json.loads(open(json_path).read()).get("course_name"),
                                            json.loads(open(json_path).read()).get("language"), pdf_path), email)
    except Exception as e:
        print("Could not send PDF " + os.path.basename(pdf_path) + ": " + str(e))
    else:
        # Only production marks the certificate as sent to its recipient
        if MODE == "production":
            write_cell(SERVICE_ACCOUNT_INFO, SPREADSHEET_ID, PAGE_NAME, column_letter(HISTORY_HEADER, "sent"), json.loads(open(json_path).read()).get("row_number"), "yes")

    # Space out the SMTP logins
    if cert_num < cert_total:
        time.sleep(EMAIL_DELAY_SECONDS)
    cert_num += 1

mailer.close()
