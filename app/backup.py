import os
import shutil
from datetime import datetime


def backup_database():
    db_file = "assistant.db"

    if not os.path.exists(db_file):
        return None

    os.makedirs("backups", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/assistant_backup_{timestamp}.db"

    shutil.copy2(db_file, backup_path)

    return backup_path