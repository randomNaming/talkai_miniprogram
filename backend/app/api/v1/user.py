"""
User management API endpoints
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response"""
    id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    grade: Optional[str] = None
    added_vocab_levels: List[str] = []
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None
    total_usage_time: int = 0
    chat_history_count: int = 0
    preferred_ai_model: str = "moonshot-v1-8k"
    vocab_sync_interval: int = 24
    is_active: bool = True
    is_premium: bool = False


class UserProfileUpdateRequest(BaseModel):
    """User profile update request"""
    nickname: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    grade: Optional[str] = None
    added_vocab_levels: Optional[List[str]] = None
    preferred_ai_model: Optional[str] = None
    vocab_sync_interval: Optional[int] = None


class UsageTimeUpdateRequest(BaseModel):
    """Usage time update request"""
    session_duration: int  # seconds


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfileResponse(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            age=user.age,
            gender=user.gender,
            grade=user.grade,
            added_vocab_levels=user.added_vocab_levels or [],
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            total_usage_time=user.total_usage_time or 0,
            chat_history_count=user.chat_history_count or 0,
            preferred_ai_model=user.preferred_ai_model or "moonshot-v1-8k",
            vocab_sync_interval=user.vocab_sync_interval or 24,
            is_active=user.is_active,
            is_premium=user.is_premium
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information
    
    Following talkai_py pattern:
    - When grade is updated, automatically load corresponding vocabulary level
    - Monitor profile changes and update vocabulary accordingly
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 记录是否更新了 grade（用于后续自动加载词汇）
        grade_updated = False
        old_grade = user.grade
        new_grade = None
        
        # Update fields if provided
        if profile_update.nickname is not None:
            user.nickname = profile_update.nickname
        if profile_update.age is not None:
            user.age = profile_update.age
        if profile_update.gender is not None:
            user.gender = profile_update.gender
        if profile_update.grade is not None:
            new_grade = profile_update.grade
            if old_grade != new_grade:
                grade_updated = True
                logger.info(f"User {user_id} grade updated: {old_grade} -> {new_grade}")
            user.grade = new_grade
        if profile_update.added_vocab_levels is not None:
            user.added_vocab_levels = profile_update.added_vocab_levels
        if profile_update.preferred_ai_model is not None:
            user.preferred_ai_model = profile_update.preferred_ai_model
        if profile_update.vocab_sync_interval is not None:
            user.vocab_sync_interval = profile_update.vocab_sync_interval
        
        db.commit()
        db.refresh(user)
        
        # 如果 grade 更新了，清空词汇库并重新初始化（按照需求）
        vocab_load_result = None
        if grade_updated and new_grade:
            try:
                from app.services.vocab_loader import vocab_loader
                from app.models.vocab import VocabItem
                
                logger.info(f"Grade updated from '{old_grade}' to '{new_grade}', clearing and re-initializing vocabulary")
                
                # 1. 清空现有词汇库中的level_vocab类型词汇（保留lookup和wrong_use类型）
                level_vocab_items = db.query(VocabItem).filter(
                    VocabItem.user_id == user_id,
                    VocabItem.source == "level_vocab",
                    VocabItem.is_active == True
                ).all()
                
                cleared_count = len(level_vocab_items)
                for item in level_vocab_items:
                    item.is_active = False  # 软删除
                
                logger.info(f"Cleared {cleared_count} level_vocab items")
                
                # 2. 清空added_vocab_levels记录
                user.added_vocab_levels = []
                
                # 先提交清空操作
                db.commit()
                db.refresh(user)
                
                # 3. 根据新grade初始化词汇库
                vocab_success = vocab_loader.load_vocab_by_grade(user_id, db)
                if vocab_success:
                    vocab_load_result = f"Vocabulary cleared and reinitialized for new grade: {new_grade}"
                    logger.info(f"Successfully reinitialized vocabulary for user {user_id}, grade: {new_grade}")
                else:
                    vocab_load_result = f"Vocabulary cleared but failed to load for {new_grade}"
                    logger.warning(f"Vocabulary for {new_grade} failed to load after clearing")
                    
            except Exception as e:
                logger.error(f"Error handling vocabulary during profile update: {e}")
                vocab_load_result = f"Failed to handle vocabulary update for {new_grade}"
                db.rollback()
                raise
        
        response = UserProfileResponse(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            age=user.age,
            gender=user.gender,
            grade=user.grade,
            added_vocab_levels=user.added_vocab_levels or [],
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            total_usage_time=user.total_usage_time or 0,
            chat_history_count=user.chat_history_count or 0,
            preferred_ai_model=user.preferred_ai_model or "moonshot-v1-8k",
            vocab_sync_interval=user.vocab_sync_interval or 24,
            is_active=user.is_active,
            is_premium=user.is_premium
        )
        
        # 如果有词汇加载结果，添加到响应中
        if vocab_load_result:
            # 可以通过 logger 记录，前端可以通过其他方式获取此信息
            logger.info(f"Profile update completed with vocab result: {vocab_load_result}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user profile failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.post("/usage-time")
async def update_usage_time(
    usage_update: UsageTimeUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's total usage time
    
    This endpoint is called when a user session ends to track learning time.
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Add session duration to total usage time
        user.total_usage_time = (user.total_usage_time or 0) + usage_update.session_duration
        user.last_login_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Usage time updated successfully",
            "total_usage_time": user.total_usage_time,
            "session_duration": usage_update.session_duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update usage time failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update usage time"
        )


@router.get("/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's learning statistics
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get vocabulary count
        from app.models.vocab import VocabItem
        vocab_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        # Get learning summary count
        from app.models.chat import LearningSummary
        summary_count = db.query(LearningSummary).filter(
            LearningSummary.user_id == user_id
        ).count()
        
        # Calculate days since registration
        days_since_registration = 0
        if user.created_at:
            days_since_registration = (datetime.utcnow() - user.created_at).days
        
        return {
            "user_id": user.id,
            "total_usage_time": user.total_usage_time or 0,
            "chat_history_count": user.chat_history_count or 0,
            "vocab_count": vocab_count,
            "learning_summaries": summary_count,
            "days_since_registration": days_since_registration,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "is_premium": user.is_premium,
            "grade": user.grade,
            "preferred_ai_model": user.preferred_ai_model
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )


@router.delete("/account")
async def delete_user_account(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account and all associated data
    
    This is a soft delete - marks the user as inactive.
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete - mark as inactive
        user.is_active = False
        
        # Also mark vocabulary items as inactive
        from app.models.vocab import VocabItem
        db.query(VocabItem).filter(VocabItem.user_id == user_id).update(
            {"is_active": False}
        )
        
        db.commit()
        
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user account failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )


@router.get("/profile/vocab-status-simple")
async def get_vocab_status_simple(
    db: Session = Depends(get_db)
):
    """
    获取词汇状态（简化版本，用于测试，使用默认用户）
    """
    try:
        # 使用默认用户ID
        default_user_id = "3ed4291004c12c2a"
        
        from app.models.vocab import VocabItem
        total_vocab = db.query(VocabItem).filter(
            VocabItem.user_id == default_user_id,
            VocabItem.is_active == True
        ).count()
        
        mastered_vocab = db.query(VocabItem).filter(
            VocabItem.user_id == default_user_id,
            VocabItem.is_active == True,
            VocabItem.isMastered == True  # 使用talkai_py兼容字段名
        ).count()
        
        return {
            "total_vocab_count": total_vocab,
            "mastered_vocab_count": mastered_vocab,
            "unmastered_vocab_count": total_vocab - mastered_vocab,
            "mastery_percentage": (mastered_vocab / total_vocab * 100) if total_vocab > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Get vocab status simple failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vocabulary status"
        )


@router.get("/profile/learning-progress")
async def get_learning_progress(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取学习进度数据，包括每日/每周/每月统计
    """
    try:
        user_id = current_user["sub"]
        
        from app.models.vocab import VocabItem
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        
        # 获取基本词汇统计
        total_vocab = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        mastered_vocab = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.isMastered == True
        ).count()
        
        # 获取最近7天的学习进度
        now = datetime.utcnow()
        weekly_progress = []
        
        for i in range(7):
            day_start = now - timedelta(days=i+1)
            day_end = now - timedelta(days=i)
            
            # 统计当天添加的新词汇
            new_words = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.is_active == True,
                VocabItem.added_date >= day_start,
                VocabItem.added_date < day_end
            ).count()
            
            # 统计当天掌握的词汇（假设通过last_used时间判断）
            mastered_today = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.is_active == True,
                VocabItem.isMastered == True,
                VocabItem.last_used >= day_start,
                VocabItem.last_used < day_end
            ).count()
            
            weekly_progress.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "new_words": new_words,
                "mastered_words": mastered_today,
                "day_name": day_start.strftime("%A")[:3]  # Mon, Tue, etc.
            })
        
        weekly_progress.reverse()  # 按时间正序排列
        
        # 获取本月统计
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_new_words = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.added_date >= month_start
        ).count()
        
        monthly_review_words = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.last_used >= month_start
        ).count()
        
        monthly_mastered_words = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.isMastered == True,
            VocabItem.last_used >= month_start
        ).count()
        
        return {
            "success": True,
            "weekly_progress": weekly_progress,
            "monthly_stats": {
                "newWords": monthly_new_words,
                "reviewWords": monthly_review_words,
                "masteredWords": monthly_mastered_words,
                "month_name": now.strftime("%B %Y")
            },
            "basic_stats": {
                "total_vocab_count": total_vocab,
                "mastered_vocab_count": mastered_vocab,
                "unmastered_vocab_count": total_vocab - mastered_vocab,
                "mastery_percentage": round((mastered_vocab / total_vocab) * 100, 1) if total_vocab > 0 else 0.0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get learning progress failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get learning progress"
        )


@router.get("/vocab-list")
async def get_user_vocab_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的完整词汇列表（用于前端同步）
    
    返回用户所有激活的词汇项，格式兼容前端storage格式
    """
    try:
        user_id = current_user["sub"]
        
        from app.models.vocab import VocabItem
        vocab_items = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).order_by(VocabItem.added_date.desc()).all()
        
        vocab_list = []
        for item in vocab_items:
            vocab_dict = {
                "word": item.word,
                "definition": item.definition or "",
                "phonetic": item.phonetic or "",
                "translation": item.translation or "",
                "source": item.source or "",
                "level": item.level or "",
                "wrong_use_count": item.wrong_use_count or 0,
                "right_use_count": item.right_use_count or 0,
                "isMastered": item.isMastered or False,  # talkai_py兼容字段名
                "added_date": item.added_date.isoformat() if item.added_date else "",
                "last_used": item.last_used.isoformat() if item.last_used else ""
            }
            vocab_list.append(vocab_dict)
        
        return {
            "vocabulary": vocab_list,
            "total_count": len(vocab_list),
            "server_time": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user vocab list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vocabulary list"
        )


@router.get("/vocab-list-simple")
async def get_vocab_list_simple(
    db: Session = Depends(get_db)
):
    """
    获取默认用户的词汇列表（用于测试和前端同步，无需认证）
    """
    try:
        # 使用默认用户ID
        default_user_id = "3ed4291004c12c2a"
        
        from app.models.vocab import VocabItem
        vocab_items = db.query(VocabItem).filter(
            VocabItem.user_id == default_user_id,
            VocabItem.is_active == True
        ).order_by(VocabItem.added_date.desc()).all()
        
        vocab_list = []
        for item in vocab_items:
            vocab_dict = {
                "word": item.word,
                "definition": item.definition or "",
                "phonetic": item.phonetic or "",
                "translation": item.translation or "",
                "source": item.source or "",
                "level": item.level or "",
                "wrong_use_count": item.wrong_use_count or 0,
                "right_use_count": item.right_use_count or 0,
                "isMastered": item.isMastered or False,  # talkai_py兼容字段名
                "added_date": item.added_date.isoformat() if item.added_date else "",
                "last_used": item.last_used.isoformat() if item.last_used else ""
            }
            vocab_list.append(vocab_dict)
        
        return {
            "vocabulary": vocab_list,
            "total_count": len(vocab_list),
            "server_time": datetime.utcnow().isoformat(),
            "user_id": default_user_id
        }
        
    except Exception as e:
        logger.error(f"Get simple vocab list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vocabulary list"
        )


@router.get("/profile/grades")
async def get_available_grades():
    """
    获取所有可用的学习等级列表
    
    返回支持的所有学习等级，用于前端 profile 编辑界面
    """
    try:
        from app.services.vocab_loader import vocab_loader
        
        grades = vocab_loader.get_available_grades()
        grade_info = []
        
        for grade in grades:
            vocab_count = vocab_loader.get_vocab_count_by_grade(grade)
            grade_info.append({
                "grade": grade,
                "vocab_count": vocab_count,
                "description": f"{grade} level vocabulary ({vocab_count} words)"
            })
        
        return {
            "grades": grade_info,
            "total_grades": len(grades)
        }
        
    except Exception as e:
        logger.error(f"Get available grades failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available grades"
        )


@router.post("/profile/load-vocab")
async def manually_load_vocab_by_grade(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动加载当前用户 grade 对应的词汇
    
    这个端点允许用户手动触发词汇加载，复制 talkai_py 的 monitor_profile_changes 功能
    """
    try:
        user_id = current_user["sub"]
        
        from app.services.vocab_loader import vocab_loader
        
        success = vocab_loader.monitor_profile_changes(user_id, db)
        
        if success:
            # 获取用户信息以显示加载的等级
            user = db.query(User).filter(User.id == user_id).first()
            grade = user.grade if user else "Unknown"
            
            return {
                "success": True,
                "message": f"Vocabulary loaded successfully for grade: {grade}",
                "grade": grade
            }
        else:
            return {
                "success": False,
                "message": "Vocabulary not loaded (might already exist or grade not set)",
                "grade": None
            }
        
    except Exception as e:
        logger.error(f"Manually load vocab failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load vocabulary"
        )


@router.get("/profile/vocab-status")
async def get_vocab_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户词汇加载状态
    
    显示用户已加载的词汇等级和统计信息
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 获取已加载的词汇等级
        added_vocab_levels = user.added_vocab_levels or []
        
        # 获取词汇统计
        from app.models.vocab import VocabItem
        total_vocab = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        mastered_vocab = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.isMastered == True  # 使用talkai_py兼容字段名
        ).count()
        
        # 获取各等级词汇数量
        level_vocab_counts = {}
        
        for level in added_vocab_levels:
            count = 0
            
            # 定义多种可能的数据库格式
            possible_formats = [
                level,  # 原格式 "CET4"
                level.lower().replace(" ", "_"),  # 小写下划线 "cet4"
                f"college({level})",  # college格式 "college(CET4)"
                level.lower(),  # 纯小写 "cet4"
            ]
            
            # 如果是Primary School等，添加更多格式
            if " " in level:
                possible_formats.append(level.lower().replace(" ", "_"))  # "primary_school"
            
            # 尝试所有可能的格式
            for db_format in possible_formats:
                count = db.query(VocabItem).filter(
                    VocabItem.user_id == user_id,
                    VocabItem.level == db_format,
                    VocabItem.is_active == True
                ).count()
                
                if count > 0:
                    # logger.info(f"Level {level} found with format: {db_format}, count: {count}")  # 减少日志输出
                    break
            
            if count == 0:
                logger.warning(f"Level {level} not found with any format: {possible_formats}")
            
            level_vocab_counts[level] = count
        
        return {
            "current_grade": user.grade,
            "added_vocab_levels": added_vocab_levels,
            "total_vocab_count": total_vocab,
            "mastered_vocab_count": mastered_vocab,
            "unmastered_vocab_count": total_vocab - mastered_vocab,
            "mastery_percentage": (mastered_vocab / total_vocab * 100) if total_vocab > 0 else 0,
            "level_vocab_counts": level_vocab_counts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get vocab status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vocabulary status"
        )


@router.post("/debug/create-test-user")
async def create_test_user(
    db: Session = Depends(get_db)
):
    """
    创建开发者测试用户
    仅用于开发调试，生产环境应移除
    """
    try:
        import uuid
        
        test_user_id = f"dev_user_{uuid.uuid4().hex[:8]}"
        test_openid = f"test_openid_{uuid.uuid4().hex[:8]}"
        
        # 创建测试用户
        from datetime import datetime
        test_user = User(
            id=test_user_id,
            openid=test_openid,
            nickname="开发者测试用户",
            avatar_url="/images/default_avatar.png",
            age=25,
            gender="Male",
            grade="Primary School",  # 默认等级
            added_vocab_levels=[],
            created_at=datetime.utcnow(),
            last_login_at=datetime.utcnow(),
            total_usage_time=0,
            chat_history_count=0,
            preferred_ai_model="moonshot-v1-8k",
            vocab_sync_interval=24,
            is_active=True,
            is_premium=False
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        logger.info(f"[DEBUG] 创建测试用户: {test_user_id}")
        
        # 自动初始化词汇库
        from app.services.vocab_loader import vocab_loader
        logger.info(f"为测试用户 {test_user_id} 初始化词汇库 (grade: {test_user.grade})")
        vocab_success = vocab_loader.load_vocab_by_grade(test_user_id, db)
        
        # 检查加载结果
        from app.models.vocab import VocabItem
        vocab_count = db.query(VocabItem).filter(
            VocabItem.user_id == test_user_id,
            VocabItem.is_active == True
        ).count()
        
        # 获取词汇示例
        sample_vocabs = db.query(VocabItem).filter(
            VocabItem.user_id == test_user_id,
            VocabItem.is_active == True
        ).limit(5).all()
        
        vocab_examples = [
            {
                "word": v.word,
                "level": v.level,
                "source": v.source
            }
            for v in sample_vocabs
        ]
        
        # 生成测试用的JWT token
        from app.api.v1.auth import create_access_token
        token_data = {
            "sub": test_user_id,
            "openid": test_openid,
            "type": "access_token"
        }
        access_token = create_access_token(data=token_data)

        return {
            "success": True,
            "user_id": test_user_id,
            "openid": test_openid,
            "grade": test_user.grade,
            "vocab_initialized": vocab_success,
            "vocab_count": vocab_count,
            "vocab_examples": vocab_examples,
            "access_token": access_token,
            "token_type": "bearer",
            "message": f"测试用户创建成功，词汇库初始化{'成功' if vocab_success else '失败'}"
        }
        
    except Exception as e:
        logger.error(f"Create test user failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}