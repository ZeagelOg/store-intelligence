from fastapi import FastAPI
from app.routers import events, stores

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Store Intelligence"}

@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(events.router, prefix="/events")
app.include_router(stores.router, prefix="/stores")
