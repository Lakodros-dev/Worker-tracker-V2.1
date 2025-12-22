"""FastAPI Backend for Attendance System."""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from config import config
from auth import get_current_user
from database import db, get_settings, save_settings, USERS_FILE, REPORTS_FILE, LOCATIONS_FILE
import services

app = FastAPI(title="Davomat Tizimi API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class LocationRequest(BaseModel):
    latitude: float
    longitude: float


class ReportRequest(BaseModel):
    content: str
    date: Optional[str] = None


class DateRangeRequest(BaseModel):
    start_date: str
    end_date: str


class SettingsRequest(BaseModel):
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    lunch_start: Optional[str] = None
    lunch_end: Optional[str] = None
    geofence: Optional[dict] = None


class UserStatusRequest(BaseModel):
    status: str


# Health Check
@app.get("/")
async def root():
    return {"message": "Davomat Tizimi API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# User Routes
@app.get("/users/me")
async def get_me(user=Depends(get_current_user)):
    return user


@app.get("/users/is-admin")
async def check_admin(user=Depends(get_current_user)):
    return {"is_admin": config.is_admin(user["telegram_id"])}


@app.get("/users")
async def get_all_users(user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    return db.read(USERS_FILE)


@app.get("/users/pending")
async def get_pending_users(user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    return db.find_many(USERS_FILE, {"status": "pending"})


@app.put("/users/{telegram_id}/status")
async def update_user_status(telegram_id: int, req: UserStatusRequest, user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    if req.status not in ["active", "blocked", "pending"]:
        raise HTTPException(400, "Invalid status")
    success = db.update(USERS_FILE, "telegram_id", telegram_id, {"status": req.status})
    if not success:
        raise HTTPException(404, "User not found")
    return {"message": "Updated", "status": req.status}


# Session Routes
@app.post("/sessions/start")
async def start_session(user=Depends(get_current_user)):
    session = services.start_session(user["telegram_id"])
    if not session:
        raise HTTPException(400, "Ish vaqti tashqarida")
    return session


@app.post("/sessions/end")
async def end_session(user=Depends(get_current_user)):
    session = services.end_session(user["telegram_id"])
    if not session:
        raise HTTPException(404, "Faol sessiya topilmadi")
    return session


@app.get("/sessions/today")
async def get_today_session(user=Depends(get_current_user)):
    session = services.get_today_session(user["telegram_id"])
    return {"session": session}


@app.post("/sessions/history")
async def get_session_history(req: DateRangeRequest, user=Depends(get_current_user)):
    return services.get_sessions_by_range(user["telegram_id"], req.start_date, req.end_date)


@app.get("/sessions/should-track")
async def should_track(user=Depends(get_current_user)):
    return {"should_track": services.is_work_hours()}


# Location Routes
@app.post("/locations/record")
async def record_location(req: LocationRequest, user=Depends(get_current_user)):
    session = services.get_today_session(user["telegram_id"])
    if not session:
        raise HTTPException(400, "Avval sessiyani boshlang")
    
    location = services.record_location(user["telegram_id"], session["id"], req.latitude, req.longitude)
    if not location:
        return {"recorded": False, "message": "Ish vaqti tashqarida"}
    return location


@app.get("/locations/session/{session_id}")
async def get_session_locations(session_id: str, user=Depends(get_current_user)):
    return db.find_many(LOCATIONS_FILE, {"session_id": session_id})


@app.get("/locations/should-track")
async def should_track_location(user=Depends(get_current_user)):
    return {"should_track": services.is_work_hours()}


# Report Routes
@app.post("/reports/submit")
async def submit_report(req: ReportRequest, user=Depends(get_current_user)):
    if not req.content.strip():
        raise HTTPException(400, "Hisobot bo'sh bo'lishi mumkin emas")
    return services.submit_report(user["telegram_id"], req.content, req.date)


@app.get("/reports/today")
async def get_today_report(user=Depends(get_current_user)):
    today = datetime.now().strftime("%Y-%m-%d")
    report = services.get_user_report(user["telegram_id"], today)
    return {"report": report, "submitted": report is not None}


@app.get("/reports/date/{date}")
async def get_report_by_date(date: str, user=Depends(get_current_user)):
    return {"report": services.get_user_report(user["telegram_id"], date)}


@app.get("/reports/history")
async def get_report_history(user=Depends(get_current_user)):
    return db.find_many(REPORTS_FILE, {"user_id": user["telegram_id"]})


@app.get("/reports/status")
async def get_report_status(user=Depends(get_current_user)):
    today = datetime.now().strftime("%Y-%m-%d")
    report = services.get_user_report(user["telegram_id"], today)
    return {"submitted": report is not None}


@app.get("/reports/all/{date}")
async def get_all_reports_by_date(date: str, user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    return db.find_many(REPORTS_FILE, {"date": date})


# Statistics Routes
@app.post("/statistics/me")
async def get_my_statistics(req: DateRangeRequest, user=Depends(get_current_user)):
    return services.get_user_statistics(user["telegram_id"], req.start_date, req.end_date)


@app.post("/statistics/user/{user_id}")
async def get_user_statistics(user_id: int, req: DateRangeRequest, user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    return services.get_user_statistics(user_id, req.start_date, req.end_date)


@app.post("/statistics/all")
async def get_all_statistics(req: DateRangeRequest, user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    users = db.read(USERS_FILE)
    return [
        {"user": u, "statistics": services.get_user_statistics(u["telegram_id"], req.start_date, req.end_date)}
        for u in users
    ]


@app.post("/statistics/chart/me")
async def get_my_chart(req: DateRangeRequest, user=Depends(get_current_user)):
    return services.get_chart_data(user["telegram_id"], req.start_date, req.end_date)


@app.post("/statistics/chart/user/{user_id}")
async def get_user_chart(user_id: int, req: DateRangeRequest, user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    return services.get_chart_data(user_id, req.start_date, req.end_date)


# Settings Routes
@app.get("/settings")
async def get_work_settings(user=Depends(get_current_user)):
    return get_settings()


@app.put("/settings")
async def update_settings(req: SettingsRequest, user=Depends(get_current_user)):
    if not config.is_admin(user["telegram_id"]):
        raise HTTPException(403, "Admin only")
    
    current = get_settings()
    if req.work_start:
        current["work_start"] = req.work_start
    if req.work_end:
        current["work_end"] = req.work_end
    if req.lunch_start:
        current["lunch_start"] = req.lunch_start
    if req.lunch_end:
        current["lunch_end"] = req.lunch_end
    if req.geofence:
        current["geofence"] = req.geofence
    
    save_settings(current)
    return current


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
