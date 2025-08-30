#!/usr/bin/env python3
"""Test the new has_error logic"""

def test_new_logic():
    """Test new has_error logic"""
    
    test_cases = [
        ("I go to school", "I go to school."),         # Just punctuation
        ("I go to school.", "I go to school."),        # No change
        ("I goes to school", "I go to school."),       # Grammar error
        ("I'm interested science", "I'm interested in science."),  # Missing preposition
        ("Hello how are you", "Hello, how are you?"), # Just punctuation
    ]
    
    for original, corrected in test_cases:
        print(f"\nOriginal: '{original}'")
        print(f"Corrected: '{corrected}'")
        
        # New logic
        if corrected and corrected != original:
            # 检查是否只是标点符号差异
            text_no_punct = original.rstrip('.,!?;:')
            corrected_no_punct = corrected.rstrip('.,!?;:')
            is_just_punctuation = text_no_punct == corrected_no_punct
            
            # 只有非标点差异的实质性错误才算has_error
            has_error = not is_just_punctuation
        else:
            has_error = False
        
        print(f"Has substantial error: {has_error}")
        print(f"Should show correction: {has_error}")

if __name__ == "__main__":
    test_new_logic()