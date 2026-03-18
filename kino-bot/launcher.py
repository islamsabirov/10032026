import os

# Bot papkasi (o‘zingizga moslab yozing)
BASE_DIR = r"E:\0.my bot\444\kino-bot"
os.environ['PYTHONPATH'] = BASE_DIR
os.chdir(BASE_DIR)

# Required environment variables
os.environ['BOT_TOKEN'] = '8759637966:AAG4dXEfmN6H3HxRJq67IzO_VY04Wj3WbP4'
os.environ['ADMIN_IDS'] = '5907118746'
os.environ['PRIVATE_CHANNEL_ID'] = '-1001234567890'

# Bo‘sh db faylni yaratish agar yo‘q bo‘lsa
db_path = os.path.join(BASE_DIR, "bot", "db.sqlite")
if not os.path.exists(db_path):
    open(db_path, 'a').close()

# Botni ishga tushurish
os.system('python -m bot.main')