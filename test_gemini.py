"""
Simple test script to verify Gemini API connection and chat functionality.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import get_settings
import sys

def test_gemini_api():
    """Test basic Gemini API call."""
    print("=" * 60)
    print("Testing Gemini API Connection")
    print("=" * 60)
    
    # Get settings
    settings = get_settings()
    
    if not settings.google_api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables")
        print("\nPlease set your API key:")
        print("  - Create a .env file with: GOOGLE_API_KEY=your_key_here")
        print("  - Or set environment variable: set GOOGLE_API_KEY=your_key_here")
        return False
    
    print(f"✓ API Key found (first 10 chars): {settings.google_api_key[:10]}...")
    
    try:
        # Initialize the model
        print("\nInitializing Gemini model...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.google_api_key,
            temperature=0.7,
        )
        print("✓ Model initialized successfully")
        
        # Test API call
        print("\nSending test message to Gemini...")
        test_message = "Hello! Please respond with 'API connection successful' to confirm you're working."
        
        response = llm.invoke(test_message)
        
        print("✓ API call successful!")
        print("\n" + "-" * 60)
        print("Response from Gemini:")
        print("-" * 60)
        print(response.content)
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during API call: {str(e)}")
        print("\nPossible issues:")
        print("  - Invalid API key")
        print("  - Network connectivity problem")
        print("  - API quota exceeded")
        print("  - Model name incorrect")
        return False


def test_gemini_chat():
    """Test a multi-turn chat conversation with Gemini."""
    print("\n" + "=" * 60)
    print("Testing Gemini Chat Conversation")
    print("=" * 60)
    
    settings = get_settings()
    
    if not settings.google_api_key:
        print("❌ Error: GOOGLE_API_KEY not found")
        return False
    
    try:
        # Initialize the model
        print("\nInitializing chat model...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.google_api_key,
            temperature=0.7,
        )
        print("✓ Chat model initialized")
        
        # Create a conversation with context
        messages = [
            SystemMessage(content="You are a helpful assistant specializing in automotive technology and standards like ASPICE, AUTOSAR, and ISO 26262."),
            HumanMessage(content="What is ASPICE?"),
        ]
        
        print("\n" + "-" * 60)
        print("User: What is ASPICE?")
        print("-" * 60)
        
        response1 = llm.invoke(messages)
        print(f"Assistant: {response1.content}")
        print("-" * 60)
        
        # Continue the conversation
        messages.append(AIMessage(content=response1.content))
        messages.append(HumanMessage(content="Can you give me a brief example of an ASPICE process?"))
        
        print("\nUser: Can you give me a brief example of an ASPICE process?")
        print("-" * 60)
        
        response2 = llm.invoke(messages)
        print(f"Assistant: {response2.content}")
        print("-" * 60)
        
        # One more turn
        messages.append(AIMessage(content=response2.content))
        messages.append(HumanMessage(content="Thanks! That's helpful."))
        
        print("\nUser: Thanks! That's helpful.")
        print("-" * 60)
        
        response3 = llm.invoke(messages)
        print(f"Assistant: {response3.content}")
        print("-" * 60)
        
        print("\n✓ Chat conversation test successful!")
        print(f"✓ Total messages exchanged: {len(messages)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during chat test: {str(e)}")
        return False


if __name__ == "__main__":
    # Test basic API connection
    success = test_gemini_api()
    
    if success:
        # Test chat conversation
        chat_success = test_gemini_chat()
        sys.exit(0 if chat_success else 1)
    else:
        sys.exit(1)
