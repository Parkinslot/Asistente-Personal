from app.database import init_db
from app.telegram_bot import run_bot
from app.reminders import start_scheduler
from app.backup import backup_database


def main():
    print("🚀 Iniciando asistente personal...")

    init_db()
    print("✅ Base de datos lista.")

    backup_path = backup_database()

    if backup_path:
        print(f"💾 Backup creado: {backup_path}")

    start_scheduler()

    run_bot()


if __name__ == "__main__":
    main()