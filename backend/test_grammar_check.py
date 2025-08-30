#!/usr/bin/env python3
"""Test grammar check API directly to debug the issue"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.ai import AIService
from app.core.config import settings
import json

def test_grammar_check():
    """Test grammar check with correct sentence"""
    ai_service = AIService()
    
    # Test with the exact sentence from the screenshot
    test_sentence = "I go to school"
    
    print(f"Testing grammar check for: '{test_sentence}'")
    print("=" * 50)
    
    result = ai_service.check_vocab_from_input(test_sentence)
    
    print(f"Raw result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print("=" * 50)
    
    # Check the logic used in chat.py
    corrected_input = result.get("corrected_input")
    is_valid = result.get("is_valid", False)
    
    print(f"corrected_input: '{corrected_input}'")
    print(f"original text: '{test_sentence}'")
    print(f"is_valid: {is_valid}")
    
    # Current backend logic
    has_error_current = corrected_input and corrected_input != test_sentence
    print(f"Current logic (corrected_input and corrected_input != text): {has_error_current}")
    
    # Proposed logic based on is_valid
    has_error_proposed = is_valid
    print(f"Proposed logic (is_valid): {has_error_proposed}")
    
    print("\nShould show correction?")
    print(f"- With current logic: {has_error_current}")
    print(f"- With proposed logic: {has_error_proposed}")

if __name__ == "__main__":
    test_grammar_check()