"""
AI service for chat and grammar correction
"""
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import httpx
from loguru import logger

from app.core.config import settings
from app.utils.prompts import (
    GRAMMAR_CHECK_SYSTEM_PROMPT, 
    BASE_SYSTEM_PROMPT,
    BEGINNER_LEVEL_PROMPT,
    INTERMEDIATE_LEVEL_PROMPT, 
    ADVANCED_LEVEL_PROMPT,
    INITIAL_GREETING_MESSAGE,
    SIMPLE_WORDS
)


class AIService:
    """AI service for chat and grammar correction"""
    
    def __init__(self):
        self.moonshot_api_key = settings.moonshot_api_key
        self.openai_api_key = settings.openai_api_key
        self.model_provider = settings.model_provider
        self.moonshot_model = settings.moonshot_model
        self.openai_model = settings.openai_model
        
        # API endpoints
        self.moonshot_url = "https://api.moonshot.cn/v1/chat/completions"
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        
    def _create_system_prompt(self, user_profile: Dict[str, Any]) -> str:
        """Create system prompt based on user profile"""
        base_prompt = BASE_SYSTEM_PROMPT
        
        # Add level-specific prompts based on user's learning level
        grade = user_profile.get("grade", "").lower()
        level_prompt = ""
        
        if "primary" in grade:
            level_prompt = BEGINNER_LEVEL_PROMPT
        elif "middle" in grade or "high" in grade:
            level_prompt = INTERMEDIATE_LEVEL_PROMPT  
        elif "cet" in grade or "toefl" in grade or "ielts" in grade or "gre" in grade:
            level_prompt = ADVANCED_LEVEL_PROMPT
        
        base_prompt += "\n" + level_prompt
        
        # Add user profile information if available
        if user_profile:
            user_info = "\nUser information:\n"
            
            if user_profile.get("age"):
                user_info += f"- Age: {user_profile['age']}\n"
                
            if user_profile.get("gender"):
                user_info += f"- Gender: {user_profile['gender']}\n"
                
            base_prompt += user_info
            base_prompt += "Adapt your language complexity and topics to match the user's age, grade and English level.\n"
        
        return base_prompt
    
    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    async def _call_moonshot_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        """Call Moonshot API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.moonshot_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.moonshot_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1000
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.moonshot_url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Moonshot API call failed: {e}")
            return None
    
    async def _call_openai_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        """Call OpenAI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.openai_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1000
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.openai_url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return None
    
    async def _call_ai_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        """Call AI API based on configured provider"""
        if self.model_provider == "openai" and self.openai_api_key:
            return await self._call_openai_api(messages, temperature)
        elif self.moonshot_api_key:
            return await self._call_moonshot_api(messages, temperature)
        else:
            logger.error("No API key configured for AI service")
            return None
    
    async def check_grammar_and_vocabulary(self, user_input: str) -> Dict[str, Any]:
        """
        Check grammar and identify vocabulary to learn
        
        Args:
            user_input: User's input text
            
        Returns:
            Dict containing corrected input and vocabulary to learn
        """
        try:
            messages = [
                {"role": "system", "content": GRAMMAR_CHECK_SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
            
            response = await self._call_ai_api(messages, temperature=0.3)
            
            if not response:
                return {
                    "corrected_input": user_input,
                    "has_error": False,
                    "vocab_to_learn": []
                }
            
            try:
                # Try to parse JSON response
                result = json.loads(response)
                
                # Validate required fields
                if "corrected_input" not in result:
                    result["corrected_input"] = user_input
                if "has_error" not in result:
                    result["has_error"] = False
                if "vocab_to_learn" not in result:
                    result["vocab_to_learn"] = []
                
                return result
                
            except json.JSONDecodeError:
                # If not valid JSON, treat as plain text correction
                return {
                    "corrected_input": response.strip(),
                    "has_error": response.strip() != user_input,
                    "vocab_to_learn": []
                }
                
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return {
                "corrected_input": user_input,
                "has_error": False,
                "vocab_to_learn": []
            }
    
    async def generate_chat_response(
        self, 
        user_input: str, 
        user_profile: Dict[str, Any], 
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate chat response for conversation practice
        
        Args:
            user_input: User's input text
            user_profile: User profile information
            conversation_history: Previous conversation messages
            
        Returns:
            AI-generated response
        """
        try:
            # Create system prompt based on user profile
            system_prompt = self._create_system_prompt(user_profile)
            
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if available
            if conversation_history:
                # Limit history to last few turns to avoid token limit
                recent_history = conversation_history[-settings.max_memory_turns * 2:]
                messages.extend(recent_history)
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Generate response
            response = await self._call_ai_api(messages, temperature=0.8)
            
            if not response:
                return "I'm having trouble connecting right now. Could you please try again?"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            return "I'm sorry, I encountered an error. Please try again."
    
    async def generate_learning_summary(
        self, 
        chat_records: List[Dict[str, Any]], 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate learning summary from chat records
        
        Args:
            chat_records: List of chat records for analysis
            user_profile: User profile information
            
        Returns:
            Dict containing learning summary and insights
        """
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            You are an English learning progress analyzer. Analyze the following conversation records and provide a learning summary.

            User Profile:
            - Grade/Level: {user_profile.get('grade', 'Unknown')}
            - Age: {user_profile.get('age', 'Unknown')}

            Conversation Records ({len(chat_records)} entries):
            """
            
            # Add conversation samples
            for i, record in enumerate(chat_records[:20]):  # Limit to first 20 for prompt size
                analysis_prompt += f"\n{i+1}. User: {record.get('user_input', '')}"
                if record.get('ai_correction'):
                    analysis_prompt += f"\n   Correction: {record['ai_correction']}"
            
            if len(chat_records) > 20:
                analysis_prompt += f"\n... and {len(chat_records) - 20} more entries"
            
            analysis_prompt += """

            Please provide a comprehensive learning analysis in JSON format:
            {
              "summary_content": "Overall learning progress summary",
              "strengths": ["strength1", "strength2", "strength3"],
              "weaknesses": ["weakness1", "weakness2", "weakness3"],
              "recommendations": ["recommendation1", "recommendation2", "recommendation3"],
              "progress_score": 75
            }

            Progress score should be 0-100 based on improvement, consistency, and error reduction.
            """
            
            messages = [
                {"role": "system", "content": "You are an expert English learning analyst."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = await self._call_ai_api(messages, temperature=0.5)
            
            if not response:
                return self._get_default_summary(len(chat_records))
            
            try:
                result = json.loads(response)
                
                # Validate and set defaults
                result["record_count"] = len(chat_records)
                result["analysis_model"] = self.moonshot_model if self.model_provider != "openai" else self.openai_model
                result["analysis_version"] = "1.0"
                
                return result
                
            except json.JSONDecodeError:
                # Fallback to simple text summary
                return {
                    "summary_content": response.strip(),
                    "strengths": [],
                    "weaknesses": [],
                    "recommendations": [],
                    "progress_score": 70,
                    "record_count": len(chat_records),
                    "analysis_model": self.moonshot_model if self.model_provider != "openai" else self.openai_model,
                    "analysis_version": "1.0"
                }
                
        except Exception as e:
            logger.error(f"Learning summary generation failed: {e}")
            return self._get_default_summary(len(chat_records))
    
    def _get_default_summary(self, record_count: int) -> Dict[str, Any]:
        """Get default summary when AI analysis fails"""
        return {
            "summary_content": f"Learning summary based on {record_count} conversation records. Keep practicing to improve your English skills!",
            "strengths": ["Active participation in conversations", "Willingness to learn"],
            "weaknesses": ["Analysis temporarily unavailable"],
            "recommendations": ["Continue practicing daily", "Focus on grammar accuracy", "Expand vocabulary"],
            "progress_score": 60,
            "record_count": record_count,
            "analysis_model": "fallback",
            "analysis_version": "1.0"
        }
    
    def get_initial_greeting(self) -> str:
        """Get initial greeting message"""
        return INITIAL_GREETING_MESSAGE


# Global AI service instance
ai_service = AIService()