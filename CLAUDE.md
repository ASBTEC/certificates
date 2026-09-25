# CLAUDE.md

## Project overview

Generates ASBTEC course certificates:

1. `src/certificate-generator.py` reads the Google Spreadsheet (`_certificate_history`, `courses_implemented`,
   `university`, `courses` tabs) and writes one JSON per certificate into `data/`.
2. `src/build-htmls.js` fills `templates/template.html` (Handlebars) with each JSON → `certs/<id>.html`.
3. `src/build-pdfs.js` renders each HTML to PNG with Puppeteer, crops it and converts it to a single-page PDF in `pdfs/`.
4. For each certificate the Python script uploads the PDF to Drive into a subfolder of the "sent" folder named after the course id (created if missing), writes its link in `url_cert`, tries to send the email (`src/mailer.py`) and, only if it was sent, writes "yes" in `sent`. The JSON stays local. All Google API requests (Drive and spreadsheet reads/writes) retry with exponential backoff on rate limit / server errors (`GOOGLE_API_RETRIES`). A PDF whose name already exists in the target folder overwrites that file (same id and link, previous content kept in the Drive version history).

Do not run the software (it reads/writes the real spreadsheet, Drive and sends emails).

The `bac-certs` branch adapts the generator for the BAC (Biotechnology Annual Congress). BAC-specific behaviour must
be kept as **options** inside the software, not as a fork.

## Plan: certificate language option

Goal: each course in `courses_implemented` chooses the language of its certificates.

### Spreadsheet contract

- New column `language` in the `courses_implemented` tab (found by header name, see the dates plan below).
- Accepted values: `cat` (Catalan), `es` (Spanish), `en` (English). Case-insensitive, surrounding spaces ignored.
- Empty cell / missing column → `cat` (current behaviour, so existing courses keep working).
- Any other value → the script fails with an explicit error before generating anything for that row.
- The date phrase is generated from the dates tabs in the course language (see the dates plan below).

### Implementation steps

1. **`src/translations.py`** (new): a `TRANSLATIONS` dict keyed by language code holding every static text of the
   certificate: html `lang` attribute, "awarded to", ID label, per-`cert_type` title and action text, "organised by
   ASBTEC", preposition before the university, the credits/mark sentence, the closing sentence and the signers'
   position. Plus a `DEFAULT_LANGUAGE = "cat"` and a `get_translation(code)` helper that normalises/validates the code.
   - Avoid double quotes and backslashes in the strings: `save_cert_data` decodes the JSON with `unicode_escape`.
2. **`src/certificate-generator.py`**:
   - Read `courses_implemented` up to column `L` instead of `K`.
   - In `parse_certificate_data`, read the language from `course_metadata[11]` (guarding against the shorter rows the
     Sheets API returns when trailing cells are empty), store `language` in the JSON and take every text
     (`cert_type_text`, `action_text`, `student_nota_text`) from the translation. Expose the remaining static texts
     under an `i18n` object in the JSON.
3. **`templates/template.html`**: replace every hard-coded Catalan text with Handlebars placeholders
   (`{{i18n.*}}`, `{{cert_type_text}}`, `{{action_text}}`), and set `<html lang="{{i18n.html_lang}}">`.
4. **Email**: the subject and body of each language live in `translations.py` (`email_subject`, `email_body` with
   `{partner_name}` and `{course_name}`); `mailer.py` builds the email in the language of the certificate.
5. Docs: document the new column in the README.

### Out of scope

- Signers' names are still hard-coded in the template.

## Plan: dates built from days instead of `date_text`

Goal: remove the free-text `date_text` column of `courses_implemented` and generate the date phrase of the certificate
from the individual days of the course, in the language of the course.

### Spreadsheet contract

Row 1 of every tab is a header row. Columns are looked up **by header name**, so their order does not matter.

- `courses_implemented`: `date_text` is deleted. Columns used: `id`, `university`, `course`, `credits`,
  `additional_logo_file`, `event_type`, `language`.
- `dates_intermediate` (N to N course ↔ date): `course_id` (id of `courses_implemented`), `date_id`.
- `dates`: `id`.
- `days_intermediate` (N to N date ↔ day): `date_id`, `day_id`.
- `days`: `id`, `date` (a single day, `DD/MM/YYYY`).

Join: `courses_implemented.id → dates_intermediate.course_id → date_id → dates.id → days_intermediate.date_id →
day_id → days.id → date`. The days of a course are deduplicated and sorted.

### Date phrase

Days are grouped by year and month, then written as a list per month, e.g.:

- cat: `el dia 17 de febrer del 2025`, `els dies 17, 18, 19 i 20 de febrer del 2025`,
  `els dies 28 i 29 de novembre i els dies 2 i 5 de desembre del 2024`
  (`d'` before `abril`, `agost`, `octubre`).
- es: `los días 28 y 29 de noviembre y los días 2 y 5 de diciembre de 2024`.
- en: `on the 28th and 29th of November and the 2nd and 5th of December 2024` (ordinal days, `the` before later months).
- Several years: each year closes its own group, e.g. `els dies 30 i 31 de desembre del 2024 i el dia 2 de gener del 2025`.

The phrase is stored in the `text_date` field of the certificate JSON, so the template does not change.

### Implementation steps

1. `certificate-generator.py`: new `read_table()` that reads a whole tab and returns its rows as dicts keyed by header,
   validating that the required headers exist and skipping empty rows. Use it for `courses_implemented` (replacing
   positional indices in `parse_certificate_data`) and the four new tabs.
2. `certificate-generator.py`: `build_course_days()` joins the four tabs into `{course_id: [sorted dates]}`, failing
   with explicit errors on dangling ids or badly formatted dates. A course without days is an error.
3. `translations.py`: per-language month names, conjunction, day prefixes and year format, plus `format_days(days,
   language)` that builds the phrase.
4. README: document the new tabs.

## Plan: dynamic signatures

Goal: the two signers of a certificate come from the course, and their position text is translated.

### Spreadsheet contract

- `courses_implemented`: new columns `signature1` (left signer) and `signature2` (right signer), each holding an `id`
  of the `signatures` tab.
- `signatures`: `id`, `sign_as`, `signature_image`, `name` (found by header name).
  - `sign_as` enum: `SECRETARY` (secretary of ASBTEC), `PRESIDENT` (president of ASBTEC), `BAC_COORDINATOR_2026`
    (general coordinator of the BAC Barcelona 2026). Its text is translated per course language.
  - `signature_image`: file name inside `templates/` (e.g. `signature_jacastro.png`) or a URL, used as is without
    validation.
  - `name`: full name printed under the signature.

### Implementation steps

1. `translations.py`: replace `signer_position` with a `sign_as` dict (enum → text) per language.
2. `certificate-generator.py`: read the `signatures` tab with `read_table()`; in `parse_certificate_data` resolve
   `signature1`/`signature2` into `{name, position, image}` objects in the JSON. Fail with an explicit error on an
   unknown signature id or unknown `sign_as`.
3. `template.html`: use `{{signature1.*}}` / `{{signature2.*}}` for image, name and position. Both signature slots use
   `object-fit: contain` anchored at the bottom center, so any image fits without cropping.
4. README: document the new columns and tab.

## Plan: every column referenced by header name

Goal: no code refers to a spreadsheet column by letter or position, so columns can be moved or removed (e.g. the
`date_text` column of `courses_implemented`).

- `read_table()` reads a whole tab by header; `read_table_rows()` reads row 1 plus the row range passed as arguments
  (`_certificate_history`) and keeps each row's real spreadsheet row number. `column_letter()` turns a header name into
  the letter used when writing.
- `_certificate_history` columns used: `id`, `name`, `email`, `NIF`, `cert_type`, `mark`, `assisted` (rows with `no`
  are skipped), `ready` (rows with `no` are skipped), `sent` (written `yes` after the email is sent), `url_cert` (Drive link of the PDF) and `commit_SHA_ID`
  (SHA of the commit that rendered the certificate, `-dirty` suffix if tracked files had uncommitted changes).
  `created` is no longer written and can be deleted.
- `university`: `id`, `name`, `logo_file` (university logo: file name inside `templates/` or URL, used as is; empty → `logo_empty.png`). `courses`: `id`, `name`.

## Plan: additional logo as a file name

- `courses_implemented.additional_logo_file` (renamed from `Additional_logo_suffix`) holds the full file name of a logo inside
  `templates/` (e.g. `logo_bac.png`, `logo_hipra.jpg`) or a public image URL, used as is by the template
  (`{{additional_logo}}`). No validation: a wrong value renders an empty slot.
- Empty cell (or the legacy `-`) → `logo_empty.png`, a transparent 1x1 placeholder, so the slot looks empty.
- Template assets (images, fonts, `style.css`) live in `templates/` next to `template.html`, which sets
  `<base href="../templates/">` so the rendered HTML in `certs/` resolves bare file names there.

## Plan: event type before the course name

- `courses_implemented.event_type` enum: `COURSE`, `CONGRESS`. Translated per language (`event_types` in
  `translations.py`: curs/congrés, curso/congreso, course/congress) into the `course_type` field, which the template
  writes just before the course name: `per haver participat en el curs "Nom del curs"`.
- Any other value, including an empty cell, stops the generation with an error.

## Plan: run modes

`certificate-generator.py FIRST_ROW LAST_ROW [--dev|--develop | --test | --production|--prod] [-f|--force]`

- `--dev` (default): email sent to `secrets/DEV_EMAIL`. No Drive upload, nothing written to the spreadsheet.
- `--test`: email sent to `secrets/TEST_EMAIL`. No Drive upload, nothing written to the spreadsheet.
- `--production`: write `commit_SHA_ID`, upload to Drive, write `url_cert`, email the address in the spreadsheet,
  write `sent`. Asks for a typed `yes` confirmation (showing the certificate count and commit) unless `--force`.
- `certificats@asbtec.cat` always receives a copy (`mailer.py`).

## Email sending (`src/mailer.py`)

- Python `smtplib` over SSL to `smtp.gmail.com:465`, replacing the former `send-emails.sh` + `curl`. One SMTP
  connection and login for the whole run: one login per email made Gmail answer `454 4.7.0 Too many login attempts`.
- Envelope sender `secrets/GMAIL_FROM.txt`; header `From: Certificats ASBTEC <certificats@asbtec.cat>`; header `To` with
  the recipient's name; recipients = the mode's address + `certificats@asbtec.cat`. Plain-text body in the course
  language, PDF attached as `application/pdf` named `<cert_id>.pdf`.
- Temporary failures (SMTP 4xx, network errors, server disconnection) reconnect and retry with exponential backoff
  (`EMAIL_RETRY_BASE_SECONDS * 2^n` + jitter, `EMAIL_RETRIES` times). SMTP 5xx (e.g. wrong password, unknown recipient)
  is not retried. `EMAIL_DELAY_SECONDS` pause between emails.
- Output of the old `send-emails.sh` (`curl -v`) printed the base64 app password: never paste old logs.

## Plan: organizers of a course

- `organizers`: `id`, `name` (entity name, not translated). `organizers_intermediate` (N to N course ↔ organizer):
  `course_id` (id of `courses_implemented`), `organizer_id`.
- `build_course_organisers()` joins them into `{course_id: [names]}` in the order of the `organizers_intermediate`
  rows, skipping repeated organizers. Unknown `organizer_id` or a course without organizers stops the generation.
- `format_organisers()` (`translations.py`) builds the `organised_by` field: translated prefix (`organised_by`:
  ", organitzat per" / ", organizado por" / ", organised by") + names joined with the language's list rule (`, ` and
  i / y / and; Spanish `y` → `e` before an i sound). The template writes `{{organised_by}}`.
