"""
Test script for /api/chat endpoint
"""
import requests
import json
import sys
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/chat"

def print_separator(char="="):
    print(char * 70)

def test_chat_endpoint():
    """Test the /api/chat endpoint with various messages."""
    
    print_separator()
    print("Testing /api/chat Endpoint")
    print_separator()
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint: {CHAT_ENDPOINT}\n")
    
    # Test cases
    test_messages = [
        {
            "message": "What is ASPICE?",
            "session_id": "test_session_1",
            "k": 5
        },
        {
            "message": "Can you explain ISO 26262?",
            "session_id": "test_session_1",
            "k": 5
        },
        {
            "message": "What is AUTOSAR?",
            "session_id": "test_session_2",
            "k": 3
        }
    ]
    
    try:
        # Check if server is running
        print("Checking server health...")
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✓ Server is running\n")
        else:
            print(f"⚠ Server returned status code: {health_response.status_code}\n")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server")
        print(f"   Make sure the FastAPI server is running on {BASE_URL}")
        print("   Run: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}\n")
        return False
    
    # Test each message
    for i, test_data in enumerate(test_messages, 1):
        print_separator("-")
        print(f"Test {i}/{len(test_messages)}")
        print_separator("-")
        print(f"Session ID: {test_data['session_id']}")
        print(f"Message: {test_data['message']}")
        print(f"k (chunks to retrieve): {test_data['k']}")
        
        try:
            # Send POST request
            print("\nSending request...")
            response = requests.post(
                CHAT_ENDPOINT,
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # Check response status
            if response.status_code == 200:
                print("✓ Request successful (200 OK)")
                
                # Parse response
                result = response.json()
                
                print("\n" + "─" * 70)
                print("RESPONSE:")
                print("─" * 70)
                print(f"Answer:\n{result['answer']}\n")
                print(f"Chunks Retrieved: {result['chunks_retrieved']}")
                print(f"Domain Terms Used: {result['domain_terms_used']}")
                
                if result['sources']:
                    print(f"\nSources ({len(result['sources'])}):")
                    for idx, source in enumerate(result['sources'], 1):
                        print(f"  {idx}. {source['filename']}")
                        print(f"     Document ID: {source['document_id']}")
                        print(f"     Relevance Score: {source['relevance_score']}")
                else:
                    print("\nSources: No sources found")
                
                print("─" * 70)
                
            else:
                print(f"❌ Request failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out (>30s)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response.text}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        print()
    
    print_separator()
    print("Test completed!")
    print_separator()
    return True


def test_simple_chat():
    """Quick test with a single message."""
    print_separator()
    print("Quick Chat Test")
    print_separator()
    
    test_message = {
        "message": "Hello! What can you help me with?",
        "session_id": "quick_test",
        "k": 3
    }
    
    try:
        print(f"Sending: '{test_message['message']}'\n")
        response = requests.post(
            CHAT_ENDPOINT,
            json=test_message,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Response received:")
            print(f"\n{result['answer']}\n")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n")
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        success = test_simple_chat()
    else:
        success = test_chat_endpoint()
    
    print("\nUsage:")
    print("  python test_chat_api.py         # Run full test suite")
    print("  python test_chat_api.py --quick # Quick single message test")
    print()
    
    sys.exit(0 if success else 1)
