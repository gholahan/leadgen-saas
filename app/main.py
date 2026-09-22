from fastapi import FastAPI
from app.core.logger import configure_logging
from app.api import api_router

configure_logging()

app = FastAPI(title="LeadGen SaaS", version="1.0.0", description="LeadGen SaaS API")
app.include_router(api_router)

