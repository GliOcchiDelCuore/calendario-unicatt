import datetime
import requests

# URL dell'API Unicatt
API_URL = "https://secure.unicatt.it/didatticaweb2/ps/lezioni/"

# Parametri del tuo corso (Medicine and Surgery, 3° Anno)
PAYLOAD = {
    "anno": 2026,
    "tipo": "CDL",
    "codFacolta": "75012",
    "codCdl": "0H0B",
    "annoDiCorso": 3,
}


def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Inviamo una richiesta POST inviando i parametri in JSON
    res = requests.post(API_URL, json=PAYLOAD, headers=headers)

    # Se POST fallisce con 405, tentiamo la richiesta in formato Form Data
    if res.status_code == 405:
        res = requests.post(API_URL, data=PAYLOAD, headers=headers)

    res.raise_for_status()

    data = res.json().get("lezioniCalendario", {})

    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Unicatt//IT",
        "X-WR-CALNAME:Lezioni Unicatt - Medicine and Surgery 3° Anno",
        "X-WR-TIMEZONE:Europe/Rome",
    ]

    for data_str, lezioni in data.items():
        day, month, year = map(int, data_str.split("/"))
        for l in lezioni:
            if l.get("flagSospensione"):
                continue

            h_s, m_s = map(int, l["oraInizio"].split(":"))
            h_e, m_e = map(int, l["oraFine"].split(":"))

            start = datetime.datetime(year, month, day, h_s, m_s).strftime(
                "%Y%m%dT%H%M%S"
            )
            end = datetime.datetime(year, month, day, h_e, m_e).strftime(
                "%Y%m%dT%H%M%S"
            )

            materia = l.get("descrizioneInsegnamento", "Lezione")
            aula = l.get("descrizioneAula", "")
            edificio = l.get("descrizioneEdificio", "")
            docente = l.get("docente", "")
            uid = f"unicatt-{l.get('idCalendarioAula')}@sync"

            location_str = (
                f"Aula {aula} - {edificio}" if edificio else f"Aula {aula}"
            )

            ics.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTART;TZID=Europe/Rome:{start}",
                    f"DTEND;TZID=Europe/Rome:{end}",
                    f"SUMMARY:{materia}",
                    f"LOCATION:{location_str}",
                    f"DESCRIPTION:Docente: {docente}",
                    "END:VEVENT",
                ]
            )

    ics.append("END:VCALENDAR")

    with open("lezioni.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(ics))


if __name__ == "__main__":
    main()
