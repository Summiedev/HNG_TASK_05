import sys
import os
import httpx

BASE = os.environ.get("TEST_BASE", "http://127.0.0.1:8000")


def main():
    img_path = os.path.join(os.path.dirname(__file__), "..", "lab_results.png")
    img_path = os.path.abspath(img_path)
    print("Using image:", img_path)

    with httpx.Client(timeout=30.0) as client:
        try:
            r = client.get(f"{BASE}/")
            print("GET / ->", r.status_code, r.text)
        except Exception as exc:
            print("GET / failed:", exc)

        try:
            r = client.get(f"{BASE}/api/v1/health")
            print("GET /api/v1/health ->", r.status_code, r.text)
        except Exception as exc:
            print("GET /api/v1/health failed:", exc)

        # Try upload
        if not os.path.exists(img_path):
            print("Image not found, aborting upload test")
            return

        files = {"files": (os.path.basename(img_path), open(img_path, "rb"), "image/png")}
        try:
            r = client.post(f"{BASE}/api/v1/analysis/upload", files=files)
            print("POST /api/v1/analysis/upload ->", r.status_code, r.text)
        except Exception as exc:
            print("POST /api/v1/analysis/upload failed:", exc)


if __name__ == "__main__":
    main()
