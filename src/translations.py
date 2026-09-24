# Static texts of the certificate for each supported language.
# The language of a course is read from the "language" column of the courses_implemented tab.
# Do not use double quotes or backslashes in these strings: the certificate JSON is decoded with unicode_escape.

DEFAULT_LANGUAGE = "ca"

TRANSLATIONS = {
    "ca": {
        "html_lang": "ca-ES",
        "cert_types": {
            "ALUMNE": {"title": "Certificat d'assistència", "action": "per la seva assistència al"},
            "ALUMNE_NOTA": {"title": "Certificat d'assistència", "action": "per la seva assistència al"},
            "PROFE": {"title": "Certificat de reconeixement", "action": "per haver impartit el"},
            "ORGANITZADOR": {"title": "Certificat de coordinació", "action": "per haver organitzat el"},
            "VOLUNTARI": {"title": "Certificat de voluntariat", "action": "per haver participat en el"},
        },
        "student_nota_text": ", amb equivalència de {credits} crèdit(s) ECTS amb nota {mark}, acreditat per la {university_name}",
        "awarded_to": "OTORGAT A",
        "id_label": "amb DNI",
        "organised_by": ", organitzat per ASBTEC",
        "university_preposition": "a la",
        "closing": ", i perquè així consti s’expedeix aquest certificat.",
        "signer_position": "Coordinador general del BAC",
    },
    "es": {
        "html_lang": "es-ES",
        "cert_types": {
            "ALUMNE": {"title": "Certificado de asistencia", "action": "por su asistencia al"},
            "ALUMNE_NOTA": {"title": "Certificado de asistencia", "action": "por su asistencia al"},
            "PROFE": {"title": "Certificado de reconocimiento", "action": "por haber impartido el"},
            "ORGANITZADOR": {"title": "Certificado de coordinación", "action": "por haber organizado el"},
            "VOLUNTARI": {"title": "Certificado de voluntariado", "action": "por haber participado en el"},
        },
        "student_nota_text": ", con equivalencia de {credits} crédito(s) ECTS con nota {mark}, acreditado por la {university_name}",
        "awarded_to": "OTORGADO A",
        "id_label": "con DNI",
        "organised_by": ", organizado por ASBTEC",
        "university_preposition": "en la",
        "closing": ", y para que así conste se expide el presente certificado.",
        "signer_position": "Coordinador general del BAC",
    },
    "en": {
        "html_lang": "en-GB",
        "cert_types": {
            "ALUMNE": {"title": "Certificate of attendance", "action": "for attending the"},
            "ALUMNE_NOTA": {"title": "Certificate of attendance", "action": "for attending the"},
            "PROFE": {"title": "Certificate of recognition", "action": "for having taught the"},
            "ORGANITZADOR": {"title": "Certificate of coordination", "action": "for having organised the"},
            "VOLUNTARI": {"title": "Certificate of volunteering", "action": "for having volunteered at the"},
        },
        "student_nota_text": ", equivalent to {credits} ECTS credit(s) with a mark of {mark}, accredited by the {university_name}",
        "awarded_to": "AWARDED TO",
        "id_label": "with ID",
        "organised_by": ", organised by ASBTEC",
        "university_preposition": "at the",
        "closing": ", and for the record, this certificate is hereby issued.",
        "signer_position": "General Coordinator of the BAC",
    },
}


# Normalizes a language code read from the spreadsheet. Empty values fall back to the default language.
def normalize_language(code):
    code = (code or "").strip().lower()
    if code == "":
        return DEFAULT_LANGUAGE
    if code not in TRANSLATIONS:
        raise ValueError("Unsupported language \"" + code + "\". Supported languages: " + ", ".join(TRANSLATIONS.keys()))
    return code


def get_translation(code):
    return TRANSLATIONS[normalize_language(code)]
