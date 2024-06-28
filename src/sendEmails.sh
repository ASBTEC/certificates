#!/usr/bin/env bash

PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/../" &>/dev/null && pwd)"

for signature in $@; do
  pointer="$(echo "${signature}" | tr '[:lower:]' '[:upper:]')_EMAIL"
  email_value="${!pointer}"

  curl -v --url 'smtps://smtp.gmail.com:465' \
    --ssl-reqd \
    --mail-from "${EMAIL_USERNAME}" \
    --mail-rcpt "${email_value}" \
    --mail-rcpt "${EMAIL_USERNAME}" \
    --user "${EMAIL_USERNAME}:${EMAIL_PASSWORD}" \
    -F '=(;type=multipart/mixed' \
    -F "=Hola!

Estàs rebent aquest correu perquè has rebut un certificat per part d'ASBTEC.

Aquest missatge ha estat auto-generat. Per a qualsevol problema contacteu amb informatica@asbtec.cat.

Fins aviat!

A
;type=text/plain" \
    -F "file=@${PROJECT_FOLDER}/out/${signature}.html;type=text/html;encoder=base64" \
    -F '=)' \
    -H "Subject: Actualització de signatures d'email" \
    -H "From: Informàtica ASBTEC <informatica@asbtec.cat>" \
    -H "To: ${EMAIL_USERNAME} <${EMAIL_USERNAME}>"
done