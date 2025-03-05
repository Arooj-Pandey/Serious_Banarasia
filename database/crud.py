from sqlalchemy.orm import Session
from . import models
from typing import Optional, List

# User CRUD operations
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_google_id(db: Session, google_id: str):
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def create_user(db: Session, email: str, name: str, picture: Optional[str] = None, google_id: Optional[str] = None):
    db_user = models.User(email=email, name=name, picture=picture, google_id=google_id)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, **kwargs):
    db_user = get_user(db, user_id)
    if db_user:
        for key, value in kwargs.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

# Chat message CRUD operations
def get_chat_messages(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.ChatMessage).filter(models.ChatMessage.user_id == user_id).order_by(models.ChatMessage.created_at).offset(skip).limit(limit).all()

def create_chat_message(db: Session, user_id: int, message: str, sender: str):
    db_message = models.ChatMessage(user_id=user_id, message=message, sender=sender)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message