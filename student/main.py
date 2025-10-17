from fastapi import FastAPI
import os
import requests
import base64
import traceback

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def validate_secret(secret: str) -> bool:
    return secret == os.getenv("secret")

def create_github_repo(repo_name: str):
    payload = {"name": repo_name, 
               "private": False,
               "auto_init": True,
               "license_template": "mit"}
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}

    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=payload
    )

    if response.status_code != 201:  # raise exception only if failed
        raise Exception(f"Failed to create repo: {response.text}")

    return response.json()


def enable_github_pages(repo_name: str):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}
    payload = {
        "build_type": "legacy",
        "source": {"branch": "main", "path": "/"}
    }
    
    response = requests.post(
        f"https://api.github.com/repos/RamDevX/{repo_name}/pages",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 201:
        return response.json()  
    elif response.status_code == 409:
        print("GitHub Pages already enabled, continuing...")
        return None  # already enabled, not an error
    else:
        raise Exception(f"Failed to enable GitHub Pages: {response.text}")

    
def get_sha_of_latest_commit(repo_name: str, branch: str = "main") -> str:
    response = requests.get(f"https://api.github.com/repos/RamDevX/{repo_name}/commits/{branch}")
    if response.status_code != 200:
        raise Exception(f"Failed to get latest commit: {response.text}")
    return response.json().get("sha")

def get_file_sha(repo_name: str, file_path: str, branch: str = "main"):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}
    response = requests.get(
        f"https://api.github.com/repos/RamDevX/{repo_name}/contents/{file_path}?ref={branch}",
        headers=headers
    )
    if response.status_code == 200:
        return response.json().get("sha")
    return None

def push_files_to_repo(repo_name: str, files: list[dict]):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}

    for file in files:
        file_name = file.get("name")
        file_content = file.get("content")

        if isinstance(file_content, bytes):
            file_content = base64.b64encode(file_content).decode('utf-8')
        else:
            file_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

        payload = {
            "message": f"Add {file_name}",
            "content": file_content
        }

        sha = get_file_sha(repo_name, file_name)
        if sha:
            payload["sha"] = sha  # only add sha if file exists

        response = requests.put(
            f"https://api.github.com/repos/RamDevX/{repo_name}/contents/{file_name}",
            headers=headers,
            json=payload
        )
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to push {file_name}: {response.text}")


    
def decode_base64(data: str):
    """Decode base64 string safely by fixing padding."""
    data = data.strip().replace("\n", "")
    missing_padding = len(data) % 4
    if missing_padding:
        data += "=" * (4 - missing_padding)
    return base64.b64decode(data)

def handle_attachments(attachments):
    files = []
    for att in attachments:
        name = att["name"]
        # Split the data URI and decode base64 content safely
        b64_data = att["url"].split(",")[1]  
        content = decode_base64(b64_data)
        files.append({"name": name, "content": content})
    return files


import requests
import json
import os

LLM_API_URL = "https://aipipe.org/openai/v1/chat/completions"
LLM_API_KEY = os.getenv("LLM_API_KEY")

def write_code_to_llm(task: str, brief: str):
    """
    Sends a code generation request to the LLM using OpenAI-compatible API (via aipipe.org).
    Returns a list of code files [{"name": filename, "content": file_content}].
    """

    messages = [
        {
            "role": "system",
            "content": "You are a professional coding assistant that writes complete and runnable code. Always return valid JSON as output."
        },
        {
            "role": "user",
            "content": f"""
You are building code for the following project.

### Task
{task}

### Brief
{brief}

### Rules
1. Write fully functional code — do NOT return an empty stub.
2. Include imports, functions, and logic that run end-to-end.
3. Use standard libraries and well-known packages only (like requests, Pillow, pytesseract).
4. Files can include index.html, app.js, style.css, main.py, or README.md depending on the task.
5. Return your output **strictly as JSON** in this format:

[
  {{
    "name": "main.py",
    "content": "<entire code here>"
  }},
  {{
    "name": "README.md",
    "content": "<documentation here>"
  }}
]

Do not include any explanations, markdown formatting, or extra text outside the JSON.
"""
        }
    ]

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 3000
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(LLM_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"LLM request failed: {response.text}")

    try:
        result = response.json()
        text = result["choices"][0]["message"]["content"].strip()

        # strip ```json ``` wrappers if any
        if text.startswith("```"):
            text = text.split("```")[1]
            text = text.replace("json", "").strip()

        # Parse JSON output
        files = json.loads(text)
        if not isinstance(files, list):
            raise Exception("LLM response is not a JSON array.")

        print("✅ Code successfully generated by LLM.")
        return files

    except Exception as e:
        raise Exception(f"Failed to parse LLM response: {e}")


  



import time
import random
import string

def generate_unique_repo_name(base_name: str) -> str:
    """Generate a unique repo name using timestamp and random suffix."""
    ts = int(time.time())
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{base_name}_{ts}_{suffix}"


def round1(data):
    base_repo_name = f"{data['task']}_{data['nonce']}"
    repo_name = generate_unique_repo_name(base_repo_name)

    create_github_repo(repo_name)
    llm_files = write_code_to_llm(task=data["task"], brief=data.get("brief", ""))
    attachment_files = handle_attachments(data.get("attachments", []))
    files = llm_files + attachment_files
    push_files_to_repo(repo_name, files)
    enable_github_pages(repo_name)

    commit_sha = get_sha_of_latest_commit(repo_name)
    pages_url = f"https://RamDevX.github.io/{repo_name}/"

    payload = {
        "email": data["email"],
        "task": data["task"],
        "round": 1,
        "nonce": data["nonce"],
        "repo_url": f"https://github.com/RamDevX/{repo_name}",
        "commit_sha": commit_sha,
        "pages_url": pages_url
    }

    delay = 1
    for _ in range(5):
        try:
            response = requests.post(data["evaluation_url"], json=payload)
            if response.status_code == 200:
                break
        except Exception as e:
            print(f"Evaluation POST failed: {e}")
        time.sleep(delay)
        delay *= 2


def round2(data):
    base_repo_name = f"{data['task']}_{data['nonce']}"
    repo_name = generate_unique_repo_name(base_repo_name)

    llm_files = write_code_to_llm(task=data["task"], brief=data.get("brief", ""))
    attachment_files = handle_attachments(data.get("attachments", []))
    files = llm_files + attachment_files
    push_files_to_repo(repo_name, files)
    enable_github_pages(repo_name)

    commit_sha = get_sha_of_latest_commit(repo_name)
    pages_url = f"https://RamDevX.github.io/{repo_name}/"

    payload = {
        "email": data["email"],
        "task": data["task"],
        "round": 2,
        "nonce": data["nonce"],
        "repo_url": f"https://github.com/RamDevX/{repo_name}",
        "commit_sha": commit_sha,
        "pages_url": pages_url
    }

    delay = 1
    for _ in range(5):
        try:
            response = requests.post(data["evaluation_url"], json=payload)
            if response.status_code == 200:
                break
        except Exception as e:
            print(f"Evaluation POST failed: {e}")
        time.sleep(delay)
        delay *= 2



    
    
app = FastAPI()

@app.post("/handle_task")
def handle_task(data: dict):
    try:
        if not validate_secret(data.get("secret", "")):
            return {"error": "Invalid secret"}

        round_num = data.get("round")
        if round_num == 1:
            round1(data)
            return {"message": "Round 1 started"}
        elif round_num == 2:
            round2(data)
            return {"message": "Round 2 started"}
        else:
            return {"error": "Invalid round"}

    except Exception as e:
        print("ERROR in handle_task:", e)
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))  # Render sets PORT automatically
    uvicorn.run(app, host="0.0.0.0", port=port)