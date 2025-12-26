from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import team_data

app = FastAPI(
    title="Fantasy Football Prediction API",
    description="An API to provide fantasy football team and player statistics and predictions.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

app.include_router(team_data.router, prefix="/api/v1/team-data", tags=["Team Data"])

@app.get("/")
def root():
    return {"message": "Welcome to the Fantasy Football Prediction API!"}

@app.on_event("startup") 
async def startup_event(): 
    # e.g., connect to database, 
    # load cache 
    print("Starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    # e.g., close DB connection 
    print("Shutting down...")