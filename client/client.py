import heapq
import logging
import os
import random
import time
from typing import List, Set

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
client_index = int(os.getenv("CLIENT_INDEX", "CLIENT_INDEX not set"))


class Message(BaseModel):
    text: str
    index: int


class LogReplica:
    def __init__(self) -> None:
        self._messages: List = []
        self._num_consecutive = 0
        self._total_messages = 0

        self.__buffer_indeces: List = []
        self.__indeces: Set = set()

    @property
    def messages(self):
        return list(
            map(lambda x: x[1], heapq.nsmallest(self._num_consecutive, self._messages))
        )

    @property
    def get_messages(self):
        return self._messages

    def add_message(self, message: Message):
        if message.index in self.__indeces:
            return

        heapq.heappush(self._messages, (message.index, message.text))
        self._total_messages += 1
        self.__indeces.add(message.index)

        # if current index is consecutive to the last index then
        #  increment the counter, else append the index to the buffer
        last_index = self._num_consecutive
        if message.index == last_index + 1:
            self._num_consecutive += 1
        else:
            heapq.heappush(self.__buffer_indeces, message.index)

            # check if the buffer has consecutive index we are missing
            while self.__buffer_indeces:
                if self.__buffer_indeces[0] == last_index + 1:
                    self._num_consecutive += 1
                    heapq.heappop(self.__buffer_indeces)
                else:
                    break


log = LogReplica()


@app.get("/")
def get_root():
    return {"message": "Hello World from CLIENT", "client_index": client_index}


@app.get("/health")
def get_health():
    return


@app.get("/messages")
def get_messages():
    return {"messages": log.messages}


@app.post("/internal/messages")
def add_messages(message: Message):
    logger.info(f"Received message: {message.text}")

    sleep_time = random.randrange(1, 15)
    logger.info(f"Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)

    log.add_message(message)

    return
