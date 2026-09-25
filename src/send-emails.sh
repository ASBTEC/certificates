#!/usr/bin/env bash

# Usage
# Arg1: Sender
# Arg2: Receiver
# Arg3: App password
# Arg4: cert_id
# Arg5: course name
# Arg6: partner name
# Arg7: from address
# Arg8: language (cat, es, en). Defaults to cat

EMAIL_USERNAME="$1"
email_value="$2"
EMAIL_PASSWORD="$3"
cert_id="$4"
course_name="$5"
partner_name="$6"
GMAIL_FROM="$7"
language="${8:-cat}"

print_args()
{
  echo "from: $EMAIL_USERNAME"
  echo "to: $email_value"
  echo "pass: **"
  echo "cert: $cert_id"
  echo "course name: $course_name"
  echo "Partner name: $partner_name"
  echo "Language: $language"
}

PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/../" &>/dev/null && pwd)"


# Email subject and body in the language of the course. Do not use semicolons in the body: curl -F parses them.
case "${language}" in
  cat)
    email_subject="Recepció del teu certificat d'ASBTEC"
    email_body="Benvolgut/da ${partner_name},

Ens plau informar-te que has rebut el teu certificat de \"${course_name}\" per part d'ASBTEC.

Volem agrair-te la teva participació i esperem que continuïs gaudint i formant part dels nostres actes, cursos i iniciatives. Junts, contribuïm a millorar la biotecnologia al territori.

Aquest missatge ha estat generat automàticament. Per a qualsevol dubte o incidència, pots contactar-nos a certificats@asbtec.cat.

Si has rebut més d'un correu d'aquest tipus, queda't amb l'últim mail que hagis rebut, doncs serà la versió més actualitzada. Pots borrar la resta.

Fins aviat!

Atentament,
ASBTEC"
    ;;
  es)
    email_subject="Recepción de tu certificado de ASBTEC"
    email_body="Estimado/a ${partner_name},

Nos complace informarte de que has recibido tu certificado de \"${course_name}\" por parte de ASBTEC.

Queremos agradecerte tu participación y esperamos que sigas disfrutando y formando parte de nuestros actos, cursos e iniciativas. Juntos, contribuimos a mejorar la biotecnología en el territorio.

Este mensaje ha sido generado automáticamente. Para cualquier duda o incidencia, puedes contactarnos en certificats@asbtec.cat.

Si has recibido más de un correo de este tipo, quédate con el último que hayas recibido, ya que será la versión más actualizada. Puedes borrar el resto.

¡Hasta pronto!

Atentamente,
ASBTEC"
    ;;
  en)
    email_subject="Your ASBTEC certificate"
    email_body="Dear ${partner_name},

We are pleased to inform you that you have received your certificate for \"${course_name}\" from ASBTEC.

We would like to thank you for your participation and we hope you keep enjoying and taking part in our events, courses and initiatives. Together, we contribute to improving biotechnology in our region.

This message has been generated automatically. For any questions or issues, you can contact us at certificats@asbtec.cat.

If you have received more than one email of this kind, please keep the most recent one, as it is the most up-to-date version. You can delete the rest.

See you soon!

Kind regards,
ASBTEC"
    ;;
  *)
    echo "Unsupported language: ${language}" >&2
    exit 1
    ;;
esac

curl -v --url 'smtps://smtp.gmail.com:465' \
  --ssl-reqd \
  --mail-from "${GMAIL_FROM}" \
  --mail-rcpt "${email_value}" \
  --mail-rcpt "certificats@asbtec.cat" \
  --user "${EMAIL_USERNAME}:${EMAIL_PASSWORD}" \
  -F '=(;type=multipart/mixed' \
  -F "=${email_body}
;type=text/plain" \
    -F "file=@${PROJECT_FOLDER}/pdfs/${cert_id}.pdf;type=text/html;encoder=base64" \
    -F '=)' \
    -H "Subject: ${email_subject}" \
    -H "From: Certificats ASBTEC <certificats@asbtec.cat>" \
    -H "To: ${partner_name} <${email_value}>"
