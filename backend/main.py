from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
import pymongo
from bson import ObjectId
from pydantic_core import core_schema

# --- MongoDB Connection Setup ---
MONGO_CLIENT = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
DB = MONGO_CLIENT["conversation_history_db"]
SESSIONS_COLLECTION = DB["sessions"]
USERS_COLLECTION = DB["users"]

# --- Pydantic Models for Data Schemas ---

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v: Any):
        if not isinstance(v, ObjectId):
            raise TypeError('ObjectId required')
        return v
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any,
    ):
        def validate_from_str(value: str) -> ObjectId:
            if not ObjectId.is_valid(value):
                raise ValueError('Invalid ObjectId')
            return ObjectId(value)
        return core_schema.no_info_after_validator_function(
            validate_from_str,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

class Message(BaseModel):
    role: str  # e.g., "user", "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ConversationSession(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[Message] = []

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
        
class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    username: str
    
    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

# --- New Pydantic Model for the Chat API Request Body ---
class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None


# --- FastAPI Application ---
app = FastAPI()

# A simple function to simulate an AI response
def get_ai_response(user_message: str) -> str:
    # This can be replaced with a call to a real AI model later
    return f"I received your message: '{user_message}'. Thank you for reaching out!"


# --- Milestone 3 Endpoints (unchanged) ---

@app.post("/users/", response_model=User)
async def create_user(username: str):
    user = {"username": username}
    result = USERS_COLLECTION.insert_one(user)
    created_user = USERS_COLLECTION.find_one({"_id": result.inserted_id})
    return created_user

@app.post("/sessions/{user_id}", response_model=ConversationSession)
async def create_session(user_id: str):
    user_obj = USERS_COLLECTION.find_one({"_id": ObjectId(user_id)})
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
    session = {"user_id": user_id, "messages": [], "created_at": datetime.utcnow()}
    result = SESSIONS_COLLECTION.insert_one(session)
    created_session = SESSIONS_COLLECTION.find_one({"_id": result.inserted_id})
    return created_session

@app.post("/sessions/{session_id}/messages/")
async def add_message_to_session(session_id: str, message: Message):
    result = SESSIONS_COLLECTION.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"messages": message.dict()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")
    return {"message": "Message added successfully"}

@app.get("/sessions/{session_id}", response_model=ConversationSession)
async def get_session_history(session_id: str):
    session = SESSIONS_COLLECTION.find_one({"_id": ObjectId(session_id)})
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")
    return session


# --- Milestone 4 Endpoint: Core Chat API ---

@app.post("/api/chat")
async def chat_api(request: ChatRequest):
    session_id_str = request.session_id
    user_message_content = request.message
    
    # 1. Handle user message
    user_message = Message(role="user", content=user_message_content)
    
    # 2. Check for an existing session or create a new one
    if not session_id_str:
        # Create a new session for the user
        session = {"user_id": request.user_id, "messages": [user_message.dict()], "created_at": datetime.utcnow()}
        result = SESSIONS_COLLECTION.insert_one(session)
        session_id_str = str(result.inserted_id)
        
        # Simulate AI response
        ai_response_content = get_ai_response(user_message_content)
        ai_message = Message(role="assistant", content=ai_response_content)
        
        # Append AI response and return
        SESSIONS_COLLECTION.update_one(
            {"_id": ObjectId(session_id_str)},
            {"$push": {"messages": ai_message.dict()}}
        )
        return {"session_id": session_id_str, "response": ai_response_content}
        
    else:
        # Use an existing session
        session = SESSIONS_COLLECTION.find_one({"_id": ObjectId(session_id_str)})
        if not session:
            raise HTTPException(status_code=404, detail=f"Session with ID {session_id_str} not found")
        
        # Push user message to the existing session
        SESSIONS_COLLECTION.update_one(
            {"_id": ObjectId(session_id_str)},
            {"$push": {"messages": user_message.dict()}}
        )
        
        # Simulate AI response
        ai_response_content = get_ai_response(user_message_content)
        ai_message = Message(role="assistant", content=ai_response_content)
        
        # Push AI response to the existing session
        SESSIONS_COLLECTION.update_one(
            {"_id": ObjectId(session_id_str)},
            {"$push": {"messages": ai_message.dict()}}
        )
        
        return {"session_id": session_id_str, "response": ai_response_content}