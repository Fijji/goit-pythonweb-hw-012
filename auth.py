import os
from datetime import datetime, timedelta, UTC
from typing import Optional
from fastapi import Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import get_db
from models import User
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import load_dotenv

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

class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

async def create_access_token(data: dict, expires_delta: Optional[int] = None):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=expires_delta or 15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def send_verification_email(email: str, token: str, background_tasks: BackgroundTasks):
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"Click the link to verify your email: http://127.0.0.1:8000/user/verify-email?token={token}",
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

async def get_current_user(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
