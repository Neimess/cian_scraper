from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship
)
from datetime import datetime

Base = declarative_base()

class User(Base):
    """
    User model representing a Telegram user (or any other kind of user).

    Fields:
        id (int): Primary key, auto-increment.
        tg_id (str): Telegram user ID (unique).
        username (str): Telegram username.
        full_name (str): Full name if available.
        created_at (DateTime): Date/time the user was created in the DB.
        updated_at (DateTime): Date/time the user last updated. Changes automatically on update.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(Integer, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.now(),
        onupdate=datetime.now()
    )

    config = relationship("UserConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserConfig(Base):
    """
    Stores user-specific search preferences.
    """
    __tablename__ = "users_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    deal_type = Column(String(10), default="sale")  
    engine_version = Column(Integer, default=2)
    region = Column(Integer, default=2)  
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)
    offer_type = Column(String(10), default="flat")
    mintarea = Column(Integer, nullable=True)
    maxtarea = Column(Integer, nullable=True)
    rooms = Column(String(50), default="1")
    only_foot = Column(Integer, default=2)
    min_house_year = Column(Integer, default=1990)
    min_floor = Column(Integer, default=1)
    max_floor = Column(Integer, nullable=True)
    is_first_floor = Column(Integer, default=0)
    
    user = relationship("User", back_populates="config", lazy="joined")
class Apartment(Base):
    """
    Apartment model representing scraped apartment data from Cian.

    Fields:
        id (int): Primary key, auto-increment.
        title (str): Title or short description of the listing.
        price (float): Price of the apartment (if numeric).
        price_currency (str): Currency code for the price, e.g., 'RUB'.
        description (str): Detailed description of the apartment.
        address (str): Address or location of the listing.
        images (JSON): A list of image URLs (stored in JSON format).
        date_published (DateTime): Date of publication (converted to datetime if needed).
        rooms (str): Number of rooms.
        area (str): String with total area info, or parse into numeric if needed.
    """
    
    __tablename__ = "apartments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    images = relationship("ApartmentImage", back_populates="listing", cascade="all, delete-orphan")
    date_published = Column(DateTime, default=None, nullable=True)
    rooms = Column(String(50), nullable=True)
    area = Column(String(50), nullable=True)
    url = Column(String(500), unique=True, nullable=False)
    
class ApartmentImage(Base):
    """
    ApartmentImage model representing the images for a Apartment.

    Fields:
        id (int): Primary key.
        listing_id (int): Foreign key referencing Apartment.id
        url (str): URL to the image resource
    """

    __tablename__ = "apartment_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    url = Column(Text, nullable=False)

    listing = relationship("Apartment", back_populates="images")