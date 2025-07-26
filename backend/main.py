import os
import pymongo
from groq import Groq
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from bson import ObjectId
from pydantic_core import core_schema
from dotenv import load_dotenv

# --- Load environment variables from .env file ---
load_dotenv()

# --- LLM and MongoDB Connection Setup ---
try:
    GROQ_API_KEY = os.environ["GROQ_API_KEY"]
except KeyError:
    raise ValueError("GROQ_API_KEY environment variable not set. Please set it in your .env file.")

client_groq = Groq(api_key=GROQ_API_KEY)

MONGO_CLIENT = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
DB = MONGO_CLIENT["conversation_history_db"]
SESSIONS_COLLECTION = DB["sessions"]
USERS_COLLECTION = DB["users"]
PRODUCTS_COLLECTION = MONGO_CLIENT["ecommerce_db"]["products"]

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
    role: str
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

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None

# --- FastAPI Application ---
app = FastAPI()

# --- Database Query Tool for the LLM ---
def get_products(product_name: str):
    """
    Queries the products database for a product by name.
    """
    product = PRODUCTS_COLLECTION.find_one({"product_name": {"$regex": product_name, "$options": "i"}})
    if product:
        product['_id'] = str(product['_id'])
        return product
    return {"error": f"Product '{product_name}' not found."}


# --- Groq System Prompt and Tool Definition ---
SYSTEM_PROMPT = """You are an e-commerce assistant. Your purpose is to help users with their shopping needs.
You have access to a tool to query a product database.
When a user asks for a specific product, you MUST use the `get_products` tool to search for it.
When you use a tool, you should not generate any text, only a tool call.
If the user's request is ambiguous or you cannot find the product, you should ask a clarifying question.
If the user's query is not related to e-commerce, respond appropriately and politely.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "Get information about a specific product from the e-commerce database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "The name of the product to retrieve.",
                    }
                },
                "required": ["product_name"],
            },
        },
    }
]

# --- Milestone 3 Endpoints ---

@app.post("/users/", response_model=User)
async def create_user(username: str):
    user = {"username": username}
    result = USERS_COLLECTION.insert_one(user)
    created_user = USERS_COLLECTION.find_one({"_id": result.inserted_id})
    created_user['_id'] = str(created_user['_id'])
    return User(**created_user)

@app.post("/sessions/{user_id}", response_model=ConversationSession)
async def create_session(user_id: str):
    user_obj = USERS_COLLECTION.find_one({"_id": ObjectId(user_id)})
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    session = {"user_id": user_id, "messages": [], "created_at": datetime.utcnow()}
    result = SESSIONS_COLLECTION.insert_one(session)
    created_session = SESSIONS_COLLECTION.find_one({"_id": result.inserted_id})
    created_session['_id'] = str(created_session['_id'])
    return ConversationSession(**created_session)

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
    session['_id'] = str(session['_id'])
    return ConversationSession(**session)


# --- Milestone 5 Endpoint: Core Chat API with LLM Integration ---
@app.post("/api/chat")
async def chat_api(request: ChatRequest):
    session_id_str = request.session_id
    user_message_content = request.message
    
    messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if session_id_str:
        try:
            session = SESSIONS_COLLECTION.find_one({"_id": ObjectId(session_id_str)})
            if not session:
                raise HTTPException(status_code=404, detail=f"Session with ID {session_id_str} not found")
            for msg in session.get("messages", []):
                messages_for_llm.append({"role": msg["role"], "content": msg["content"]})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid session_id format.")
    else:
        try:
            user_obj = USERS_COLLECTION.find_one({"_id": ObjectId(request.user_id)})
            if not user_obj:
                raise HTTPException(status_code=404, detail=f"User with ID {request.user_id} not found")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user_id format.")
            
        session_id_str = str(SESSIONS_COLLECTION.insert_one({
            "user_id": request.user_id,
            "messages": [],
            "created_at": datetime.utcnow()
        }).inserted_id)

    messages_for_llm.append({"role": "user", "content": user_message_content})

    try:
        chat_completion = client_groq.chat.completions.with_raw_response.create(
            messages=messages_for_llm,
            model="llama3-8b-8192",
            tools=TOOLS,
            tool_choice="auto"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Groq API: {e}")

    # FIX: Change .parsed to .parse()
    llm_response_message = chat_completion.parse().choices[0].message
    
    ai_response_content = ""
    if llm_response_message.tool_calls:
        tool_call = llm_response_message.tool_calls[0]
        function_name = tool_call.function.name
        
        if function_name == "get_products":
            product_name_arg = eval(tool_call.function.arguments).get("product_name")
            tool_result = get_products(product_name_arg)
            
            messages_for_llm.append(llm_response_message)
            messages_for_llm.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result),
            })
            
            # FIX: Change .parsed to .parse() for the second call
            final_response = client_groq.chat.completions.with_raw_response.create(
                messages=messages_for_llm,
                model="llama3-8b-8192",
            ).parse()
            ai_response_content = final_response.choices[0].message.content
        else:
            ai_response_content = "Sorry, an invalid tool was called."
            
    else:
        ai_response_content = llm_response_message.content

    SESSIONS_COLLECTION.update_one(
        {"_id": ObjectId(session_id_str)},
        {"$push": {"messages": {"$each": [
            {"role": "user", "content": user_message_content, "timestamp": datetime.utcnow()},
            {"role": "assistant", "content": ai_response_content, "timestamp": datetime.utcnow()}
        ]}}}
    )
    
    return {"session_id": session_id_str, "response": ai_response_content}