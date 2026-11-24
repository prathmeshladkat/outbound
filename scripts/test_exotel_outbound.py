
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv(".env")

required = [
    "EXOTEL_API_KEY",
    "EXOTEL_API_TOKEN",
    "EXOTEL_ACCOUNT_SID",
    "EXOTEL_API_HOST",
    "EXOTEL_CALLER_ID",
    "EXOTEL_TEST_TO",
    "EXOTEL_STREAM_URL",
]

missing = [key for key in required if not os.getenv(key)]

if missing:
    raise SystemExit(f"Missing environment variables: {missing}")

host = os.environ["EXOTEL_API_HOST"]
sid = os.environ["EXOTEL_ACCOUNT_SID"]

url = f"https://{host}/v1/Accounts/{sid}/Calls/connect"

data = {
    "From": os.environ["EXOTEL_TEST_TO"],
    "CallerId": os.environ["EXOTEL_CALLER_ID"],
    "StreamUrl": os.environ["EXOTEL_STREAM_URL"],
    "StreamType": "bidirectional",
    "Record": "false",
    "TimeLimit": "120",
}

if not data["StreamUrl"].startswith("wss://"):
    raise SystemExit("EXOTEL_STREAM_URL must use wss://")

if "--call" not in sys.argv:
    print("Configuration ready.")
    print("No call placed. Add --call to initiate one.")
    raise SystemExit(0)

with httpx.Client(timeout=30) as client:
    response = client.post(
        url,
        auth=(
            os.environ["EXOTEL_API_KEY"],
            os.environ["EXOTEL_API_TOKEN"],
        ),
        data=data,
    )

print("HTTP status:", response.status_code)

try:
    result = response.json()
    call = result.get("Call")

    if call:
        print("Call SID:", call.get("Sid"))
        print("Call status:", call.get("Status"))
    else:
        print("API response:", result)
except ValueError:
    print("Non-JSON API response, HTTP", response.status_code)

response.raise_for_status()
