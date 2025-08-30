"""
Authentication API endpoints
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import create_access_token, generate_user_id, get_current_user
from app.services.wechat import wechat_service
from app.models.user import User

router = APIRouter()


class WeChatLoginRequest(BaseModel):
    """WeChat login request"""
    js_code: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    is_new_user: bool


@router.post("/wechat/login", response_model=LoginResponse)
async def wechat_login(
    login_data: WeChatLoginRequest,
    db: Session = Depends(get_db)
):
    """
    WeChat Mini Program login
    
    This endpoint handles WeChat Mini Program authentication.
    It exchanges the js_code for user's openid and creates/updates user record.
    """
    try:
        # Get session info from WeChat
        session_info = await wechat_service.get_session_info(login_data.js_code)
        
        if not session_info or not session_info.get("openid"):
            # TEMPORARY FIX: Create mock session for development/testing
            if login_data.js_code and login_data.js_code.startswith("0") and len(login_data.js_code) > 20:
                logger.warning(f"Using temporary mock session for development - js_code: {login_data.js_code[:10]}...")
                session_info = {
                    "openid": "dev_openid_fixed_development_user",  # 固定开发环境用户
                    "session_key": "dev_session_key",
                    "unionid": None
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid WeChat authorization code"
                )
        
        openid = session_info["openid"]
        user_id = generate_user_id(openid)
        
        # Check if user exists
        user = db.query(User).filter(User.openid == openid).first()
        is_new_user = user is None
        
        if is_new_user:
            # Create new user
            user = User(
                id=user_id,
                openid=openid,
                nickname=login_data.nickname,
                avatar_url=login_data.avatar_url,
                created_at=datetime.utcnow(),
                last_login_at=datetime.utcnow(),
                
                # Default profile settings (matching original user_profiles.json)
                age=None,
                gender=None,
                grade="Primary School",  # Default grade
                added_vocab_levels=["Primary School"],
                
                # Initialize counters
                total_usage_time=0,
                chat_history_count=0,
                
                # Default preferences
                preferred_ai_model="moonshot-v1-8k",
                vocab_sync_interval=24,
                
                # Status
                is_active=True,
                is_premium=False
            )
            db.add(user)
            logger.info(f"Created new user: {user_id}")
            
            # 新用户首次登录：自动初始化词汇库
            db.commit()  # 先提交用户创建
            db.refresh(user)
            
            # 根据默认grade (Primary School) 自动加载词汇
            try:
                from app.services.vocab_loader import vocab_loader
                logger.info(f"为新用户 {user_id} 初始化词汇库 (grade: {user.grade})")
                vocab_success = vocab_loader.load_vocab_by_grade(user_id, db)
                if vocab_success:
                    logger.info(f"新用户 {user_id} 词汇库初始化成功")
                else:
                    logger.warning(f"新用户 {user_id} 词汇库初始化失败")
            except Exception as e:
                logger.error(f"新用户词汇库初始化失败: {e}")
        else:
            # Update existing user
            user.last_login_at = datetime.utcnow()
            if login_data.nickname:
                user.nickname = login_data.nickname
            if login_data.avatar_url:
                user.avatar_url = login_data.avatar_url
            logger.info(f"User login: {user_id}")
            
            db.commit()
            db.refresh(user)
        
        # Create access token
        token_data = {
            "sub": user.id,
            "openid": user.openid,
            "type": "access_token"
        }
        access_token = create_access_token(data=token_data)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            is_new_user=is_new_user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WeChat login failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout():
    """
    Logout endpoint
    
    For JWT tokens, logout is typically handled on client side
    by simply discarding the token.
    """
    return {"message": "Logged out successfully"}


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify token validity
    """
    return {
        "valid": True,
        "user_id": current_user["sub"],
        "openid": current_user.get("openid")
    }


