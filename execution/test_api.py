"""
API Connection Test Script
Tests connectivity to OpenRouter and local services.
"""
import os
import sys
from pathlib import Path
import httpx

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


def test_openrouter_connection() -> bool:
    """Test OpenRouter API connectivity."""
    print("\n[1] Testing OpenRouter API...")

    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key or api_key == "your_openrouter_api_key_here":
        print("  ERROR: OPENROUTER_API_KEY not configured")
        print("  Please set your API key in backend/.env")
        return False

    try:
        response = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0
        )

        if response.status_code == 200:
            print("  SUCCESS: OpenRouter API is accessible")
            return True
        else:
            print(f"  ERROR: Status {response.status_code}")
            return False

    except httpx.TimeoutException:
        print("  ERROR: Request timed out")
        return False
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False


def test_local_api() -> bool:
    """Test local FastAPI server."""
    print("\n[2] Testing Local API...")

    api_url = f"http://localhost:{os.getenv('API_PORT', 8000)}"

    try:
        response = httpx.get(f"{api_url}/health", timeout=5.0)

        if response.status_code == 200:
            print(f"  SUCCESS: Local API is running at {api_url}")
            return True
        else:
            print(f"  ERROR: Status {response.status_code}")
            return False

    except httpx.ConnectError:
        print(f"  WARNING: Local API not running at {api_url}")
        print("  Start the server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False


def main():
    """Run all connection tests."""
    print("=" * 50)
    print("API Connection Tests")
    print("=" * 50)

    results = {
        "OpenRouter": test_openrouter_connection(),
        "Local API": test_local_api()
    }

    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)

    for service, status in results.items():
        icon = "OK" if status else "FAIL"
        print(f"  [{icon}] {service}")

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
