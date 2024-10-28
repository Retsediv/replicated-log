import logging
import os
import random
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
    index: int


messages: List[Message] = []


@app.get("/")
def get_root():
    return {"message": "Hello World from CLIENT", "client_index": client_index}


@app.get("/messages")
def get_messages():
    return {"messages": messages}


@app.post("/internal/messages")
def add_messages(message: Message):
    logger.info(f"Received message: {message.text}")

    sleep_time = random.randrange(1, 15)
    logger.info(f"Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)

    messages.append(message)
    return
