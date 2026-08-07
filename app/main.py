from fastapi import FastAPI
from app.core.logger import configure_logging

configure_logging()

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}