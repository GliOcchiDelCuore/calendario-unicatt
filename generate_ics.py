
import datetime
import hashlib
import os
import requests

from zoneinfo import ZoneInfo

# API UniCatt
API_URL = "https://secure.unicatt.it/didatticaweb2/ps/lezioni/"

# Medicine and Surgery - III anno - Roma
PAYLOAD = {
    "codiceSede": "RM",
    "annoAccademico": "2026",
    "codiceFacolta": "75012",
    "codiceCorsoDiLaurea": "0H0B",
    "annoDiCorso": "3",
}

ROME = ZoneInfo("Europe/Rome")
UTC = datetime.timezone.utc


def ics_escape(value):
    """Escape dei caratteri speciali previsti dal formato ICS."""
    value = str(value or "")
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def fold_line(line):
    """Rispetta il limite RFC5545 di 75 ottetti per riga."""
    result = []
    current = ""
    current_bytes = 0

    for char in line:
        char_bytes = len(char.encode("utf-8"))

        if current_bytes + char_bytes > 75:
            result.append(current)
            current = " " + char
            current_bytes = 1 + char_bytes
        else:
            current += char
            current_bytes += char_bytes

    result.append(current)
    return "\r\n".join(result)


def is_suspended(value):
    return str(value).strip().lower() in {
        "1", "true", "s", "si", "sì", "yes", "y"
    }


def utc_ics(date_str, time_str):
    day, month, year = map(int, date_str.split("/"))
    hour, minute = map(int, time_str.split(":"))

    local_dt = datetime.datetime(
        year, month, day, hour, minute, tzinfo=ROME
    )
    return local_dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def main():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://roma.unicatt.it",
        "Referer": "https://roma.unicatt.it/",
    }

    print("Recupero lezioni da UniCatt...")

    response = requests.post(
        API_URL,
        json=PAYLOAD,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    data = result.get("lezioniCalendario")

    if not isinstance(data, dict):
        raise ValueError(
            "Risposta API inattesa: manca lezioniCalendario."
        )

    now = datetime.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UniCatt//Calendario Medicine and Surgery//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Lezioni UniCatt - Medicine and Surgery III",
    ]

    event_count = 0

    for date_str, lessons in data.items():
        for lesson in lessons:
            if is_suspended(lesson.get("flagSospensione", False)):
                continue

            start = utc_ics(date_str, lesson["oraInizio"])
            end = utc_ics(date_str, lesson["oraFine"])

            materia = lesson.get("descrizioneInsegnamento") or "Lezione"
            aula = lesson.get("descrizioneAula") or ""
            edificio = lesson.get("descrizioneEdificio") or ""
            docente = lesson.get("docente") or ""
            piano = lesson.get("pianoAula") or ""
            note = lesson.get("note") or ""
            motivo = lesson.get("motivo") or ""

            location = " - ".join(
                part for part in [
                    f"Aula {aula}" if aula else "",
                    edificio,
                    f"Piano {piano}" if piano else "",
                ] if part
            )

            description = [
                f"Docente: {docente}" if docente else "",
                f"Note: {note}" if note else "",
                f"Motivo: {motivo}" if motivo else "",
            ]
            description = "\\n".join(
                part for part in description if part
            )

            event_id = lesson.get("idCalendarioAula")

            if event_id is None:
                fallback = (
                    f"{lesson.get('idLezione', '')}-"
                    f"{date_str}-{lesson['oraInizio']}"
                )
                event_id = hashlib.sha256(
                    fallback.encode("utf-8")
                ).hexdigest()

            uid = f"unicatt-{event_id}@calendar.unicatt"

            ics.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART:{start}",
                f"DTEND:{end}",
                f"SUMMARY:{ics_escape(materia)}",
                f"LOCATION:{ics_escape(location)}",
                f"DESCRIPTION:{ics_escape(description)}",
                "END:VEVENT",
            ])

            event_count += 1

    ics.append("END:VCALENDAR")

    os.makedirs("public", exist_ok=True)

    with open("public/lezioni.ics", "w", encoding="utf-8", newline="") as file:
        file.write("\r\n".join(fold_line(line) for line in ics))
        file.write("\r\n")

    print(f"Calendario generato: {event_count} eventi.")
    print("File: public/lezioni.ics")


if __name__ == "__main__":
    main()
