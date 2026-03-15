from fastapi import FastAPI, WebSocket, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ResumeApply Agent API")

app.add_middleware(CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"])

# Import routers
from routers import resume, agent, websocket
app.include_router(resume.router, prefix="/api/resume")
app.include_router(agent.router, prefix="/api/agent")
app.include_router(websocket.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
