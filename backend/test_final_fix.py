#!/usr/bin/env python3
"""Test the final fix for grammar correction logic"""

import requests
import json
import time

def create_test_token():
    """Create a test token by logging in"""
    url = "http://localhost:8000/api/v1/auth/wechat/login"
    data = {
        "js_code": f"test_code_{int(time.time())}",
        "nickname": "Test User", 
        "avatar_url": ""
    }
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Failed to create token: {response.text}")
        return None

def test_grammar_check_api(token, text):
    """Test grammar check API with given text"""
    url = "http://localhost:8000/api/v1/chat/grammar-check"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {"text": text}
    
    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.json() if response.status_code == 200 else response.text

def main():
    print("🔧 Testing grammar correction fix...")
    
    # Get test token
    token = create_test_token()
    if not token:
        print("❌ Failed to get test token")
        return
    
    print(f"✅ Got test token: {token[:20]}...")
    
    # Test cases
    test_cases = [
        "I go to school",           # Should NOT show correction (just punctuation)
        "I goes to school",         # Should show correction (grammar error)
        "I'm interested science",   # Should show correction (missing preposition)
        "Hello, how are you?",      # Should NOT show correction (perfect)
    ]
    
    for text in test_cases:
        print(f"\n📝 Testing: '{text}'")
        print("-" * 50)
        
        status_code, result = test_grammar_check_api(token, text)
        
        if status_code == 200:
            corrected = result.get("corrected_input")
            has_error = result.get("has_error")
            vocab_to_learn = result.get("vocab_to_learn", [])
            
            print(f"✅ API Response:")
            print(f"   corrected_input: '{corrected}'")
            print(f"   has_error: {has_error}")
            print(f"   vocab_to_learn: {len(vocab_to_learn)} items")
            
            if has_error:
                print(f"   🔴 WILL show correction UI")
            else:
                print(f"   🟢 Will NOT show correction UI")
        else:
            print(f"❌ API failed: {result}")

if __name__ == "__main__":
    main()