import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID:  int = int(os.getenv("OWNER_ID", "0"))
