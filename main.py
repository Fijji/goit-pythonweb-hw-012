import os
'''
Main application entry point.
'''
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
- `/users` - Manage users
"""

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="goit-pythonweb-hw-012",
    description=description,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    redis = Redis(host="localhost", port=6379, decode_responses=True)
    await FastAPILimiter.init(redis)

app.include_router(contacts_router, prefix="/contacts", tags=["Contacts"])
app.include_router(user_router, prefix="/user", tags=["User"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
