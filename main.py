from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
from datetime import datetime

from database import engine, SessionLocal
from models import Base, User, Room, Booking
from auth import verify_password, create_access_token, verify_token

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hotel PMS System")

# Template ve Static dosyalarını bağla
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency: Veritabanı oturumu
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============= LOGIN MODELLERI =============
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str = None
    department: str = None

# ============= LOGIN SAYFASI =============
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Giriş sayfasını sunun"""
    return templates.TemplateResponse("login.html", {"request": request})

# ============= LOGIN ENDPOINT'İ =============
@app.post("/api/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Kullanıcı giriş endpoint'i
    - Username ve password kontrolü yapılır
    - Department bilgisine göre token oluşturulur
    """
    # Kullanıcıyı veritabanında ara
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre"
        )
    
    # Token oluştur
    access_token = create_access_token(
        data={"sub": user.username, "department": user.department}
    )
    
    return {
        "success": True,
        "message": f"{user.department} paneline hoşgeldiniz",
        "token": access_token,
        "department": user.department
    }

# ============= ÖNBÜRO DASHBOARD =============
@app.get("/dashboard/front_office", response_class=HTMLResponse)
async def front_office_dashboard(request: Request, token: str = None, db: Session = Depends(get_db)):
    """Önbüro departmanı dashboard'u"""
    
    if not token:
        return RedirectResponse(url="/", status_code=302)
    
    # Token doğrula
    payload = verify_token(token)
    if not payload or payload.get("department") != "front_office":
        return RedirectResponse(url="/", status_code=302)
    
    # Aktif rezervasyonları getir
    today = datetime.now().date()
    active_bookings = db.query(Booking).filter(
        (Booking.check_in <= today) & (Booking.check_out >= today)
    ).all()
    
    return templates.TemplateResponse(
        "front_office_dashboard.html",
        {
            "request": request,
            "username": payload.get("sub"),
            "bookings": active_bookings,
            "token": token
        }
    )

# ============= HOUSEKEEPING DASHBOARD =============
@app.get("/dashboard/housekeeping", response_class=HTMLResponse)
async def housekeeping_dashboard(request: Request, token: str = None, db: Session = Depends(get_db)):
    """Housekeeping departmanı dashboard'u"""
    
    if not token:
        return RedirectResponse(url="/", status_code=302)
    
    # Token doğrula
    payload = verify_token(token)
    if not payload or payload.get("department") != "housekeeping":
        return RedirectResponse(url="/", status_code=302)
    
    # Odaların durumunu getir
    rooms = db.query(Room).all()
    
    return templates.TemplateResponse(
        "housekeeping_dashboard.html",
        {
            "request": request,
            "username": payload.get("sub"),
            "rooms": rooms,
            "token": token
        }
    )

# ============= API: REZERVASYONLAR (Önbüro) =============
@app.get("/api/bookings")
async def get_bookings(token: str = None, db: Session = Depends(get_db)):
    """Tüm rezervasyonları listele (Önbüro)"""
    
    payload = verify_token(token)
    if not payload or payload.get("department") != "front_office":
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    
    bookings = db.query(Booking).all()
    return [
        {
            "id": b.id,
            "room_id": b.room_id,
            "guest_name": b.guest_name,
            "check_in": b.check_in,
            "check_out": b.check_out,
            "reservation_status": b.reservation_status
        }
        for b in bookings
    ]

# ============= API: ODALAR (Housekeeping) =============
@app.get("/api/rooms")
async def get_rooms(token: str = None, db: Session = Depends(get_db)):
    """Tüm odaları listele (Housekeeping)"""
    
    payload = verify_token(token)
    if not payload or payload.get("department") != "housekeeping":
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    
    rooms = db.query(Room).all()
    return [
        {
            "id": r.id,
            "room_type": r.room_type,
            "status": r.status,
            "occupancy": r.occupancy,
            "last_cleaned_at": r.last_cleaned_at
        }
        for r in rooms
    ]

# ============= API: ODA DURUMU GÜNCELLE =============
@app.put("/api/rooms/{room_id}/status")
async def update_room_status(
    room_id: int,
    new_status: str,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Oda durumunu güncelle (Housekeeping)"""
    
    payload = verify_token(token)
    if not payload or payload.get("department") != "housekeeping":
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Oda bulunamadı")
    
    room.status = new_status
    room.last_cleaned_at = datetime.now()
    db.commit()
    
    return {"message": f"Oda {room_id} durumu '{new_status}' olarak güncellendi"}

# ============= LOGOUT =============
@app.post("/api/logout")
async def logout():
    """Logout işlemi"""
    return JSONResponse({"success": True, "message": "Başarıyla çıkış yaptınız"})

# ============= HEALTH CHECK =============
@app.get("/health")
async def health_check():
    """Uygulama sağlık kontrolü (Render monitoring için)"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
