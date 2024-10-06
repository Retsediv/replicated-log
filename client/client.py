import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def get_root():
    client_index = os.getenv("CLIENT_INDEX", "CLIENT_INDEX not set")
    return {"message": "Hello World from CLIENT", "client_index": client_index}

print("Client is running")

