import concurrent.futures
import enum
import heapq
import logging
import os
import threading
import time
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


class CLIENT_STATUS(enum.Enum):
    LIVE = "live"
    SUSPECTED = "suspected"
    DEAD = "dead"


class ClientsManager(object):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CLIENTS)

    def __init__(self) -> None:
        self._clients: List[int] = [i for i in range(0, NUM_CLIENTS)]

        self._clients_status: List[CLIENT_STATUS] = [
            CLIENT_STATUS.LIVE for _ in range(0, NUM_CLIENTS)
        ]
        self._clients_events: List[threading.Event] = [
            threading.Event() for _ in range(0, NUM_CLIENTS)
        ]

    @property
    def clients(self):
        return self._clients

    @property
    def clients_status(self):
        return self._clients_status

    @property
    def clients_events(self):
        return self._clients_events

    def client_events(self, client_id: int):
        return self._clients_events[client_id]

    def __heartbeats(
        self, client_id: int, min_delay: float = 0.5, max_delay: float = 5.0
    ):
        logger.info(f"Starting heartbeats for CLIENT #{client_id}")

        url = f"{CLIENTS_URL[client_id]}/health"
        timeout = 1.0  # second
        delay = min_delay

        while True:
            good = False

            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    good = True
            except requests.exceptions.RequestException:
                pass

            if good:
                logger.info(f"CLIENT #{client_id} is live")
                delay = min_delay
                self._clients_events[client_id].set()
                self._clients_status[client_id] = CLIENT_STATUS.LIVE

            if not good:
                delay = min(1.25 * delay, max_delay)

                self._clients_events[client_id].clear()

                current_status = self._clients_status[client_id]
                if current_status == CLIENT_STATUS.LIVE:
                    self._clients_status[client_id] = CLIENT_STATUS.SUSPECTED
                    logger.warn(f"CLIENT #{client_id} is suspected to be dead")
                elif current_status == CLIENT_STATUS.SUSPECTED:
                    self._clients_status[client_id] = CLIENT_STATUS.DEAD

                logger.warn(
                    f"CLIENT #{client_id} status is {self._clients_status[client_id]}"
                )

            time.sleep(delay)

    def start_heartbeats(self):
        for client in self._clients:
            self.executor.submit(self.__heartbeats, client)


class MasterLog(object):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CLIENTS + 1)

    def __init__(self) -> None:
        self._messages: List = []
        self._indices: Set = set()
        self._messages_num: int = 0
        self._current_index: int = 0

    def add_message(self, message: Message):
        if message.index in self._indices:
            return

        heapq.heappush(self._messages, (message.index, message.text))
        self._indices.add(message.index)
        self._messages_num += 1

    @property
    def messages(self):
        return list(
            map(lambda x: x[1], heapq.nsmallest(self._messages_num, self._messages))
        )

    @property
    def current_index(self):
        return self._current_index

    def replicate_once(self, message: Message, client_id: int, clients_manager: ClientsManager) -> bool:
        logger.info(
            f"Replicating message '{message.text}' to CLIENT {CLIENTS_HOSTNAME[client_id]}"
        )

        clients_manager.client_events(client_id).wait()
        logger.info(f"CLIENT#{client_id} is live, sending message '{message.text}'")

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

    def replicate_message(self, message: Message, clients_manager: ClientsManager):
        self._current_index += 1
        message.index = self._current_index

        futures = [
            self.executor.submit(self.replicate_once, message, client_id, clients_manager)
            for client_id in range(0, NUM_CLIENTS)
        ]

        min_responses = message.write_concern - 1  # -1 for the master itself
        if min_responses == 0:
            logger.info(
                f"No confirmation is needed, updating internal log state for message {message.text}"
            )
            self.add_message(message)
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

                self.add_message(message)
                return


log = MasterLog()
clients_manager = ClientsManager()


@app.get("/")
def get_root():
    return {"message": f"Hello World from MASTER | NUM_CLIENTS: {NUM_CLIENTS}"}


@app.get("/health")
def get_health():
    return


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

    log.replicate_message(message, clients_manager)
    logger.info(f"Message '{message.text}' has been successfully replicated")

    return


@app.on_event("startup")
def app_startup():
    clients_manager.start_heartbeats()
    logger.info("Heartbeats started")
