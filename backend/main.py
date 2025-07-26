from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
import pymongo
from bson import ObjectId
from pydantic_core import core_schema

# --- MongoDB Connection Setup ---
print("Initializing MongoDB connection...")
MONGO_CLIENT = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
DB = MONGO_CLIENT["conversation_history_db"]
SESSIONS_COLLECTION = DB["sessions"]
USERS_COLLECTION = DB["users"]
print("MongoDB connection complete.")

# --- Pydantic Models for Data Schemas ---

# Helper class for MongoDB's ObjectId, compatible with Pydantic v2
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


# --- FastAPI Application ---
print("Creating FastAPI app instance...")
app = FastAPI()
print("FastAPI app instance created.")

# Endpoint to create a new user
@app.post("/users/", response_model=User)
async def create_user(username: str):
    user = {"username": username}
    result = USERS_COLLECTION.insert_one(user)
    created_user = USERS_COLLECTION.find_one({"_id": result.inserted_id})
    return created_user

# Endpoint to create a new conversation session for a user
@app.post("/sessions/{user_id}", response_model=ConversationSession)
async def create_session(user_id: str):
    user_obj = USERS_COLLECTION.find_one({"_id": ObjectId(user_id)})
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
    session = {"user_id": user_id, "messages": [], "created_at": datetime.utcnow()}
    result = SESSIONS_COLLECTION.insert_one(session)
    created_session = SESSIONS_COLLECTION.find_one({"_id": result.inserted_id})
    return created_session

# Endpoint to add a new message to an existing session
@app.post("/sessions/{session_id}/messages/")
async def add_message_to_session(session_id: str, message: Message):
    # This will append the new message to the existing array
    result = SESSIONS_COLLECTION.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"messages": message.dict()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")
    return {"message": "Message added successfully"}

# Endpoint to retrieve the full conversation history for a session
@app.get("/sessions/{session_id}", response_model=ConversationSession)
async def get_session_history(session_id: str):
    session = SESSIONS_COLLECTION.find_one({"_id": ObjectId(session_id)})
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")
    return session