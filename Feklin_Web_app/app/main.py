from fastapi import FastAPI
from app.routers import router
from app.database import init_db

app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(router)