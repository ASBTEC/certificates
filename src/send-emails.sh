#!/usr/bin/env bash

# Usage
# Arg1: Sender
# Arg2: Receiver
# Arg3: App password
# Arg4: cert_id

EMAIL_USERNAME="$1"
email_value="$2"
EMAIL_PASSWORD="$3"
cert_id="$4"
course_name="$5"
partner_name="$6"

print_args()
{
  echo "from: $EMAIL_USERNAME"
  echo "to: $email_value"
  echo "pass: **"
  echo "cert: $cert_id"
  echo "course name: $course_name"
  echo "Partner name: $partner_name"
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
  -F "=Benvolgut/da ${partner_name},

Ens plau informar-te que has rebut el teu certificat de \"${course_name}\" per part d'ASBTEC.

Volem agrair-te la teva participació i esperem que continuïs gaudint i formant part dels nostres actes, cursos i iniciatives. Junts, contribuïm a millorar la biotecnologia al territori.

Aquest missatge ha estat generat automàticament. Per a qualsevol dubte o incidència, pots contactar-nos a secretaria@asbtec.cat.

Si has rebut més d'un correu d'aquest tipus, queda't amb l'últim mail que hagis rebut, doncs serà la versió més actualitzada. Pots borrar la resta.

Fins aviat!

Atentament,
ASBTEC


;type=text/plain" \
    -F "file=@${PROJECT_FOLDER}/pdfs/${cert_id}.pdf;type=text/html;encoder=base64" \
    -F '=)' \
    -H "Subject: Recepció del teu certificat d'ASBTEC" \
    -H "From: Secretaria ASBTEC <secretaria@asbtec.cat>" \
    -H "To: ${EMAIL_USERNAME} <${EMAIL_USERNAME}>"
