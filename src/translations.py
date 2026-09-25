# Static texts of the certificate for each supported language.
# The language of a course is read from the "language" column of the courses_implemented tab.
# Do not use double quotes or backslashes in these strings: the certificate JSON is decoded with unicode_escape.

DEFAULT_LANGUAGE = "cat"

TRANSLATIONS = {
    "cat": {
        "html_lang": "ca-ES",
        "cert_types": {
            "ALUMNE": {"title": "Certificat d'assistència", "action": "per la seva assistència al"},
            "ALUMNE_NOTA": {"title": "Certificat d'assistència", "action": "per la seva assistència al"},
            "PROFE": {"title": "Certificat de reconeixement", "action": "per haver impartit el"},
            "ORGANITZADOR": {"title": "Certificat de coordinació", "action": "per haver organitzat el"},
            "VOLUNTARI": {"title": "Certificat de voluntariat", "action": "per haver fet de voluntari en el"},
        },
        "student_nota_text": ", amb equivalència de {credits} crèdit(s) ECTS amb nota {mark}, acreditat per la {university_name}",
        "awarded_to": "OTORGAT A",
        "id_label": "amb DNI",
        # Followed by the organizers of the course, e.g. ", organitzat per ASBTEC i FEBiotec"
        "organised_by": ", organitzat per",
        "university_preposition": "a la",
        "closing": ", i perquè així consti s’expedeix aquest certificat.",
        "email_subject": "Recepció del teu certificat d'ASBTEC",
        "email_body": (
            "Benvolgut/da {partner_name},\n"
            "\n"
            "Ens plau informar-te que has rebut el teu certificat de \"{course_name}\" per part d'ASBTEC.\n"
            "\n"
            "Volem agrair-te la teva participació i esperem que continuïs gaudint i formant part dels nostres actes, cursos i iniciatives. Junts, contribuïm a millorar la biotecnologia al territori.\n"
            "\n"
            "Aquest missatge ha estat generat automàticament. Per a qualsevol dubte o incidència, pots contactar-nos a certificats@asbtec.cat.\n"
            "\n"
            "Si has rebut més d'un correu d'aquest tipus, queda't amb l'últim mail que hagis rebut, doncs serà la versió més actualitzada. Pots borrar la resta.\n"
            "\n"
            "Fins aviat!\n"
            "\n"
            "Atentament,\n"
            "ASBTEC"
        ),
        "event_types": {"COURSE": "curs", "CONGRESS": "congrés"},
        "sign_as": {
            "SECRETARY": "Secretari d'ASBTEC",
            "PRESIDENT": "President d'ASBTEC",
            "BAC_COORDINATOR_2026": "Coordinador general del BAC Barcelona 2026",
        },
        "dates": {
            "and": "i",
            "day_prefix": ["el dia", "els dies"],
            "next_day_prefix": ["el dia", "els dies"],
            "ordinal_days": False,
            "months": ["de gener", "de febrer", "de març", "d'abril", "de maig", "de juny", "de juliol", "d'agost",
                       "de setembre", "d'octubre", "de novembre", "de desembre"],
            "year": "del {year}",
        },
    },
    "es": {
        "html_lang": "es-ES",
        "cert_types": {
            "ALUMNE": {"title": "Certificado de asistencia", "action": "por su asistencia al"},
            "ALUMNE_NOTA": {"title": "Certificado de asistencia", "action": "por su asistencia al"},
            "PROFE": {"title": "Certificado de reconocimiento", "action": "por haber impartido el"},
            "ORGANITZADOR": {"title": "Certificado de coordinación", "action": "por haber organizado el"},
            "VOLUNTARI": {"title": "Certificado de voluntariado", "action": "por haber hecho de voluntario en el"},
        },
        "student_nota_text": ", con equivalencia de {credits} crédito(s) ECTS con nota {mark}, acreditado por la {university_name}",
        "awarded_to": "OTORGADO A",
        "id_label": "con DNI",
        "organised_by": ", organizado por",
        # "y" becomes "e" before a word starting with an i sound (i-, hi-, but not hia-, hie-, hio-, hiu-)
        "and_before_i": "e",
        "university_preposition": "en la",
        "closing": ", y para que así conste se expide el presente certificado.",
        "email_subject": "Recepción de tu certificado de ASBTEC",
        "email_body": (
            "Estimado/a {partner_name},\n"
            "\n"
            "Nos complace informarte de que has recibido tu certificado de \"{course_name}\" por parte de ASBTEC.\n"
            "\n"
            "Queremos agradecerte tu participación y esperamos que sigas disfrutando y formando parte de nuestros actos, cursos e iniciativas. Juntos, contribuimos a mejorar la biotecnología en el territorio.\n"
            "\n"
            "Este mensaje ha sido generado automáticamente. Para cualquier duda o incidencia, puedes contactarnos en certificats@asbtec.cat.\n"
            "\n"
            "Si has recibido más de un correo de este tipo, quédate con el último que hayas recibido, ya que será la versión más actualizada. Puedes borrar el resto.\n"
            "\n"
            "¡Hasta pronto!\n"
            "\n"
            "Atentamente,\n"
            "ASBTEC"
        ),
        "event_types": {"COURSE": "curso", "CONGRESS": "congreso"},
        "sign_as": {
            "SECRETARY": "Secretario de ASBTEC",
            "PRESIDENT": "Presidente de ASBTEC",
            "BAC_COORDINATOR_2026": "Coordinador general del BAC Barcelona 2026",
        },
        "dates": {
            "and": "y",
            "day_prefix": ["el día", "los días"],
            "next_day_prefix": ["el día", "los días"],
            "ordinal_days": False,
            "months": ["de enero", "de febrero", "de marzo", "de abril", "de mayo", "de junio", "de julio",
                       "de agosto", "de septiembre", "de octubre", "de noviembre", "de diciembre"],
            "year": "de {year}",
        },
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
        "organised_by": ", organised by",
        "university_preposition": "at the",
        "closing": ", and for the record, this certificate is hereby issued.",
        "email_subject": "Your ASBTEC certificate",
        "email_body": (
            "Dear {partner_name},\n"
            "\n"
            "We are pleased to inform you that you have received your certificate for \"{course_name}\" from ASBTEC.\n"
            "\n"
            "We would like to thank you for your participation and we hope you keep enjoying and taking part in our events, courses and initiatives. Together, we contribute to improving biotechnology in our region.\n"
            "\n"
            "This message has been generated automatically. For any questions or issues, you can contact us at certificats@asbtec.cat.\n"
            "\n"
            "If you have received more than one email of this kind, please keep the most recent one, as it is the most up-to-date version. You can delete the rest.\n"
            "\n"
            "See you soon!\n"
            "\n"
            "Kind regards,\n"
            "ASBTEC"
        ),
        "event_types": {"COURSE": "course", "CONGRESS": "congress"},
        "sign_as": {
            "SECRETARY": "Secretary of ASBTEC",
            "PRESIDENT": "President of ASBTEC",
            "BAC_COORDINATOR_2026": "General Coordinator of the BAC Barcelona 2026",
        },
        "dates": {
            "and": "and",
            "day_prefix": ["on the", "on the"],
            "next_day_prefix": ["the", "the"],
            "ordinal_days": True,
            "months": ["of January", "of February", "of March", "of April", "of May", "of June", "of July",
                       "of August", "of September", "of October", "of November", "of December"],
            "year": "{year}",
        },
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


# Joins items as "a, b and c" using the conjunction of the language.
def join_list(items, conjunction):
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " " + conjunction + " " + items[-1]


# English ordinal of a day of the month: 1st, 2nd, 3rd, 4th, 11th, 12th, 13th, 21st...
def english_ordinal(day):
    if 11 <= day % 100 <= 13:
        return str(day) + "th"
    return str(day) + {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


# Builds the "organised by" text of a certificate from the names of its organizers, in order, e.g.
# ", organitzat per ASBTEC", ", organitzat per ASBTEC i FEBiotec", ", organised by X, Y, ASBTEC and FEBiotec".
def format_organisers(names, code):
    texts = get_translation(code)
    if not names:
        raise ValueError("Cannot build the organised by text without organizers")
    conjunction = texts["dates"]["and"]
    last = names[-1].lower()
    if "and_before_i" in texts and (last.startswith(("i", "í")) or (last.startswith(("hi", "hí")) and last[2:3] not in ("a", "e", "o", "u"))):
        conjunction = texts["and_before_i"]
    return texts["organised_by"] + " " + join_list(names, conjunction)


# Builds the date phrase of a certificate from its days (datetime.date), e.g.
# "els dies 28 i 29 de novembre i els dies 2 i 5 de desembre del 2024".
def format_days(days, code):
    texts = get_translation(code)["dates"]
    days = sorted(set(days))
    if not days:
        raise ValueError("Cannot build a date phrase without days")

    # Group days by year and then by month, keeping chronological order
    years = {}
    for day in days:
        years.setdefault(day.year, {}).setdefault(day.month, []).append(day.day)

    year_parts = []
    first_segment = True
    for year, months in years.items():
        month_parts = []
        for month, month_days in months.items():
            day_texts = [english_ordinal(d) if texts["ordinal_days"] else str(d) for d in month_days]
            prefix = texts["day_prefix"] if first_segment else texts["next_day_prefix"]
            segment = (prefix[0 if len(month_days) == 1 else 1] + " " + join_list(day_texts, texts["and"]) + " " +
                       texts["months"][month - 1])
            first_segment = False
            month_parts.append(segment)
        year_parts.append(join_list(month_parts, texts["and"]) + " " + texts["year"].format(year=year))

    return join_list(year_parts, texts["and"])
