import os
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
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


GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

async def verify_signature(request: Request):
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")

    body = await request.body()

    expected_signature = "sha256=" + hmac.new(
        GITHUB_SECRET.encode(), 
        body, 
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")

@app.post('/webhooks/github')
async def handle_github_webhook(request: Request):
        # --- SECURITY CHECK ---
        await verify_signature(request)
        # ----------------------

        payload = await request.json()
        
        # 1. Extract the data we care about
        action = payload.get("action")
        pull_request = payload.get("pull_request", {})
        is_merged = pull_request.get("merged", False)
        
        # 2. Route the event
        if action == "opened":
            print("🔔 ACTION: A new PR was opened!")
            # Later, we will write code here to create the Staging PR
            
        elif action == "closed":
            if is_merged:
                print("✅ ACTION: The PR was successfully merged!")
                # Later, we will send a Slack success message here
            else:
                print("❌ ACTION: The PR was closed without merging. Ignoring.")
                
        else:
            print(f"🤷‍♂️ ACTION: Unhandled event action: {action}")
            
        return {"message": "Webhook processed successfully"}