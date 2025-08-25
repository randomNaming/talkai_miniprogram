"""
Text processing utilities for vocabulary management and matching
Ported from talkai_py/utils/utils.py
"""
import re
import spacy
from typing import List, Set, Optional
from sentence_transformers import SentenceTransformer
from loguru import logger

# Try to load spacy model, fallback gracefully if not available
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("Spacy English model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

# Initialize embedding model for semantic similarity
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Failed to initialize embedding model: {e}")
    embedding_model = None

def has_chinese(text: str) -> bool:
    """
    Check if the given text contains Chinese characters.
    
    Args:
        text (str): Text to check
          
    Returns:
        bool: True if text contains Chinese characters, False otherwise
          
    Examples:
        - has_chinese("hello") → False
        - has_chinese("你好") → True  
        - has_chinese("粗心") → True
        - has_chinese("hello你好") → True
    """
    if not text:
        return False
    for char in text:
        # Check if character is in Chinese Unicode range
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def is_collocation(phrase: str) -> bool:
    """
    Determine if a phrase is a fixed collocation (rather than a complete sentence).
    
    Collocation features:
    - Few words (2-4 words)
    - No complete subject+verb structure
    - Common collocation patterns: verb+preposition, adjective+preposition, noun+preposition
    
    Complete sentence features:
    - Contains subject+verb structure
    - Has question words, auxiliary verbs, etc.
    """
    if not nlp:
        # Fallback logic without spacy
        words = phrase.split()
        if len(words) < 2 or len(words) > 5:
            return False
        # Simple heuristic: if contains question words, likely a sentence
        question_words = {"what", "where", "when", "why", "how", "who", "which"}
        return not any(word.lower() in question_words for word in words)
    
    words = phrase.split()
    if len(words) < 2 or len(words) > 5:  # Collocations usually 2-5 words
        return False
    
    doc = nlp(phrase)
    tokens = [token for token in doc if not token.is_punct]
    
    # Check for question words (sentence feature)
    question_words = {"what", "where", "when", "why", "how", "who", "which"}
    if any(token.text.lower() in question_words for token in tokens):
        return False
    
    # Check for subject+verb structure (sentence feature)
    has_subject = False
    has_verb = False
    
    for token in tokens:
        # Check for subject (pronouns, nouns)
        if token.dep_ in ["nsubj", "nsubjpass"] or token.pos_ == "PRON":
            has_subject = True
        # Check for main verb (excluding auxiliary verbs)
        if token.pos_ == "VERB" and token.dep_ in ["ROOT", "cop"]:
            has_verb = True
    
    # If both subject and verb present, likely a sentence
    if has_subject and has_verb:
        return False
    
    # Check common collocation patterns
    pos_tags = [token.pos_ for token in tokens]
    
    # Common collocation patterns
    collocation_patterns = [
        ["VERB", "ADP"],           # look at, depend on
        ["VERB", "ADV", "ADP"],    # look forward to
        ["ADJ", "ADP"],            # interested in, afraid of
        ["NOUN", "ADP"],           # reason for, solution to
        ["VERB", "PART"],          # give up, put on
        ["ADV", "ADJ"],            # very good, quite nice
    ]
    
    # Check if matches any collocation pattern
    for pattern in collocation_patterns:
        if len(pos_tags) >= len(pattern):
            # Check pattern at beginning
            if pos_tags[:len(pattern)] == pattern:
                return True
            # Check pattern at any position
            for i in range(len(pos_tags) - len(pattern) + 1):
                if pos_tags[i:i+len(pattern)] == pattern:
                    return True
    
    return False

def original(word: str) -> str:
    """
    Return the lemmatized (original) form of a word or phrase:
    
    Single words:
    - "playing" → "play"
    - "went" → "go" 
    - "friends" → "friend"
    - "Running" → "run"
    
    Hyphenated compound words (keep intact):
    - "dining-room" → "dining-room"
    - "best-seller" → "best-seller"
    - "well-known" → "well-known"
    
    Fixed collocations (lemmatize each word):
    - "looking forward to" → "look forward to"
    - "interested in" → "interested in"
    - "depending on" → "depend on"
    
    Complete sentences (keep as-is for grammatical correctness):
    - "how are you" → "how are you"
    - "what is your name" → "what is your name"
    - "I am fine" → "I am fine"
    
    Chinese (keep as-is):
    - "你好" → "你好"
    - "您好hello" → "您好hello"
    """
    if not nlp:
        # Fallback without spacy
        return word.lower().strip()
    
    # Check if it's a hyphenated compound word (single token with hyphen)
    if '-' in word and len(word.split()) == 1:
        # For hyphenated compound words, keep as-is but lowercase
        return word.lower()
    
    # Single word processing
    if len(word.split()) == 1:
        doc = nlp(word)
        for token in doc:
            if token.is_alpha:
                return token.lemma_.lower()  # Return lowercase lemma
        return word.lower()
    
    # Multi-word processing: distinguish collocations from sentences
    if is_collocation(word):
        # Fixed collocation: lemmatize each word
        doc = nlp(word)
        lemmatized_words = []
        
        for token in doc:
            if token.is_alpha:
                lemmatized_words.append(token.lemma_.lower())
            elif token.is_space:
                continue  # Skip spaces
            else:
                lemmatized_words.append(token.text.lower())  # Keep prepositions, punctuation
        
        return " ".join(lemmatized_words)
    else:
        # Complete sentence: keep as-is to maintain grammatical correctness
        return word

def find_word_variants_in_text(target_word: str, text: str) -> Optional[str]:
    """
    Intelligent word variant matching that supports:
    - Plural forms: cat→cats, child→children
    - Verb tenses: run→running, go→went, write→written
    - Comparatives/superlatives: big→bigger→biggest
    - Common suffixes: -s, -es, -ed, -ing, -er, -est, -ly
    
    Args:
        target_word: The word to find variants of
        text: The text to search in
        
    Returns:
        The matched word variant found in text, or None if not found
    """
    common_suffixes = ['s', 'es', 'ed', 'ing', 'er', 'est', 'ly', 'tion', 'sion', 'ness', 'ment']
    
    # 1. Exact match
    exact_pattern = r'\b' + re.escape(target_word) + r'\b'
    if re.search(exact_pattern, text, flags=re.IGNORECASE):
        return target_word
    
    # 2. Root matching
    words_in_text = re.findall(r'\b\w+\b', text.lower())
    target_lower = target_word.lower()
    
    for word in words_in_text:
        # Check if word starts with target word
        if word.startswith(target_lower) and len(word) > len(target_lower):
            suffix = word[len(target_lower):]
            if suffix.isalpha() and (suffix in common_suffixes or len(suffix) <= 3):
                return word
        
        # Also check if target word could be a root of the word (more complex matching)
        # For cases like "big" -> "biggest" where we need to handle doubled consonants
        if len(word) > len(target_lower):
            # Handle doubled consonant cases: big->bigger, run->running
            if target_lower.endswith(word[-2]) and word.startswith(target_lower[:-1]):
                return word
            # Handle 'y' to 'i' changes: happy->happier, easy->easier  
            if target_lower.endswith('y') and word.startswith(target_lower[:-1] + 'i'):
                return word
    
    return None

def get_error_type_color(error_type: str) -> str:
    """
    Get color code for different error types (for UI display).
    
    Args:
        error_type: The type of error
        
    Returns:
        Hex color code
    """
    color_map = {
        "translation": "#e74c3c",    # Red - translation error
        "vocabulary": "#f39c12",     # Orange - vocabulary error
        "collocation": "#9b59b6",    # Purple - collocation error
        "grammar": "#2980b9"         # Blue - grammar error
    }
    return color_map.get(error_type, "#e74c3c")

def extract_words_from_text(text: str) -> Set[str]:
    """
    Extract meaningful words from text, excluding simple words.
    
    Args:
        text: Input text
        
    Returns:
        Set of meaningful words (lowercase)
    """
    # Simple words that are too basic for vocabulary learning
    simple_words = {
        'i', 'me', 'my', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its',
        'we', 'us', 'our', 'they', 'them', 'their', 'am', 'is', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'ought',
        'a', 'an', 'the', 'and', 'or', 'but', 'so', 'if', 'as', 'at', 'by', 'for',
        'from', 'in', 'into', 'of', 'on', 'to', 'with', 'about', 'after', 'before',
        'during', 'until', 'while', 'this', 'that', 'these', 'those', 'here', 'there',
        'when', 'where', 'why', 'how', 'what', 'who', 'which', 'whom', 'whose',
        'all', 'any', 'each', 'every', 'no', 'none', 'some', 'such', 'own', 'other',
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'first', 'last', 'next', 'new', 'old', 'good', 'bad', 'big', 'small', 'long',
        'short', 'high', 'low', 'right', 'left', 'up', 'down', 'yes', 'no', 'not',
        'now', 'then', 'today', 'tomorrow', 'yesterday', 'very', 'too', 'so', 'just',
        'only', 'also', 'even', 'still', 'already', 'yet', 'again', 'more', 'most',
        'much', 'many', 'little', 'few', 'less', 'get', 'go', 'come', 'take', 'make',
        'see', 'know', 'think', 'say', 'tell', 'ask', 'give', 'put', 'keep', 'let',
        'help', 'find', 'show', 'use', 'work', 'play', 'live', 'feel', 'look', 'seem'
    }
    
    # Extract words using regex
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter out simple words and short words
    meaningful_words = {word for word in words if len(word) > 2 and word not in simple_words}
    
    return meaningful_words

def calculate_correction_confidence(words_deserve_to_learn: List[dict]) -> float:
    """
    Calculate confidence level for grammar correction based on number and types of errors.
    
    Args:
        words_deserve_to_learn: List of word correction pairs
        
    Returns:
        Confidence level (0.0 to 1.0)
    """
    if not words_deserve_to_learn:
        return 1.0
    
    # Weight different error types
    error_weights = {
        "translation": 0.9,    # High confidence - clear translation errors
        "vocabulary": 0.8,     # Good confidence - vocabulary mistakes
        "grammar": 0.7,        # Medium confidence - grammar issues
        "collocation": 0.6     # Lower confidence - subtle collocation issues
    }
    
    total_weight = 0
    for item in words_deserve_to_learn:
        error_type = item.get("error_type", "vocabulary")
        total_weight += error_weights.get(error_type, 0.7)
    
    # Normalize by number of errors (more errors = lower confidence)
    confidence = max(0.3, 1.0 - (total_weight * 0.1))
    return min(1.0, confidence)

def get_confidence_indicator(confidence_level: float) -> str:
    """
    Get confidence indicator emoji based on confidence level.
    
    Args:
        confidence_level: Confidence level (0.0 to 1.0)
        
    Returns:
        Confidence indicator string
    """
    if confidence_level >= 0.9:
        return "✅"  # High confidence
    elif confidence_level >= 0.7:
        return "⚠️"   # Medium confidence  
    else:
        return "❓"  # Low confidence