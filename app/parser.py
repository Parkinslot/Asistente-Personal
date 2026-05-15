import re
from datetime import datetime, timedelta


DAYS = {
    "lunes": "lunes",
    "martes": "martes",
    "miercoles": "miercoles",
    "miércoles": "miercoles",
    "jueves": "jueves",
    "viernes": "viernes",
    "sabado": "sabado",
    "sábado": "sabado",
    "domingo": "domingo",
}


def remove_phrase(text: str, phrase: str) -> str:
    pattern = r"\b" + re.escape(phrase) + r"\b"
    return re.sub(pattern, " ", text, flags=re.IGNORECASE)


def extract_remind_before(text: str) -> int:
    lower = text.lower()

    patterns = [
        r"(avisame|avísame|avisar|recordame|recuérdame|recordar)\s+(\d+)\s*(min|minuto|minutos|hora|horas)\s+antes",
        r"(\d+)\s*(min|minuto|minutos|hora|horas)\s+antes",
        r"avisame\s+antes\s+(\d+)\s*(min|minuto|minutos|hora|horas)",
        r"recordame\s+antes\s+(\d+)\s*(min|minuto|minutos|hora|horas)",
    ]

    for pattern in patterns:
        match = re.search(pattern, lower)

        if match:
            groups = match.groups()

            number = None
            unit = None

            for g in groups:
                if g and g.isdigit():
                    number = int(g)
                elif g in ["min", "minuto", "minutos", "hora", "horas"]:
                    unit = g

            if number is not None and unit is not None:
                if unit in ["hora", "horas"]:
                    return number * 60

                return number

    return 60


def clean_title(text: str) -> str:
    clean = text.lower().strip()

    clean = re.sub(
        r"(avisame|avísame|avisar|recordame|recuérdame|recordar)\s+\d+\s*(min|minuto|minutos|hora|horas)\s+antes",
        " ",
        clean,
    )

    clean = re.sub(
        r"\d+\s*(min|minuto|minutos|hora|horas)\s+antes",
        " ",
        clean,
    )

    clean = re.sub(
        r"(avisame|avísame|recordame|recuérdame)\s+antes\s+\d+\s*(min|minuto|minutos|hora|horas)",
        " ",
        clean,
    )

    phrases = [
        "todos los dias",
        "todos los días",
        "cada dia",
        "cada día",
        "pasado mañana",
        "mañana",
        "hoy",
        "a las",
        "diario",
        "hs",
        "hora",
        "horas",
    ]

    for phrase in phrases:
        clean = remove_phrase(clean, phrase)

    for day in DAYS.keys():
        clean = remove_phrase(clean, day)

    clean = re.sub(r"\d{1,2}[:\.]\d{2}", " ", clean)
    clean = re.sub(r"\d{1,2}\s?h", " ", clean)
    clean = re.sub(r"\d{1,2}/\d{1,2}/\d{4}", " ", clean)

    clean = re.sub(r"\s+", " ", clean).strip()

    return clean or text


def parse_event(text: str) -> dict:
    raw = text.strip()
    lower = raw.lower()
    today = datetime.now().date()

    data = {
        "title": clean_title(raw),
        "type": "task",
        "priority": "media",
        "date": None,
        "time": None,
        "recurrence": None,
        "remind_before": extract_remind_before(raw),
    }

    if "pasado mañana" in lower:
        data["date"] = today + timedelta(days=2)

    elif "mañana" in lower:
        data["date"] = today + timedelta(days=1)

    elif "hoy" in lower:
        data["date"] = today

    date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", lower)

    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3))

        try:
            data["date"] = datetime(year, month, day).date()
        except Exception:
            pass

    time_match = re.search(r"(\d{1,2})[:\.](\d{2})", lower)

    if time_match:
        data["time"] = f"{int(time_match.group(1)):02}:{int(time_match.group(2)):02}"

    else:
        hour_match = re.search(r"(\d{1,2})\s?h", lower)

        if hour_match:
            data["time"] = f"{int(hour_match.group(1)):02}:00"

    found_days = []

    for raw_day, normalized in DAYS.items():
        if re.search(r"\b" + re.escape(raw_day) + r"\b", lower):
            if normalized not in found_days:
                found_days.append(normalized)

    if any(x in lower for x in ["todos los dias", "todos los días", "diario", "cada dia", "cada día"]):
        data["type"] = "habit"
        data["recurrence"] = "diario"

    elif found_days:
        data["type"] = "habit"
        data["recurrence"] = ",".join(found_days)

    if any(x in lower for x in ["turno", "medico", "médico", "dentista", "veterinario"]):
        if not data["recurrence"]:
            data["type"] = "reminder"

    return data