"""
Learning analysis service for generating learning summaries
"""
import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.chat import ChatRecord, LearningSummary
from app.models.user import User
from app.services.ai import ai_service


class LearningAnalysisService:
    """Service for analyzing user learning progress"""
    
    async def process_pending_analysis(self):
        """
        Process pending chat records for learning analysis
        
        This method should be called periodically (e.g., every hour)
        to check for users who have accumulated enough chat records for analysis.
        """
        db = SessionLocal()
        try:
            # Find users with unprocessed chat records >= 100
            users_needing_analysis = (
                db.query(User.id)
                .join(ChatRecord)
                .filter(ChatRecord.is_processed == False)
                .group_by(User.id)
                .having(func.count(ChatRecord.id) >= settings.max_chat_records_per_analysis)
                .all()
            )
            
            logger.info(f"Found {len(users_needing_analysis)} users needing learning analysis")
            
            for (user_id,) in users_needing_analysis:
                try:
                    await self._analyze_user_learning(user_id, db)
                except Exception as e:
                    logger.error(f"Failed to analyze learning for user {user_id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Process pending analysis failed: {e}")
        finally:
            db.close()
    
    async def _analyze_user_learning(self, user_id: str, db: Session):
        """
        Analyze learning progress for a specific user
        
        Args:
            user_id: User ID to analyze
            db: Database session
        """
        try:
            # Get user profile
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for analysis")
                return
            
            # Get unprocessed chat records
            chat_records = (
                db.query(ChatRecord)
                .filter(
                    ChatRecord.user_id == user_id,
                    ChatRecord.is_processed == False
                )
                .order_by(ChatRecord.created_at.desc())
                .limit(settings.max_chat_records_per_analysis)
                .all()
            )
            
            if len(chat_records) < settings.max_chat_records_per_analysis:
                logger.info(f"User {user_id} has only {len(chat_records)} records, skipping analysis")
                return
            
            logger.info(f"Analyzing {len(chat_records)} chat records for user {user_id}")
            
            # Prepare chat records for analysis
            records_for_analysis = []
            for record in chat_records:
                record_data = {
                    "user_input": record.user_input,
                    "ai_correction": record.ai_correction,
                    "correction_type": record.correction_type,
                    "grammar_errors": record.grammar_errors,
                    "created_at": record.created_at.isoformat()
                }
                records_for_analysis.append(record_data)
            
            # Get user profile for analysis context
            user_profile = {
                "age": user.age,
                "gender": user.gender,
                "grade": user.grade,
                "total_usage_time": user.total_usage_time,
                "chat_history_count": user.chat_history_count
            }
            
            # Generate learning summary using AI
            analysis_result = await ai_service.generate_learning_summary(
                chat_records=records_for_analysis,
                user_profile=user_profile
            )
            
            # Calculate analysis period
            start_date = min(record.created_at for record in chat_records)
            end_date = max(record.created_at for record in chat_records)
            analysis_period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            
            # Create learning summary record
            learning_summary = LearningSummary(
                user_id=user_id,
                summary_content=analysis_result.get("summary_content", ""),
                analysis_period=analysis_period,
                record_count=len(chat_records),
                strengths=analysis_result.get("strengths", []),
                weaknesses=analysis_result.get("weaknesses", []),
                recommendations=analysis_result.get("recommendations", []),
                progress_score=analysis_result.get("progress_score", 0),
                analysis_model=analysis_result.get("analysis_model", ""),
                analysis_version=analysis_result.get("analysis_version", "1.0"),
                created_at=datetime.utcnow(),
                is_sent=False
            )
            
            db.add(learning_summary)
            
            # Mark chat records as processed
            batch_id = f"batch_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            for record in chat_records:
                record.is_processed = True
                record.analysis_batch_id = batch_id
            
            db.commit()
            
            logger.info(f"Learning analysis completed for user {user_id}, summary ID: {learning_summary.id}")
            
        except Exception as e:
            logger.error(f"Analyze user learning failed for {user_id}: {e}")
            db.rollback()
            raise
    
    async def get_learning_summaries(self, user_id: str, limit: int = 10) -> List[dict]:
        """
        Get learning summaries for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of summaries to return
            
        Returns:
            List of learning summaries
        """
        db = SessionLocal()
        try:
            summaries = (
                db.query(LearningSummary)
                .filter(LearningSummary.user_id == user_id)
                .order_by(LearningSummary.created_at.desc())
                .limit(limit)
                .all()
            )
            
            results = []
            for summary in summaries:
                results.append(summary.to_dict())
            
            return results
            
        except Exception as e:
            logger.error(f"Get learning summaries failed for {user_id}: {e}")
            return []
        finally:
            db.close()
    
    async def mark_summary_as_sent(self, summary_id: int) -> bool:
        """
        Mark a learning summary as sent to user
        
        Args:
            summary_id: Summary ID
            
        Returns:
            True if successful, False otherwise
        """
        db = SessionLocal()
        try:
            summary = db.query(LearningSummary).filter(LearningSummary.id == summary_id).first()
            if summary:
                summary.is_sent = True
                summary.sent_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Mark summary as sent failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()


# Global learning analysis service instance
learning_analysis_service = LearningAnalysisService()


async def start_learning_analysis_scheduler():
    """
    Start the learning analysis scheduler
    
    This function should be called during application startup
    to begin periodic learning analysis processing.
    """
    logger.info("Starting learning analysis scheduler")
    
    async def analysis_loop():
        while True:
            try:
                await learning_analysis_service.process_pending_analysis()
                # Sleep for 1 hour before next check
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Learning analysis scheduler error: {e}")
                await asyncio.sleep(600)  # Sleep 10 minutes on error
    
    # Start the analysis loop as a background task
    asyncio.create_task(analysis_loop())