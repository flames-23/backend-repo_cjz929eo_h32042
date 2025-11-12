import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from passlib.context import CryptContext

from database import db, create_document, get_documents
from schemas import User, Progress, Step, Notification, RecommendationProfile

app = FastAPI(title="Work in Taiwan Guide API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Utility helpers
class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class AuthResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    role: str = "user"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


@app.get("/")
def root():
    return {"message": "Work in Taiwan Guide Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Auth endpoints (simple sessionless tokenless demo)
@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    existing = db["user"].find_one({"email": payload.email}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="user",
        preferences={}
    )
    user_id = create_document("user", user)
    return AuthResponse(user_id=user_id, email=payload.email, name=payload.name, role="user")


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    doc = db["user"].find_one({"email": payload.email}) if db else None
    if not doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(user_id=str(doc.get("_id")), email=doc.get("email"), name=doc.get("name"), role=doc.get("role", "user"))


# Steps content - basic CRUD for admin (no auth guard for demo)
@app.get("/api/steps", response_model=List[Dict[str, Any]])
def list_steps():
    items = get_documents("step") if db else []
    # ensure string id
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    # sort by order
    items.sort(key=lambda x: x.get("order", 0))
    return items


@app.post("/api/steps", response_model=Dict[str, Any])
def create_step(step: Step):
    step_id = create_document("step", step)
    return {"id": step_id}


@app.put("/api/steps/{step_id}")
def update_step(step_id: str, payload: Dict[str, Any]):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["step"].update_one({"_id": ObjectId(step_id)}, {"$set": payload})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"updated": True}


@app.delete("/api/steps/{step_id}")
def delete_step(step_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["step"].delete_one({"_id": ObjectId(step_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"deleted": True}


# Progress endpoints
class ProgressUpdate(BaseModel):
    user_id: str
    items: Dict[str, bool]


@app.get("/api/progress/{user_id}")
def get_progress(user_id: str):
    if db is None:
        return {"items": {}}
    doc = db["progress"].find_one({"user_id": user_id})
    if not doc:
        return {"items": {}}
    return {"items": doc.get("items", {})}


@app.post("/api/progress")
def set_progress(payload: ProgressUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    db["progress"].update_one(
        {"user_id": payload.user_id},
        {"$set": {"items": payload.items, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"saved": True}


# Notifications minimal endpoints
class NotificationIn(BaseModel):
    user_id: str
    message: str
    due_date: Optional[str] = None


@app.post("/api/notifications")
def create_notification(payload: NotificationIn):
    notif = Notification(user_id=payload.user_id, type="reminder", message=payload.message, due_date=payload.due_date)
    notif_id = create_document("notification", notif)
    return {"id": notif_id}


@app.get("/api/notifications/{user_id}")
def list_notifications(user_id: str):
    items = get_documents("notification", {"user_id": user_id}) if db else []
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    return items


# Provide schemas for admin viewer (optional helper)
@app.get("/schema")
def get_schema_info():
    return {
        "collections": [
            "user",
            "progress",
            "step",
            "notification",
            "recommendationprofile",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
