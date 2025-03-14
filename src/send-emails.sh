#!/usr/bin/env bash

# Usage
# Arg1: Sender
# Arg2: Receiver
# Arg3: App password
# Arg4: cert_id

EMAIL_USERNAME=$1
email_value=$2
EMAIL_PASSWORD="$3"
cert_id="$4"
course_name="$5"

print_args()
{
  echo "from: $EMAIL_USERNAME"
  echo "to: $email_value"
  echo "pass: **"
  echo "cert: $cert_id"
  echo "course name: $course_name"
}

PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/../" &>/dev/null && pwd)"


curl -v --url 'smtps://smtp.gmail.com:465' \
  --ssl-reqd \
  --mail-from "${EMAIL_USERNAME}" \
  --mail-rcpt "${email_value}" \
  --mail-rcpt "${EMAIL_USERNAME}" \
  --mail-rcpt "informatica@asbtec.cat" \
  --user "${EMAIL_USERNAME}:${EMAIL_PASSWORD}" \
  -F '=(;type=multipart/mixed' \
  -F "=Hola!

Estàs rebent aquest correu perquè has rebut un certificat per part d'ASBTEC.

Aquest missatge ha estat auto-generat. Per a qualsevol problema contacteu amb secretaria@asbtec.cat.

Fins aviat!

A
;type=text/plain" \
    -F "file=@${PROJECT_FOLDER}/pdfs/${cert_id}.pdf;type=text/html;encoder=base64" \
    -F '=)' \
    -H "Subject: Certificat de \"$course_name\" d'ASBTEC" \
    -H "From: Secretaria ASBTEC <secretaria@asbtec.cat>" \
    -H "To: ${EMAIL_USERNAME} <${EMAIL_USERNAME}>"
