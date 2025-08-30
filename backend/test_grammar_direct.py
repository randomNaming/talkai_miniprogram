#!/usr/bin/env python3
"""Test grammar check API by creating token directly"""

import requests
import json
import time
import sys
import os

def main():
    print("🔧 Testing grammar correction fix with direct API call...")
    
    # Use the same approach as debug_profile_simple.py
    from app.core.auth import create_access_token
    
    test_user_id = "test_user_grammar_check"
    test_token = create_access_token(data={"sub": test_user_id})
    
    print(f"✅ Generated test token: {test_token[:30]}...")
    
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
        
        url = "http://localhost:8000/api/v1/chat/grammar-check"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {test_token}"
        }
        data = {"text": text}
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
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
                print(f"❌ API failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    main()