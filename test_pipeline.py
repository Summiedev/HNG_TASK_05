#!/usr/bin/env python
"""Test the complete upload -> process -> result pipeline."""

import httpx
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

# Test 1: Health check
print("=" * 60)
print("1️⃣ Testing health endpoint...")
print("=" * 60)
resp = httpx.get(f"{BASE_URL}/api/v1/health")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}\n")

# Test 2: Upload lab_results.png
print("=" * 60)
print("2️⃣ Testing upload endpoint...")
print("=" * 60)

file_path = Path("lab_results.png")
if not file_path.exists():
    print(f"❌ File not found: {file_path.absolute()}")
    print(f"Current dir: {Path.cwd()}")
    print(f"PNG files in current dir: {list(Path('.').glob('*.png'))}")
    exit(1)

print(f"File size: {file_path.stat().st_size} bytes")

with open(file_path, "rb") as f:
    files = {"files": (file_path.name, f, "image/png")}
    resp = httpx.post(f"{BASE_URL}/api/v1/analysis/upload", files=files)
    print(f"Upload status: {resp.status_code}")
    try:
        result = resp.json()
        print(f"Response: {result}\n")
        
        if resp.status_code != 200:
            print(f"❌ Upload failed!")
            exit(1)
            
        analysis_id = result.get("analysis_id")
        print(f"✅ Upload successful! Analysis ID: {analysis_id}\n")
        
        # Test 3: Poll status
        print("=" * 60)
        print("3️⃣ Polling analysis status...")
        print("=" * 60)
        
        max_wait = 120  # 2 minutes
        start = time.time()
        
        for attempt in range(max_wait // 2):
            resp = httpx.get(f"{BASE_URL}/api/v1/analysis/{analysis_id}/status")
            if resp.status_code == 200:
                status_data = resp.json()
                status = status_data.get("status")
                print(f"Attempt {attempt + 1}: Status = {status}")
                
                if status == "completed":
                    print(f"✅ Analysis completed!\n")
                    
                    # Test 4: Fetch result
                    print("=" * 60)
                    print("4️⃣ Fetching analysis result...")
                    print("=" * 60)
                    
                    resp_final = httpx.get(f"{BASE_URL}/api/v1/analysis/{analysis_id}")
                    if resp_final.status_code == 200:
                        final_result = resp_final.json()
                        print(f"Status: {resp_final.status_code}")
                        print(f"\nAnalysis Result:")
                        print(f"  ID: {final_result.get('id')}")
                        print(f"  Status: {final_result.get('status')}")
                        
                        ocr = final_result.get("ocr_result")
                        if ocr:
                            print(f"  OCR Result: {ocr[:200]}..." if len(ocr) > 200 else f"  OCR Result: {ocr}")
                        
                        ai = final_result.get("ai_interpretation")
                        if ai:
                            print(f"  AI Interpretation: {ai[:200]}..." if len(ai) > 200 else f"  AI Interpretation: {ai}")
                        
                        print(f"\n✅ FULL PIPELINE TEST PASSED!")
                    break
                    
                elif status == "failed":
                    print(f"❌ Analysis failed: {status_data.get('error')}")
                    break
            else:
                print(f"⚠️ Status check failed: {resp.status_code}")
            
            time.sleep(2)
        
        if status not in ["completed", "failed"]:
            print(f"⏱️ Timeout waiting for analysis (max: {max_wait}s)")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Response text: {resp.text}")
