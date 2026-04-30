from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    """Kullanıcılar Tablosu"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    department = Column(String(50), nullable=False)  # 'front_office' veya 'housekeeping'
    created_at = Column(DateTime, default=datetime.utcnow)

class Room(Base):
    """Odalar Tablosu"""
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_type = Column(String(50), nullable=False)  # Standart, Delüks, Suit
    status = Column(String(50), default="Clean")  # Clean, Dirty, Inspected, OutOfOrder
    occupancy = Column(String(50), default="Vacant")  # Vacant, Occupied
    last_cleaned_at = Column(DateTime, default=datetime.utcnow)

class Booking(Base):
    """Rezervasyonlar Tablosu"""
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    guest_name = Column(String(100), nullable=False)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    reservation_status = Column(String(50), default="Arrived")  # Arrived, Checked-out, No-show
    created_at = Column(DateTime, default=datetime.utcnow)
