import logging
import os
import time
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
client_index = int(os.getenv("CLIENT_INDEX", "CLIENT_INDEX not set"))


class Message(BaseModel):
    text: str


messages: List[Message] = []


@app.get("/")
def get_root():
    return {"message": "Hello World from CLIENT", "client_index": client_index}


@app.get("/messages")
def get_messages():
    return {"messages": messages}


@app.post("/messages")
def add_messages(message: Message):
    logger.info(f"Received message: {message.text}")

    logger.info(f"Sleeping for {client_index} seconds")
    time.sleep(client_index)

    messages.append(message)
    return
