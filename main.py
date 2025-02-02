import os
from contextlib import asynccontextmanager
from redis.asyncio import Redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.contacts import router as contacts_router
from api.user import router as user_router
from database import Base, engine
from fastapi_limiter import FastAPILimiter

description = """
This is the main entry point of the application.
It sets up FastAPI and includes various routers.

### Available Routes:
- `/contacts` - Manage contacts
- `/user` - Manage users
"""

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis(host="localhost", port=6379, decode_responses=True)
    await FastAPILimiter.init(redis)
    yield
    await redis.close()

app = FastAPI(
    title="goit-pythonweb-hw-012",
    description=description,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contacts_router, prefix="/contacts", tags=["Contacts"])
app.include_router(user_router, prefix="/user", tags=["User"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
