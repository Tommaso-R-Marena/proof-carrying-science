"""One public synthetic batch; never retries. Credential is read without echo."""
import getpass
import hashlib
import json
import os
from pathlib import Path
from urllib import error, request

HERE = Path(__file__).resolve().parent
MODEL = "gemini-3.5-flash-lite"
URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"
cfg = {"temperature": 0, "maxOutputTokens": 1536, "responseMimeType": "application/json"}
content = (HERE / "instruction.txt").read_text() + (HERE / "prompts.json").read_text()
payload = json.dumps({"contents": [{"parts": [{"text": content}]}], "generationConfig": cfg}).encode()
ledger = {"model": MODEL, "payload_sha256": hashlib.sha256(payload).hexdigest(),
          "generation": cfg, "attempts": 1, "retries": 0, "free_tier": "user confirmed"}
if __name__ == "__main__":
    out = Path(os.sys.argv[1])
    with out.open("x") as receipt:
        key = os.environ.get("GEMINI_API_KEY") or getpass.getpass("Credential: ")
        req = request.Request(URL, data=payload, headers={"Content-Type": "application/json", "X-goog-api-key": key})
        try:
            with request.urlopen(req, timeout=90) as resp:
                data = json.load(resp)
                ledger.update(status=resp.status, modelVersion=data.get("modelVersion"),
                              usage=data.get("usageMetadata"), candidates=data.get("candidates", []))
        except error.HTTPError as exc:
            ledger.update(status=exc.code)
        finally:
            json.dump(ledger, receipt, indent=2, sort_keys=True)
            receipt.write("\n")
    print("HTTP status", ledger.get("status"))
