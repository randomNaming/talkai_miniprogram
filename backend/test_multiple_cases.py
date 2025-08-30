#!/usr/bin/env python3
"""Test multiple grammar check cases to understand the pattern"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.ai import AIService
import json

def test_multiple_cases():
    """Test grammar check with various sentences"""
    ai_service = AIService()
    
    test_cases = [
        "I go to school",           # Perfect sentence (missing punctuation)
        "I go to school.",          # Perfect sentence with punctuation  
        "I goes to school",         # Grammar error
        "I'm interested science",   # Missing preposition
        "Hello how are you",        # Missing punctuation
        "Hello, how are you?",      # Perfect with punctuation
    ]
    
    for sentence in test_cases:
        print(f"\nTesting: '{sentence}'")
        print("-" * 40)
        
        result = ai_service.check_vocab_from_input(sentence)
        
        corrected_input = result.get("corrected_input")
        is_valid = result.get("is_valid", False)
        words_to_learn = result.get("words_deserve_to_learn", [])
        explanation = result.get("explanation", "")
        
        print(f"corrected_input: '{corrected_input}'")
        print(f"is_valid: {is_valid}")
        print(f"words_to_learn: {len(words_to_learn)} items")
        print(f"explanation: '{explanation}'")
        
        # Check if it's just punctuation difference
        is_just_punctuation = (
            corrected_input and 
            corrected_input.rstrip('.,!?;:') == sentence.rstrip('.,!?;:')
        )
        
        print(f"Is just punctuation difference: {is_just_punctuation}")
        
        # Current logic
        has_error_current = corrected_input and corrected_input != sentence
        print(f"Would show correction (current): {has_error_current}")
        
        # Proposed logic - ignore pure punctuation differences
        has_substantial_error = (
            corrected_input and 
            corrected_input != sentence and 
            not is_just_punctuation
        )
        print(f"Would show correction (substantial errors only): {has_substantial_error}")

if __name__ == "__main__":
    test_multiple_cases()