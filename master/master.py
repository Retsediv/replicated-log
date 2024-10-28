import concurrent.futures
import heapq
import logging
import os
from threading import Lock
from typing import List, Set

import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NUM_CLIENTS = int(os.getenv("NUM_CLIENTS", 0))
assert NUM_CLIENTS > 0, "NUM_CLIENTS should be greater than 0"

CLIENTS_HOSTNAME = [f"client{i}" for i in range(1, NUM_CLIENTS + 1)]
CLIENTS_URL = [f"http://{client}:6001/" for client in CLIENTS_HOSTNAME]


class Message(BaseModel):
    text: str
    write_concern: int = 1
    index: int = 0


class Log(object):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CLIENTS + 1)

    def __init__(self):
        self._messages: List = []
        self._indices: Set = set()
        self._messages_num: int = 0
        self._current_index: int = 0

        self._lock = Lock()

    def add_message(self, message: str, index: int):
        if index in self._indices:
            return

        heapq.heappush(self._messages, (index, message))
        self._indices.add(index)
        self._messages_num += 1

    @property
    def messages(self):
        return heapq.nsmallest(self._messages_num, self._messages)

    @property
    def current_index(self):
        return self._current_index

    def replicate_once(self, message: Message, client_id: int) -> bool:
        logger.info(
            f"Replicating message '{message.text}' to CLIENT {CLIENTS_HOSTNAME[client_id]}"
        )

        url = f"{CLIENTS_URL[client_id]}/internal/messages"
        respose = requests.post(
            url, json={"text": message.text, "index": message.index}, timeout=100
        )
        if respose.status_code != 200:
            return False

        logger.info(
            f"Received confirmation from CLIENT#{client_id} for message '{message.text}'"
        )

        return True

    def replicate_message(self, message: Message):
        with self._lock:
            self._current_index += 1
            message.index = self._current_index

        futures = [
            self.executor.submit(self.replicate_once, message, client_id)
            for client_id in range(0, NUM_CLIENTS + 0)
        ]

        min_responses = message.write_concern - 1  # -1 for the master itself
        if min_responses == 0:
            logger.info(
                f"No confirmation is needed, updating internal log state for message {message.text}"
            )
            self.add_message(message.text, message.index)
            return

        completed_responses = 0
        for f in concurrent.futures.as_completed(futures):
            response = f.result()
            if response:
                completed_responses += 1

            logger.info(
                f"Message {message.text} | responses: {completed_responses} out of {min_responses}"
            )

            if completed_responses >= min_responses:
                logger.info(
                    f"Received minimum required responses for message {message.text}, updating internal log state."
                )

                self.add_message(message.text, message.index)
                return


log = Log()


@app.get("/")
def get_root():
    return {"message": f"Hello World from MASTER | NUM_CLIENTS: {NUM_CLIENTS}"}


@app.get("/messages")
def get_messages():
    return {"messages": log.messages}


@app.post("/messages", status_code=201)
def add_messages(message: Message):
    logger.info(f"Received message: {message.text}")
    assert (
        message.write_concern <= NUM_CLIENTS + 1
    ), "Write concern should be less than or equal to (NUM_CLIENTS + 1)"
    assert message.write_concern > 0, "Write concern should be greater than 0"

    log.replicate_message(message)
    logger.info(f"Message '{message.text}' has been successfully replicated")

    return
