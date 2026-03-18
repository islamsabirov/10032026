from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/")
async def root():
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "service": "kino-bot"
    }

@app.get("/health")
async def health():
    """UptimeRobot shu endpointni ping qiladi"""
    return {"status": "healthy", "uptime": "100%"}

# Agar alohida uptime server kerak bo'lsa:
# python -m uvicorn uptime:app --host 0.0.0.0 --port $PORT