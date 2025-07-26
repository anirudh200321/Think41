from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI()

# Allow frontend (React on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
users = {}
sessions = {}

class UserCreate(BaseModel):
    username: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str = None

class ChatResponse(BaseModel):
    session_id: str
    response: str

@app.post("/users/")
async def create_user(username: str):
    user_id = str(uuid.uuid4())
    users[user_id] = {"username": username}
    return {"id": user_id}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    if payload.user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")

    session_id = payload.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = []

    sessions[session_id].append({"role": "user", "content": payload.message})
    reply = f"Echo: {payload.message}"  # Replace this with real AI logic
    sessions[session_id].append({"role": "assistant", "content": reply})

    return {"session_id": session_id, "response": reply}
