"""Business logic services."""
import math
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import db, get_settings, SESSIONS_FILE, LOCATIONS_FILE, REPORTS_FILE, USERS_FILE


def is_work_hours() -> bool:
    """Check if current time is within work hours."""
    settings = get_settings()
    now = datetime.now().strftime("%H:%M")
    return settings["work_start"] <= now <= settings["work_end"]


def calculate_late_minutes(start_time: str) -> int:
    """Calculate late arrival minutes."""
    settings = get_settings()
    work_start = datetime.strptime(settings["work_start"], "%H:%M")
    actual_start = datetime.strptime(start_time, "%H:%M")
    if actual_start > work_start:
        return int((actual_start - work_start).total_seconds() / 60)
    return 0


def calculate_early_leave(end_time: str) -> int:
    """Calculate early leave minutes."""
    settings = get_settings()
    work_end = datetime.strptime(settings["work_end"], "%H:%M")
    actual_end = datetime.strptime(end_time, "%H:%M")
    if actual_end < work_end:
        return int((work_end - actual_end).total_seconds() / 60)
    return 0


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters."""
    R = 6371000
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def is_inside_geofence(lat: float, lng: float) -> bool:
    """Check if coordinates are inside office geofence."""
    settings = get_settings()
    geofence = settings.get("geofence", {})
    distance = haversine_distance(lat, lng, geofence.get("center_lat", 0), geofence.get("center_lng", 0))
    return distance <= geofence.get("radius_meters", 100)


# Session functions
def get_today_session(user_id: int) -> Optional[Dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    sessions = db.find_many(SESSIONS_FILE, {"user_id": user_id, "date": today})
    return sessions[0] if sessions else None


def start_session(user_id: int) -> Optional[Dict]:
    if not is_work_hours():
        return None
    
    existing = get_today_session(user_id)
    if existing:
        if existing["status"] != "online":
            db.update(SESSIONS_FILE, "id", existing["id"], {"status": "online"})
            existing["status"] = "online"
        return existing
    
    current_time = datetime.now().strftime("%H:%M")
    session = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "start_time": current_time,
        "end_time": None,
        "status": "online",
        "total_online_minutes": 0,
        "total_office_minutes": 0,
        "late_arrival_minutes": calculate_late_minutes(current_time),
        "early_leave_minutes": 0,
        "created_at": datetime.now().isoformat()
    }
    db.append(SESSIONS_FILE, session)
    return session


def end_session(user_id: int) -> Optional[Dict]:
    session = get_today_session(user_id)
    if not session:
        return None
    
    current_time = datetime.now().strftime("%H:%M")
    updates = {
        "status": "offline",
        "end_time": current_time,
        "early_leave_minutes": calculate_early_leave(current_time)
    }
    db.update(SESSIONS_FILE, "id", session["id"], updates)
    session.update(updates)
    return session


def get_sessions_by_range(user_id: int, start_date: str, end_date: str) -> List[Dict]:
    all_sessions = db.find_many(SESSIONS_FILE, {"user_id": user_id})
    return [s for s in all_sessions if start_date <= s["date"] <= end_date]


# Location functions
def record_location(user_id: int, session_id: str, lat: float, lng: float) -> Optional[Dict]:
    if not is_work_hours():
        return None
    
    location = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_id": session_id,
        "latitude": lat,
        "longitude": lng,
        "is_inside_office": is_inside_geofence(lat, lng),
        "timestamp": datetime.now().isoformat()
    }
    db.append(LOCATIONS_FILE, location)
    
    # Update session times
    locations = db.find_many(LOCATIONS_FILE, {"session_id": session_id})
    online_minutes = len(locations)
    office_minutes = sum(1 for loc in locations if loc["is_inside_office"])
    db.update(SESSIONS_FILE, "id", session_id, {
        "total_online_minutes": online_minutes,
        "total_office_minutes": office_minutes
    })
    
    return location


# Report functions
def submit_report(user_id: int, content: str, date: str = None) -> Dict:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    existing = db.find_many(REPORTS_FILE, {"user_id": user_id, "date": date})
    if existing:
        db.update(REPORTS_FILE, "id", existing[0]["id"], {
            "content": content,
            "submitted_at": datetime.now().isoformat()
        })
        existing[0]["content"] = content
        return existing[0]
    
    report = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": date,
        "content": content,
        "submitted_at": datetime.now().isoformat()
    }
    db.append(REPORTS_FILE, report)
    return report


def get_user_report(user_id: int, date: str) -> Optional[Dict]:
    reports = db.find_many(REPORTS_FILE, {"user_id": user_id, "date": date})
    return reports[0] if reports else None


# Statistics functions
def get_user_statistics(user_id: int, start_date: str, end_date: str) -> Dict:
    sessions = get_sessions_by_range(user_id, start_date, end_date)
    
    total_online = sum(s.get("total_online_minutes", 0) for s in sessions)
    total_office = sum(s.get("total_office_minutes", 0) for s in sessions)
    total_late = sum(s.get("late_arrival_minutes", 0) for s in sessions)
    total_early = sum(s.get("early_leave_minutes", 0) for s in sessions)
    
    return {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(sessions),
        "total_online_minutes": total_online,
        "total_office_minutes": total_office,
        "total_late_minutes": total_late,
        "total_early_leave_minutes": total_early,
        "average_online_minutes": total_online / len(sessions) if sessions else 0,
        "attendance_rate": (total_office / total_online * 100) if total_online > 0 else 0
    }


def get_chart_data(user_id: int, start_date: str, end_date: str) -> Dict:
    sessions = get_sessions_by_range(user_id, start_date, end_date)
    session_by_date = {s["date"]: s for s in sessions}
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    labels, online_data, office_data, late_data = [], [], [], []
    
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        labels.append(date_str)
        
        session = session_by_date.get(date_str)
        if session:
            online_data.append(session.get("total_online_minutes", 0))
            office_data.append(session.get("total_office_minutes", 0))
            late_data.append(session.get("late_arrival_minutes", 0))
        else:
            online_data.append(0)
            office_data.append(0)
            late_data.append(0)
        
        current += timedelta(days=1)
    
    return {
        "labels": labels,
        "datasets": [
            {"label": "Onlayn vaqt (daqiqa)", "data": online_data, "borderColor": "#4CAF50"},
            {"label": "Ofisda vaqt (daqiqa)", "data": office_data, "borderColor": "#2196F3"},
            {"label": "Kechikish (daqiqa)", "data": late_data, "borderColor": "#F44336"}
        ]
    }
