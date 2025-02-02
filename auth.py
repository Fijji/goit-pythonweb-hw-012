import json
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import BackgroundTasks
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS") == "True",
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS") == "True",
)
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify if a plain password matches its hashed version."""
        return Hash.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate a bcrypt hash for a given password."""
        return Hash.pwd_context.hash(password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

async def create_access_token(data: dict, expires_delta: int = None):
    """Generate a JWT token with a valid expiration time."""
    to_encode = data.copy()
    if "email" not in to_encode:
        raise ValueError("Missing 'email' field in token payload")
    if expires_delta is None:
        expires_delta = timedelta(minutes=15)
    elif isinstance(expires_delta, int):
        expires_delta = timedelta(seconds=expires_delta)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"sub": to_encode["email"], "exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """Decodes and verifies a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if "sub" not in payload:
            raise ValueError("Invalid token: No 'sub' found")

        return payload
    except JWTError:
        raise ValueError("Invalid token")

async def send_verification_email(email: str, token: str, background_tasks: BackgroundTasks):
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"Click the link to verify your email: http://127.0.0.1:8000/user/verify-email?token={token}",
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

def send_password_reset_email(email: str, token: str):
    """Sends a password reset email with a secure token."""
    reset_url = f"http://127.0.0.1:8000/reset-password?token={token}"
    msg = MIMEText(f"Click the link to reset your password: {reset_url}")
    msg["Subject"] = "Password Reset Request"
    msg["From"] = SMTP_USERNAME
    msg["To"] = email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

async def get_current_user(token: str, db: Session = Depends(get_db)):
    """
    Get user from Redis cache or database.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    cached_user = await redis_client.get(f"user:{email}")
    if cached_user:
        return json.loads(cached_user)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }
    await redis_client.set(f"user:{email}", json.dumps(user_data), ex=600)

    return user_data

async def is_admin(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admins only"
        )
    return current_user

