import logging
import os
from typing import List

import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NUM_CLIENTS = int(os.getenv("NUM_CLIENTS", 0))
assert NUM_CLIENTS > 0, "NUM_CLIENTS should be greater than 0"

CLIENTS = [f"client{i}" for i in range(1, NUM_CLIENTS + 1)]

messages: List = []


class Message(BaseModel):
    text: str


@app.get("/")
def get_root():
    return {"message": f"Hello World from MASTER | NUM_CLIENTS: {NUM_CLIENTS}"}


@app.get("/messages")
def get_messages():
    return {"messages": messages}


@app.post("/messages", status_code=201)
def add_messages(message: Message):
    for client in CLIENTS:
        url = f"http://{client}:6001/internal/messages"
        logger.info(f"Sending message to CLIENT#{client}")

        respose = requests.post(url, json={"text": message.text}, timeout=10)
        if respose.status_code != 200:
            return {
                "error": f"Failed to send message to (or get the response from) CLIENT#{client}"
            }

        logger.info(f"Received confirmation from CLIENT#{client}")

    messages.append(message.text)

    return
