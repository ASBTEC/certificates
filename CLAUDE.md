# CLAUDE.md

## Project overview

Generates ASBTEC course certificates:

1. `src/certificate-generator.py` reads the Google Spreadsheet (`_certificate_history`, `courses_implemented`,
   `university`, `courses` tabs) and writes one JSON per certificate into `data/`.
2. `src/build-htmls.js` fills `templates/template.html` (Handlebars) with each JSON → `certs/<id>.html`.
3. `src/build-pdfs.js` renders each HTML to PNG with Puppeteer, crops it and converts it to a single-page PDF in `pdfs/`.
4. The Python script uploads JSON/PDF to Drive, sends the email (`src/send-emails.sh`) and updates the spreadsheet.

Do not run the software (it reads/writes the real spreadsheet, Drive and sends emails).

The `bac-certs` branch adapts the generator for the BAC (Biotechnology Annual Congress). BAC-specific behaviour must
be kept as **options** inside the software, not as a fork.

## Plan: certificate language option

Goal: each course in `courses_implemented` chooses the language of its certificates.

### Spreadsheet contract

- New column **L** (`language`) in the `courses_implemented` tab, right after `event_type` (K).
- Accepted values: `ca` (Catalan), `es` (Spanish), `en` (English). Case-insensitive, surrounding spaces ignored.
- Empty cell / missing column → `ca` (current behaviour, so existing courses keep working).
- Any other value → the script fails with an explicit error before generating anything for that row.
- `text_date` (column H) is free text written per course, so it must already be written in the course language.

### Implementation steps

1. **`src/translations.py`** (new): a `TRANSLATIONS` dict keyed by language code holding every static text of the
   certificate: html `lang` attribute, "awarded to", ID label, per-`cert_type` title and action text, "organised by
   ASBTEC", preposition before the university, the credits/mark sentence, the closing sentence and the signers'
   position. Plus a `DEFAULT_LANGUAGE = "ca"` and a `get_translation(code)` helper that normalises/validates the code.
   - Avoid double quotes and backslashes in the strings: `save_cert_data` decodes the JSON with `unicode_escape`.
2. **`src/certificate-generator.py`**:
   - Read `courses_implemented` up to column `L` instead of `K`.
   - In `parse_certificate_data`, read the language from `course_metadata[11]` (guarding against the shorter rows the
     Sheets API returns when trailing cells are empty), store `language` in the JSON and take every text
     (`cert_type_text`, `action_text`, `student_nota_text`) from the translation. Expose the remaining static texts
     under an `i18n` object in the JSON.
3. **`templates/template.html`**: replace every hard-coded Catalan text with Handlebars placeholders
   (`{{i18n.*}}`, `{{cert_type_text}}`, `{{action_text}}`), and set `<html lang="{{i18n.html_lang}}">`.
4. **`src/send-emails.sh`**: takes the language as 8th argument (default `ca`) and selects the email subject and body
   (ca/es/en) with a `case`; unknown languages exit with an error. `certificate-generator.py` passes the `language`
   field of the certificate JSON. Do not use semicolons in the bodies: `curl -F` parses them.
5. Docs: document the new column in the README.

### Out of scope

- Signers' names are still hard-coded in the template.
