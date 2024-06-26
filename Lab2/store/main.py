import asyncio
import json
from typing import Set, Dict, List, Any
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Body,
    Depends,
)
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    insert,
    update,
    delete,
    Select,
    func,
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import select
from datetime import datetime
from pydantic import BaseModel, field_validator
from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)
import pydantic_core

import logging

logger = logging.getLogger()
c_handler = logging.StreamHandler()
logger.addHandler(c_handler)
logger.setLevel(logging.INFO)


# FastAPI app setup
app = FastAPI()
# SQLAlchemy setup
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
# Define the ProcessedAgentData table
processed_agent_data = Table(
    "processed_agent_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("road_state", String),
    Column("user_id", String),
    Column("x", Float),
    Column("y", Float),
    Column("z", Float),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("timestamp", DateTime),
)
SessionLocal = sessionmaker(bind=engine)


# SQLAlchemy model
class ProcessedAgentDataInDB(BaseModel):
    id: int
    road_state: str
    user_id: int
    x: float
    y: float
    z: float
    latitude: float
    longitude: float
    timestamp: datetime


# FastAPI models
class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float


class GpsData(BaseModel):
    latitude: float
    longitude: float


class AgentData(BaseModel):
    user_id: str
    accelerometer: AccelerometerData
    gps: GpsData
    timestamp: datetime

    @classmethod
    @field_validator("timestamp", mode="before")
    def check_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid timestamp format. Expected ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)."
            )


class ProcessedAgentData(BaseModel):
    road_state: str
    agent_data: AgentData


# WebSocket subscriptions
subscriptions: Dict[str, Set[WebSocket]] = {}


# FastAPI WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    if user_id not in subscriptions:
        subscriptions[user_id] = set()
    subscriptions[user_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        subscriptions[user_id].remove(websocket)


# Function to send data to subscribed users
async def send_data_to_subscribers(user_id: str, data: List):
    for websocket in subscriptions[user_id]:
        await websocket.send_json(
            json.dumps(data, default=pydantic_core.to_jsonable_python)
        )


async def send_data_websocket(data: List):
    for user_id in subscriptions.keys():
        await send_data_to_subscribers(user_id=user_id, data=data)


# FastAPI CRUD endpoints


@app.post("/processed_agent_data/")
async def create_processed_agent_data(data: List[ProcessedAgentData]):
    values = [
        {
            "road_state": item.road_state,
            "user_id": item.agent_data.user_id,
            "x": item.agent_data.accelerometer.x,
            "y": item.agent_data.accelerometer.y,
            "z": item.agent_data.accelerometer.z,
            "latitude": item.agent_data.gps.latitude,
            "longitude": item.agent_data.gps.longitude,
            "timestamp": item.agent_data.timestamp,
        }
        for item in data
    ]
    query = insert(processed_agent_data).values(values)
    conn = engine.connect()
    _ = conn.execute(query)
    conn.commit()
    # Send data to subscribers
    await send_data_websocket(values)


@app.get(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def read_processed_agent_data(processed_agent_data_id: int):
    db = SessionLocal()
    try:
        q = select(processed_agent_data).where(
            processed_agent_data.c.id == processed_agent_data_id
        )
        res = db.execute(q).fetchone()
        if res:
            return ProcessedAgentDataInDB(
                id=res[0],
                road_state=res[1],
                user_id=res[2],
                x=res[3],
                y=res[4],
                z=res[5],
                latitude=res[6],
                longitude=res[7],
                timestamp=res[8],
            )
        else:
            raise HTTPException(status_code=404, detail="ProcessedAgentData not found")
    finally:
        db.close()


@app.get("/processed_agent_data/", response_model=list[ProcessedAgentDataInDB])
def list_processed_agent_data():
    db = SessionLocal()
    try:
        q = select(processed_agent_data)
        result = db.execute(q).fetchall()
        return [
            ProcessedAgentDataInDB(
                id=s[0],
                road_state=s[1],
                user_id=s[2],
                x=s[3],
                y=s[4],
                z=s[5],
                latitude=s[6],
                longitude=s[7],
                timestamp=s[8],
            )
            for s in result
        ]
    finally:
        db.close()


@app.put(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def update_processed_agent_data(processed_agent_data_id: int, data: ProcessedAgentData):
    values = {
        "road_state": data.road_state,
        "user_id": data.agent_data.user_id,
        "x": data.agent_data.accelerometer.x,
        "y": data.agent_data.accelerometer.y,
        "z": data.agent_data.accelerometer.z,
        "latitude": data.agent_data.gps.latitude,
        "longitude": data.agent_data.gps.longitude,
        "timestamp": data.agent_data.timestamp,
    }
    query = (
        update(processed_agent_data)
        .where(processed_agent_data.c.id == processed_agent_data_id)
        .values(**values)
    )
    conn = engine.connect()
    _ = conn.execute(query)
    conn.commit()


@app.delete(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def delete_processed_agent_data(processed_agent_data_id: int):
    query = delete(processed_agent_data).where(
        processed_agent_data.c.id == processed_agent_data_id
    )
    conn = engine.connect()
    _ = conn.execute(query)
    conn.commit()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
