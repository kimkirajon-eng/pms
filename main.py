from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
from datetime import datetime
from typing import List

from database import engine, SessionLocal
from models import Base, User, Room, Booking
from auth import verify_password, create_access_token, verify_token, get_password_hash

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hotel PMS System")

# WebSocket Bağlantı Yöneticisi
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                continue

manager = ConnectionManager()

# Klasör kontrolü
if not os.path.exists("static"): os.makedirs("static")
if not os.path.exists("templates"): os.makedirs("templates")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============= MODELLER =============
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str = None
    department: str = None

# ============= STARTUP & WEBSOCKET =============
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    demo_users = [
        {"u": "front_office", "p": "1234", "d": "front_office"},
        {"u": "housekeeping", "p": "1234", "d": "housekeeping"}
    ]
    for d in demo_users:
        if not db.query(User).filter(User.username == d["u"]).first():
            new_user = User(username=d["u"], password_hash=get_password_hash(d["p"]), department=d["d"])
            db.add(new_user)
    
    if db.query(Room).count() == 0:
        for i in range(101, 106):
            db.add(Room(id=i, room_type="Standart", status="Dirty", occupancy="Vacant"))
    db.commit()
    db.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============= SAYFALAR =============
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/dashboard/front_office", response_class=HTMLResponse)
async def front_office_dashboard(request: Request, token: str = None, db: Session = Depends(get_db)):
    if not token: return RedirectResponse(url="/", status_code=302)
    payload = verify_token(token)
    if not payload or payload.get("department") != "front_office":
        return RedirectResponse(url="/", status_code=302)
    
    today = datetime.now().date()
    active_bookings = db.query(Booking).filter((Booking.check_in <= today) & (Booking.check_out >= today)).all()
    return templates.TemplateResponse(request=request, name="front_office_dashboard.html", context={
        "username": payload.get("sub"), "bookings": active_bookings, "token": token
    })

@app.get("/dashboard/housekeeping", response_class=HTMLResponse)
async def housekeeping_dashboard(request: Request, token: str = None, db: Session = Depends(get_db)):
    if not token: return RedirectResponse(url="/", status_code=302)
    payload = verify_token(token)
    if not payload or payload.get("department") != "housekeeping":
        return RedirectResponse(url="/", status_code=302)
    
    rooms = db.query(Room).all()
    return templates.TemplateResponse(request=request, name="housekeeping_dashboard.html", context={
        "username": payload.get("sub"), "rooms": rooms, "token": token
    })

# ============= API ENDPOINTLERI =============
@app.post("/api/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")
    
    access_token = create_access_token(data={"sub": user.username, "department": user.department})
    return {"success": True, "message": f"{user.department} hoşgeldiniz", "token": access_token, "department": user.department}

@app.get("/api/rooms")
async def get_rooms(token: str = None, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401)
    return db.query(Room).all()

@app.put("/api/rooms/{room_id}/status")
async def update_room_status(room_id: int, new_status: str, token: str = None, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload or payload.get("department") != "housekeeping":
        raise HTTPException(status_code=403)
    room = db.query(Room).filter(Room.id == room_id).first()
    if room:
        room.status = new_status
        room.last_cleaned_at = datetime.now()
        db.commit()
        # DEĞİŞİKLİĞİ TÜM BAĞLI EKRANLARA DUYUR
        await manager.broadcast("rooms_updated")
    return {"message": "Güncellendi"}

@app.get("/health")
async def health(): return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
