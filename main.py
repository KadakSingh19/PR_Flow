from fastapi import FastAPI
from dotenv import load_dotenv
import ngrok

load_dotenv()

app = FastAPI()


@app.on_event("startup")
async def connect_ngrok():
    forwarder = await ngrok.forward(
        "8000",
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
def handle_github_webhook():
    return {"message": "Webhook received successfully"}