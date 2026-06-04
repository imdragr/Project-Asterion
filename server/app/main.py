from fastapi import FastAPI

from app.api.routes import health

app = FastAPI(title="Asterion")
app.include_router(router=health.router)
