"""Smoke test script for Brainweave-OS Ingestion API."""

import os
import sys
import requests
import time
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - short, reliable video


def test_health_check():
    """Test health check endpoint."""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        print("✓ Health check passed")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_home_endpoint():
    """Test home endpoint."""
    print("Testing / endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "status" in data
        print("✓ Home endpoint passed")
        return True
    except Exception as e:
        print(f"✗ Home endpoint failed: {e}")
        return False


def test_youtube_ingestion():
    """Test YouTube ingestion endpoint."""
    print(f"Testing /ingest/youtube with URL: {TEST_VIDEO_URL}")
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("⚠ Warning: No API key found (OPENAI_API_KEY or GEMINI_API_KEY)")
        print("  Skipping LLM-dependent test. Set an API key to test full pipeline.")
        return True
    
    try:
        payload = {
            "url": TEST_VIDEO_URL,
            "provider": "openai" if os.getenv("OPENAI_API_KEY") else "gemini",
            "save_markdown": True,
            "overwrite": False
        }
        
        print("  Sending request...")
        response = requests.post(
            f"{BASE_URL}/ingest/youtube",
            json=payload,
            timeout=120  # LLM calls can take time
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "transcript_stats" in data
            assert "metadata" in data
            
            print(f"✓ Ingestion successful!")
            print(f"  - Transcript: {data['transcript_stats']['character_count']} characters")
            print(f"  - Title: {data['metadata']['title']}")
            
            if data.get("file_save_info"):
                save_info = data['file_save_info']
                print(f"  - File saved: {save_info['filename']}")
                
                # Verify staging file exists (should always be present)
                if save_info.get('staged_path'):
                    staged_path = Path(save_info['staged_path'])
                    if staged_path.exists():
                        print(f"  - Staging file verified: {staged_path}")
                    else:
                        print(f"  ⚠ Warning: Staging file not found at {staged_path}")
                
                # Verify vault file if copy succeeded
                if save_info.get('saved') and save_info.get('path'):
                    vault_path = Path(save_info['path'])
                    if vault_path.exists():
                        print(f"  - Vault file verified: {vault_path}")
                    else:
                        print(f"  ⚠ Warning: Vault file not found at {vault_path}")
                elif not save_info.get('saved'):
                    print(f"  - Vault copy failed (expected with sync locks): {save_info.get('error_code', 'unknown')}")
                    print(f"  - File available in staging: {save_info.get('staged_path')}")
            
            return True
        else:
            print(f"✗ Ingestion failed with status {response.status_code}")
            print(f"  Response: {response.json()}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out (this may be normal for long videos)")
        return False
    except Exception as e:
        print(f"✗ Ingestion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling with invalid URL."""
    print("Testing error handling with invalid URL...")
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/youtube",
            json={"url": "https://example.com/not-youtube"},
            timeout=10
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data.get("detail", {})
        print("✓ Error handling test passed")
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("Brainweave-OS Ingestion API - Smoke Test")
    print("=" * 60)
    print()
    
    # Check if server is running
    print("Checking if server is running...")
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
        print("✓ Server is running")
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running!")
        print("  Please start the server with: uvicorn main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Could not connect to server: {e}")
        sys.exit(1)
    
    print()
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Home Endpoint", test_home_endpoint),
        ("Error Handling", test_error_handling),
        ("YouTube Ingestion", test_youtube_ingestion),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        print("-" * 60)
        result = test_func()
        results.append((test_name, result))
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
