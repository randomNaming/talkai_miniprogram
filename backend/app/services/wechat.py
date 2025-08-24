"""
WeChat Mini Program authentication service
"""
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config import settings


class WeChatService:
    """WeChat Mini Program service"""
    
    def __init__(self):
        self.app_id = settings.wechat_app_id
        self.app_secret = settings.wechat_app_secret
        self.session_url = "https://api.weixin.qq.com/sns/jscode2session"
        
        # Log configuration status (without exposing secret)
        logger.info(f"WeChat service initialized - AppID: {self.app_id}, Secret: {'***' if self.app_secret else 'Not configured'}")
    
    async def get_session_info(self, js_code: str) -> Optional[Dict[str, Any]]:
        """
        Get session info from WeChat using js_code
        
        Args:
            js_code: Temporary authorization code from WeChat Mini Program
            
        Returns:
            Dict containing openid, session_key, and other info
        """
        if not self.app_id or not self.app_secret:
            logger.error("WeChat app_id or app_secret not configured")
            return None
        
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "js_code": js_code,
            "grant_type": "authorization_code"
        }
        
        try:
            # Create client without proxy to avoid SOCKS issues  
            async with httpx.AsyncClient(
                timeout=30.0,
                trust_env=False  # Don't use environment proxy settings
            ) as client:
                logger.debug(f"Calling WeChat API: {self.session_url}")
                logger.debug(f"Params: appid={self.app_id}, js_code={js_code[:10]}...")
                
                response = await client.get(self.session_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"WeChat API response: {data}")
                
                if "errcode" in data:
                    logger.error(f"WeChat API error: {data}")
                    return None
                
                if not data.get("openid"):
                    logger.error(f"WeChat API returned no openid: {data}")
                    return None
                
                logger.info(f"WeChat authentication successful, openid: {data.get('openid')[:8]}...")
                return {
                    "openid": data.get("openid"),
                    "session_key": data.get("session_key"),
                    "unionid": data.get("unionid")
                }
                
        except Exception as e:
            logger.error(f"Failed to get WeChat session info: {e}")
            return None
    
    async def decrypt_user_info(self, encrypted_data: str, iv: str, session_key: str) -> Optional[Dict[str, Any]]:
        """
        Decrypt WeChat user info (if needed)
        
        This is a placeholder for user info decryption.
        In production, you would implement proper AES decryption here.
        """
        # For now, return None as we'll use basic user info from frontend
        return None


# Global instance
wechat_service = WeChatService()