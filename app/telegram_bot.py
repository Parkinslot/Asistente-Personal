import asyncio

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import TELEGRAM_TOKEN
from app.parser import parse_event
from app.services import (
    create_event,
    get_all_events,
    get_today_events,
    complete_event,
    delete_event,
    delete_all_events,
    update_event,
    backup_database,
)


MENU = ReplyKeyboardMarkup(
    [
        ["➕ Nuevo evento"],
        ["📅 Ver hoy", "📌 Ver todos"],
        ["✅ Completar", "✏️ Editar"],
        ["🗑️ Eliminar", "💾 Backup"],
        ["❌ Cancelar"],
    ],
    resize_keyboard=True,
)

CONFIRM_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Guardar", "❌ No guardar"],
        ["❌ Cancelar"],
    ],
    resize_keyboard=True,
)

CONFIRM_EDIT_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Guardar cambios", "❌ No guardar"],
        ["❌ Cancelar"],
    ],
    resize_keyboard=True,
)

DELETE_MENU = ReplyKeyboardMarkup(
    [
        ["🗑️ Eliminar por ID"],
        ["💣 Eliminar TODOS"],
        ["❌ Cancelar"],
    ],
    resize_keyboard=True,
)

CONFIRM_DELETE_ALL_MENU = ReplyKeyboardMarkup(
    [
        ["CONFIRMAR BORRADO TOTAL"],
        ["❌ Cancelar"],
    ],
    resize_keyboard=True,
)

user_states = {}


def format_event(e):
    status = "✅" if e.completed else "⏳"

    type_icon = {
        "task": "📌 tarea",
        "habit": "🔁 hábito",
        "reminder": "⏰ recordatorio",
    }.get(e.type, e.type)

    date_text = str(e.date) if e.date else "-"
    time_text = e.time.strftime("%H:%M") if e.time else "sin hora"
    recurrence_text = e.recurrence if e.recurrence else "-"
    remind_text = f"{e.remind_before} min antes" if e.remind_before else "60 min antes"

    return (
        f"{e.id} | {status} | {e.title} | {type_icon} | "
        f"{date_text} | {time_text} | {recurrence_text} | 🔔 {remind_text}"
    )


def format_events(events, title):
    if not events:
        return "📭 No hay eventos."

    lines = [title, ""]

    for e in events:
        lines.append(format_event(e))

    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id] = {"mode": "menu"}

    await update.message.reply_text(
        "👋 Hola, soy tu asistente personal.\n\n"
        "Podés crear tareas, hábitos y recordatorios desde Telegram.\n\n"
        "Ejemplos:\n"
        "• gimnasio todos los días 10:30\n"
        "• veterinario martes y jueves 18h\n"
        "• dentista mañana 15:00 avisame 30 min antes\n"
        "• pagar alquiler",
        reply_markup=MENU,
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    state = user_states.get(user_id, {"mode": "menu"})

    if text == "❌ Cancelar":
        user_states[user_id] = {"mode": "menu"}
        await update.message.reply_text("👌 Cancelado.", reply_markup=MENU)
        return

    if text == "➕ Nuevo evento":
        user_states[user_id] = {"mode": "creating"}
        await update.message.reply_text(
            "📝 Escribí el evento.\n\n"
            "Ejemplos:\n"
            "• gimnasio todos los días 10:30\n"
            "• veterinario martes y jueves 18h\n"
            "• dentista mañana 15:00 avisame 30 min antes",
            reply_markup=MENU,
        )
        return

    if text == "📅 Ver hoy":
        events = get_today_events()
        await update.message.reply_text(format_events(events, "📅 HOY"), reply_markup=MENU)
        return

    if text == "📌 Ver todos":
        events = get_all_events()
        await update.message.reply_text(format_events(events, "📌 EVENTOS"), reply_markup=MENU)
        return

    if text == "💾 Backup":
        path = backup_database()

        if path:
            await update.message.reply_text(
                f"💾 Backup creado correctamente:\n{path}",
                reply_markup=MENU,
            )
        else:
            await update.message.reply_text(
                "⚠️ No encontré la base de datos para hacer backup.",
                reply_markup=MENU,
            )
        return

    if text == "✅ Completar":
        events = get_today_events()
        await update.message.reply_text(
            format_events(events, "✅ ¿Cuál completaste?\n\nRespondé con el ID."),
            reply_markup=MENU,
        )
        user_states[user_id] = {"mode": "completing"}
        return

    if text == "✏️ Editar":
        events = get_all_events()
        await update.message.reply_text(
            format_events(events, "✏️ ¿Cuál querés editar?\n\nRespondé con el ID."),
            reply_markup=MENU,
        )
        user_states[user_id] = {"mode": "editing_id"}
        return

    if text == "🗑️ Eliminar":
        user_states[user_id] = {"mode": "delete_menu"}
        await update.message.reply_text(
            "🗑️ ¿Qué querés eliminar?",
            reply_markup=DELETE_MENU,
        )
        return

    if state["mode"] == "delete_menu":
        if text == "🗑️ Eliminar por ID":
            events = get_all_events()
            await update.message.reply_text(
                format_events(events, "🗑️ ¿Cuál querés eliminar?\n\nRespondé con el ID."),
                reply_markup=MENU,
            )
            user_states[user_id] = {"mode": "deleting"}
            return

        if text == "💣 Eliminar TODOS":
            total = len(get_all_events())

            if total == 0:
                user_states[user_id] = {"mode": "menu"}
                await update.message.reply_text("📭 No hay eventos para eliminar.", reply_markup=MENU)
                return

            user_states[user_id] = {"mode": "confirm_delete_all"}
            await update.message.reply_text(
                f"⚠️ Vas a eliminar TODOS los eventos activos ({total}).\n\n"
                "Para confirmar, tocá:\n"
                "CONFIRMAR BORRADO TOTAL",
                reply_markup=CONFIRM_DELETE_ALL_MENU,
            )
            return

        await update.message.reply_text("Elegí una opción.", reply_markup=DELETE_MENU)
        return

    if state["mode"] == "confirm_delete_all":
        if text == "CONFIRMAR BORRADO TOTAL":
            total = delete_all_events()
            user_states[user_id] = {"mode": "menu"}
            await update.message.reply_text(
                f"💣 Se eliminaron {total} eventos.",
                reply_markup=MENU,
            )
            return

        user_states[user_id] = {"mode": "menu"}
        await update.message.reply_text("👌 Cancelado.", reply_markup=MENU)
        return

    if state["mode"] == "creating":
        parsed = parse_event(text)

        user_states[user_id] = {
            "mode": "confirming_create",
            "data": parsed,
        }

        await update.message.reply_text(
            "🧠 Entendí esto:\n\n"
            f"📝 Título: {parsed['title']}\n"
            f"📌 Tipo: {parsed['type']}\n"
            f"📅 Fecha: {parsed['date'] or '-'}\n"
            f"⏰ Hora: {parsed['time'] or 'sin hora'}\n"
            f"🔁 Recurrencia: {parsed['recurrence'] or '-'}\n"
            f"🔔 Recordatorio: {parsed['remind_before']} min antes\n\n"
            "¿Querés guardarlo?",
            reply_markup=CONFIRM_MENU,
        )
        return

    if state["mode"] == "confirming_create":
        if text == "✅ Guardar":
            event = create_event(state["data"])
            user_states[user_id] = {"mode": "menu"}

            await update.message.reply_text(
                f"✅ Guardado:\n{format_event(event)}",
                reply_markup=MENU,
            )
            return

        if text == "❌ No guardar":
            user_states[user_id] = {"mode": "menu"}
            await update.message.reply_text("❌ No lo guardé.", reply_markup=MENU)
            return

        await update.message.reply_text("Elegí una opción:", reply_markup=CONFIRM_MENU)
        return

    if state["mode"] == "editing_id":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Mandame solo el ID del evento.", reply_markup=MENU)
            return

        user_states[user_id] = {
            "mode": "editing_text",
            "event_id": int(text),
        }

        await update.message.reply_text(
            "✏️ Escribí cómo debería quedar el evento.\n\n"
            "Ejemplos:\n"
            "• gimnasio lunes miercoles y viernes 18:00\n"
            "• dentista mañana 16:00 avisame 30 min antes\n"
            "• regar las plantas lunes jueves 9:00 avisame 1 min antes",
            reply_markup=MENU,
        )
        return

    if state["mode"] == "editing_text":
        parsed = parse_event(text)

        user_states[user_id] = {
            "mode": "confirming_edit",
            "event_id": state["event_id"],
            "data": parsed,
        }

        await update.message.reply_text(
            "🧠 Cambiar por esto:\n\n"
            f"📝 Título: {parsed['title']}\n"
            f"📌 Tipo: {parsed['type']}\n"
            f"📅 Fecha: {parsed['date'] or '-'}\n"
            f"⏰ Hora: {parsed['time'] or 'sin hora'}\n"
            f"🔁 Recurrencia: {parsed['recurrence'] or '-'}\n"
            f"🔔 Recordatorio: {parsed['remind_before']} min antes\n\n"
            "¿Guardar cambios?",
            reply_markup=CONFIRM_EDIT_MENU,
        )
        return

    if state["mode"] == "confirming_edit":
        if text == "✅ Guardar cambios":
            event = update_event(state["event_id"], state["data"])
            user_states[user_id] = {"mode": "menu"}

            if event:
                await update.message.reply_text(
                    f"✅ Evento actualizado:\n{format_event(event)}",
                    reply_markup=MENU,
                )
            else:
                await update.message.reply_text(
                    "⚠️ No encontré ese evento.",
                    reply_markup=MENU,
                )
            return

        if text == "❌ No guardar":
            user_states[user_id] = {"mode": "menu"}
            await update.message.reply_text("❌ No guardé los cambios.", reply_markup=MENU)
            return

        await update.message.reply_text("Elegí una opción:", reply_markup=CONFIRM_EDIT_MENU)
        return

    if state["mode"] == "completing":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Mandame solo el ID del evento.", reply_markup=MENU)
            return

        event = complete_event(int(text))
        user_states[user_id] = {"mode": "menu"}

        if event:
            await update.message.reply_text(f"✅ Completado:\n{event.title}", reply_markup=MENU)
        else:
            await update.message.reply_text("⚠️ No encontré ese ID.", reply_markup=MENU)
        return

    if state["mode"] == "deleting":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Mandame solo el ID del evento.", reply_markup=MENU)
            return

        event = delete_event(int(text))
        user_states[user_id] = {"mode": "menu"}

        if event:
            await update.message.reply_text(f"🗑️ Eliminado:\n{event.title}", reply_markup=MENU)
        else:
            await update.message.reply_text("⚠️ No encontré ese ID.", reply_markup=MENU)
        return

    await update.message.reply_text(
        "Usá los botones 👇",
        reply_markup=MENU,
    )


def run_bot():
    async def main():
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

        print("🤖 Telegram bot activo...")

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        while True:
            await asyncio.sleep(3600)

    asyncio.run(main())