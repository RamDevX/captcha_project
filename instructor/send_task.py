import requests

def send_task():
    """Send a task payload to the local task handler."""
    payload = {
        "email": "24f1000536@ds.study.iitm.ac.in",
        "secret": "ram1234kst",
        "task": "captcha-solver-...",
        "round": 1,
        "nonce": "ab12-...",
        "brief": "Create a captcha solver that handles ?url=https://.../image.png. Default to attached sample.",
        "checks": [
            "Repo has MIT license",
            "README.md is professional",
            "Page displays captcha URL passed at ?url=...",
            "Page displays solved captcha text within 15 seconds",
        ],
        "evaluation_url": "https://example.com/notify",
        "attachments": [
            {
                "name": "sample.png",
                "url": "data:image/png;base64,iVBORw..."
            }
        ]
    }
    response = requests.post("http://localhost:8000/handle_task", json=payload)
    try:
        print(response.json())
    except Exception as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response text: {response.text}")

if __name__ == "__main__":
    send_task()
