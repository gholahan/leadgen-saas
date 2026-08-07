from fastapi import FastAPI
from app.core.logger import configure_logging
from app.modules.auth.routes import router as auth_router

configure_logging()

app = FastAPI(title="LeadGen SaaS", version="1.0.0", description="LeadGen SaaS API")
app.include_router(auth_router)

