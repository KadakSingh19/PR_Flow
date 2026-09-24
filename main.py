

from fastapi import FastAPI,Request
from dotenv import load_dotenv
import ngrok

load_dotenv()

app = FastAPI()


@app.on_event("startup")
async def connect_ngrok():
    forwarder = await ngrok.forward(
        "127.0.0.1:8000",
        authtoken_from_env=True,
        domain="outpost-blooming-onshore.ngrok-free.dev"
    )

    print(f"Available at: {forwarder.url()}")


@app.on_event("shutdown")
async def disconnect_ngrok():
    await ngrok.disconnect()


@app.get("/")
def read_root():
    return {"message": "PRFlow server is running"}


@app.post("/webhooks/github")
async def handle_github_webhook(request: Request):
    payload = await request.json()
    print("Received GitHub webhook" ,payload)
    return {"message": "Webhook received successfully"}