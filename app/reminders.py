from datetime import datetime, date, timedelta
import urllib.parse
import urllib.request

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from app.database import SessionLocal
from app.models import Event


sent_reminders = set()


def send_telegram_message(message: str):
    if not TELEGRAM_CHAT_ID:
        print("⚠️ Falta TELEGRAM_CHAT_ID en .env")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }).encode()

    try:
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ Error enviando Telegram: {e}")


def today_name():
    days = [
        "lunes", "martes", "miercoles",
        "jueves", "viernes", "sabado", "domingo"
    ]
    return days[date.today().weekday()]


def habit_runs_today(event):
    if event.recurrence == "diario":
        return True

    if event.recurrence:
        days = [d.strip() for d in event.recurrence.split(",")]
        return today_name() in days

    return False


def get_event_date_for_today(event):
    today = date.today()

    # Recordatorio con fecha
    if event.type == "reminder":
        if event.date == today:
            return today
        return None

    # Tarea con fecha
    if event.type == "task":
        if event.completed:
            return None

        # Si tiene fecha, solo avisa ese día
        if event.date:
            return today if event.date == today else None

        # Si NO tiene fecha pero tiene hora, avisa hoy
        return today

    # Hábito
    if event.type == "habit":
        if event.last_completed_date == today:
            return None

        if habit_runs_today(event):
            return today

    return None


def check_upcoming_reminders():
    db = SessionLocal()

    now = datetime.now()
    events = db.query(Event).filter(Event.archived == False).all()

    for event in events:
        if not event.time:
            continue

        event_date = get_event_date_for_today(event)

        if not event_date:
            continue

        event_datetime = datetime.combine(event_date, event.time)

        remind_before = event.remind_before or 60
        reminder_datetime = event_datetime - timedelta(minutes=remind_before)

        reminder_key = f"{event.id}-{event_date}-{event.time}-{remind_before}"

        if reminder_key in sent_reminders:
            continue

        if reminder_datetime <= now <= reminder_datetime + timedelta(seconds=60):
            send_telegram_message(
                "🔔 RECORDATORIO\n\n"
                f"En {remind_before} minutos:\n"
                f"• {event.title}\n"
                f"📌 Tipo: {event.type}\n"
                f"⏰ Hora: {event.time.strftime('%H:%M')}"
            )

            sent_reminders.add(reminder_key)

    db.close()


def morning_summary():
    db = SessionLocal()

    today = date.today()
    events = db.query(Event).filter(Event.archived == False).all()

    today_events = []

    for event in events:
        if event.type == "task":
            if not event.completed:
                if not event.date or event.date == today:
                    today_events.append(event)

        elif event.type == "reminder":
            if event.date == today:
                today_events.append(event)

        elif event.type == "habit":
            if event.last_completed_date == today:
                continue

            if habit_runs_today(event):
                today_events.append(event)

    if today_events:
        msg = "🌞 BUEN DÍA HERMOSO\n\nHoy:\n\n"

        for event in today_events:
            hour = event.time.strftime("%H:%M") if event.time else "sin hora"
            msg += f"• {event.title} ({hour})\n"

        send_telegram_message(msg)

    db.close()


def midday_checkin():
    db = SessionLocal()

    today = date.today()

    habits = db.query(Event).filter(
        Event.archived == False,
        Event.type == "habit"
    ).all()

    pending = [
        h for h in habits
        if h.last_completed_date != today and habit_runs_today(h)
    ]

    if pending:
        msg = "👀 CHECK-IN DEL MEDIODÍA\n\nSeguís teniendo pendiente:\n\n"

        for habit in pending:
            msg += f"• {habit.title}\n"

        send_telegram_message(msg)

    db.close()


def night_summary():
    db = SessionLocal()

    today = date.today()

    habits = db.query(Event).filter(
        Event.archived == False,
        Event.type == "habit"
    ).all()

    missed = [
        h for h in habits
        if h.last_completed_date != today and habit_runs_today(h)
    ]

    if missed:
        msg = "🌙 RESUMEN DEL DÍA\n\nHábitos no completados:\n\n"

        for habit in missed:
            msg += f"• {habit.title}\n"

        send_telegram_message(msg)

    db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(check_upcoming_reminders, "interval", minutes=1)

    scheduler.add_job(morning_summary, "cron", hour=9, minute=0)
    scheduler.add_job(midday_checkin, "cron", hour=12, minute=0)
    scheduler.add_job(night_summary, "cron", hour=22, minute=0)

    scheduler.start()

    print("⏰ Recordatorios iniciados.")