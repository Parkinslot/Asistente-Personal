import os
import shutil
from datetime import datetime, date

from app.database import SessionLocal
from app.models import Event


def parse_time_value(value):
    if not value:
        return None

    if hasattr(value, "hour"):
        return value

    try:
        return datetime.strptime(value, "%H:%M").time()
    except Exception:
        return None


def create_event(data: dict):
    db = SessionLocal()

    event = Event(
        title=data.get("title") or "sin título",
        type=data.get("type", "task"),
        priority=data.get("priority", "media"),
        date=data.get("date"),
        time=parse_time_value(data.get("time")),
        recurrence=data.get("recurrence"),
        remind_before=data.get("remind_before", 60),
        completed=False,
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    db.close()

    return event


def get_all_events():
    db = SessionLocal()
    events = db.query(Event).filter(Event.archived == False).order_by(Event.id.asc()).all()
    db.close()
    return events


def get_today_events():
    db = SessionLocal()
    today = date.today()

    events = db.query(Event).filter(Event.archived == False).order_by(Event.id.asc()).all()
    db.close()

    weekday = [
        "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"
    ][today.weekday()]

    result = []

    for e in events:
        if e.type == "task" and not e.completed:
            if not e.date or e.date == today:
                result.append(e)

        elif e.type == "reminder" and e.date == today:
            result.append(e)

        elif e.type == "habit":
            if e.last_completed_date == today:
                continue

            if e.recurrence == "diario":
                result.append(e)
            elif e.recurrence and weekday in e.recurrence.split(","):
                result.append(e)

    return result


def complete_event(event_id: int):
    db = SessionLocal()
    event = db.query(Event).filter(Event.id == event_id, Event.archived == False).first()

    if not event:
        db.close()
        return None

    if event.type == "habit":
        event.last_completed_date = date.today()
        event.total_completions += 1
        event.streak += 1
    else:
        event.completed = True

    db.commit()
    db.refresh(event)
    db.close()

    return event


def delete_event(event_id: int):
    db = SessionLocal()
    event = db.query(Event).filter(Event.id == event_id, Event.archived == False).first()

    if not event:
        db.close()
        return None

    event.archived = True
    db.commit()
    db.refresh(event)
    db.close()

    return event


def delete_all_events():
    db = SessionLocal()

    events = db.query(Event).filter(Event.archived == False).all()
    total = len(events)

    for event in events:
        event.archived = True

    db.commit()
    db.close()

    return total


def update_event(event_id: int, data: dict):
    db = SessionLocal()

    event = db.query(Event).filter(Event.id == event_id, Event.archived == False).first()

    if not event:
        db.close()
        return None

    event.title = data.get("title") or event.title
    event.type = data.get("type") or event.type
    event.priority = data.get("priority") or event.priority
    event.date = data.get("date")
    event.time = parse_time_value(data.get("time"))
    event.recurrence = data.get("recurrence")
    event.remind_before = data.get("remind_before", event.remind_before or 60)

    db.commit()
    db.refresh(event)
    db.close()

    return event


def backup_database():
    db_file = "assistant.db"

    if not os.path.exists(db_file):
        return None

    backup_folder = "backups"
    os.makedirs(backup_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_folder, f"assistant_backup_{timestamp}.db")

    shutil.copy2(db_file, backup_path)

    return backup_path