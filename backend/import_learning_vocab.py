#!/usr/bin/env python3
"""
Import learning_vocab.json from talkai_py to WeChat Mini Program database

This script reads the Python version's learning_vocab.json and imports all vocabulary
entries to the WeChat backend database for a specific user.
"""
import json
import sys
import os
from datetime import datetime, date
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.core.database import create_tables, engine, Base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean


# Define VocabItem model directly to avoid import issues
class VocabItem(Base):
    """Vocabulary item model - simplified for import"""
    __tablename__ = "vocab_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    # Vocabulary data
    word = Column(String, index=True, nullable=False)
    definition = Column(Text, nullable=True)
    phonetic = Column(String, nullable=True)
    translation = Column(Text, nullable=True)
    
    # Learning metadata
    source = Column(String, nullable=True)
    level = Column(String, nullable=True)
    familiarity = Column(Float, default=0.0)
    
    # Learning statistics
    encounter_count = Column(Integer, default=1)
    correct_count = Column(Integer, default=0)
    last_reviewed = Column(DateTime, nullable=True)
    mastery_score = Column(Float, default=0.0)
    
    # Semantic data
    embedding_vector = Column(Text, nullable=True)
    related_words = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_mastered = Column(Boolean, default=False)


def import_learning_vocab_json(user_id: str = "3ed4291004c12c2a", json_file_path: str = None):
    """
    Import learning_vocab.json to database for a specific user
    
    Args:
        user_id: The WeChat user ID to import vocabulary for
        json_file_path: Path to learning_vocab.json file
    """
    
    # Default path to talkai_py learning_vocab.json
    if not json_file_path:
        json_file_path = "/Users/pean/aiproject/talkai_mini/talkai_py/user_words/learning_vocab.json"
    
    json_path = Path(json_file_path)
    if not json_path.exists():
        print(f"❌ Error: learning_vocab.json not found at {json_path}")
        return False
    
    print(f"📖 Reading learning_vocab.json from: {json_path}")
    
    try:
        # Read JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            learning_vocab = json.load(f)
        
        print(f"📊 Found {len(learning_vocab)} vocabulary entries to import")
        
        # Get database session
        create_tables()  # Ensure tables exist
        SessionLocal = sessionmaker(bind=engine)
        db: Session = SessionLocal()
        
        # Clear existing vocabulary for this user
        existing_count = db.query(VocabItem).filter(VocabItem.user_id == user_id).count()
        if existing_count > 0:
            print(f"🗑️  Clearing {existing_count} existing vocabulary entries for user {user_id}")
            db.query(VocabItem).filter(VocabItem.user_id == user_id).delete()
            db.commit()
        
        # Import vocabulary entries
        imported_count = 0
        skipped_count = 0
        
        for item in learning_vocab:
            try:
                # Parse dates
                added_date = None
                if item.get("added_date"):
                    try:
                        added_date = datetime.strptime(item["added_date"], "%Y-%m-%d")
                    except:
                        added_date = datetime.utcnow()
                else:
                    added_date = datetime.utcnow()
                
                last_reviewed = None
                if item.get("last_used"):
                    try:
                        last_reviewed = datetime.strptime(item["last_used"], "%Y-%m-%d")
                    except:
                        pass
                
                # Calculate mastery score (same as Python version logic)
                right_use_count = item.get("right_use_count", 0)
                wrong_use_count = item.get("wrong_use_count", 0)
                mastery_score = right_use_count - wrong_use_count
                is_mastered = item.get("isMastered", False) or mastery_score >= 3
                
                # Create vocabulary item
                vocab_item = VocabItem(
                    user_id=user_id,
                    word=item["word"].lower().strip(),
                    level=item.get("level", "none"),
                    source=item.get("source", "level_vocab"),
                    
                    # Learning statistics (matching Python version)
                    encounter_count=right_use_count + wrong_use_count,
                    correct_count=right_use_count,
                    mastery_score=mastery_score,
                    is_mastered=is_mastered,
                    
                    # Timestamps
                    created_at=added_date,
                    updated_at=datetime.utcnow(),
                    last_reviewed=last_reviewed,
                    
                    # Status
                    is_active=True
                )
                
                db.add(vocab_item)
                imported_count += 1
                
            except Exception as e:
                print(f"⚠️  Skipped word '{item.get('word', 'unknown')}': {e}")
                skipped_count += 1
        
        # Commit all changes
        db.commit()
        db.close()
        
        print(f"✅ Import completed!")
        print(f"   📚 Imported: {imported_count} words")
        print(f"   ⚠️  Skipped: {skipped_count} words")
        print(f"   👤 User ID: {user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def verify_import(user_id: str = "3ed4291004c12c2a"):
    """Verify the imported vocabulary"""
    try:
        SessionLocal = sessionmaker(bind=engine)
        db: Session = SessionLocal()
        
        # Total count
        total_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        # Mastered count
        mastered_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.is_mastered == True
        ).count()
        
        # Sample entries
        sample_entries = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).limit(5).all()
        
        print(f"\n🔍 Verification Results:")
        print(f"   📊 Total vocabulary: {total_count}")
        print(f"   ✅ Mastered: {mastered_count}")
        print(f"   📚 Learning: {total_count - mastered_count}")
        print(f"   📈 Mastery rate: {mastered_count/total_count*100:.1f}%")
        
        print(f"\n📝 Sample entries:")
        for item in sample_entries:
            mastered_status = "✅" if item.is_mastered else "📚"
            print(f"   {mastered_status} {item.word} (level: {item.level}, score: {item.mastery_score})")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting learning_vocab.json import...")
    
    # Default user ID (from our test token)
    default_user_id = "3ed4291004c12c2a"
    
    # Import vocabulary
    if import_learning_vocab_json(default_user_id):
        # Verify import
        verify_import(default_user_id)
        print("\n🎉 Import completed successfully!")
    else:
        print("\n💥 Import failed!")
        sys.exit(1)