import os
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
import ngrok
import httpx

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

async def create_staging_pr(repo_full_name: str, head_branch: str, original_title: str):
    url = f"https://api.github.com/repos/{repo_full_name}/pulls"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "title": f"Staging: {original_title}",
        "head": head_branch,
        "base": "staging"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            new_pr_data = response.json()
            staging_pr_url = new_pr_data.get("html_url")
            print(f"✅ Successfully created Staging PR: {staging_pr_url}")
            return staging_pr_url
        else:
            print(f"❌ Failed to create Staging PR: {response.text}")
            return None

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
        print(action, is_merged)
        # 2. Route the event
        if action == "opened":
            print("🔔 ACTION: A new PR was opened!")
            
            base_branch = pull_request.get("base", {}).get("ref")
            head_branch = pull_request.get("head", {}).get("ref")
            repo_full_name = payload.get("repository", {}).get("full_name")
            original_title = pull_request.get("title", "Untitled PR")
            
            print(f"Someone wants to merge '{head_branch}' into '{base_branch}' in {repo_full_name}")
            
            if base_branch == "main":
                print("We need to create a staging PR for this!")
                staging_url = await create_staging_pr(repo_full_name, head_branch, original_title)
            else:
                print("Base branch is not 'main', ignoring.")
            
        elif action == "closed":
            if is_merged:
                print("✅ ACTION: The PR was successfully merged!")
                # Later, we will send a Slack success message here
            else:
                print("❌ ACTION: The PR was closed without merging. Ignoring.")
        elif action == "reopened":
            print("🔄 ACTION: The PR was reopened!")
            # Later, we will write code here to re-create the Staging PR        
        else:
            print(f"🤷‍♂️ ACTION: Unhandled event action: {action}")
            
        return {"message": "Webhook processed successfully"}