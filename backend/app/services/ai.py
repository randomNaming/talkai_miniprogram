"""
AI service for chat and grammar correction - Enhanced with LangChain integration
Ported from talkai_py/language_model.py
"""
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import httpx
import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

# LangChain imports (same as talkai_py)
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOpenAI as CommunityOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Conversation memory: handle both old and new LangChain layouts
try:
    # Older LangChain versions
    from langchain.memory import ConversationBufferWindowMemory  # type: ignore
except ImportError:  # pragma: no cover
    from collections import deque

    class ConversationBufferWindowMemory:
        """
        Minimal fallback implementation compatible with the subset of
        LangChain's ConversationBufferWindowMemory that this project uses.
        """

        def __init__(
            self,
            return_messages: bool = True,
            memory_key: str = "chat_history",
            input_key: str = "human_input",
            output_key: str = "ai_output",
            k: int = 3,
        ):
            self.return_messages = return_messages
            self.memory_key = memory_key
            self.input_key = input_key
            self.output_key = output_key
            self.k = k
            self._buffer = deque(maxlen=2 * k)

        def load_memory_variables(self, _: dict) -> dict:
            # Project expects a dict with "chat_history" -> List[BaseMessage-like]
            return {self.memory_key: list(self._buffer)}

        def save_context(self, inputs: dict, outputs: dict) -> None:
            # Store as simple dicts compatible with how this project reads them
            human = inputs.get(self.input_key)
            ai = outputs.get(self.output_key)
            if human is not None:
                self._buffer.append({"type": "human", "content": human})
            if ai is not None:
                self._buffer.append({"type": "ai", "content": ai})

from app.core.config import settings
from app.utils.prompts import (
    system_prompt_for_check_vocab, 
    BASE_SYSTEM_PROMPT,
    BEGINNER_LEVEL_PROMPT,
    INTERMEDIATE_LEVEL_PROMPT, 
    ADVANCED_LEVEL_PROMPT,
    INITIAL_GREETING_MESSAGE,
    simple_words
)


class AIService:
    """AI service for chat and grammar correction - Enhanced with LangChain (from talkai_py)"""
    
    def __init__(self):
        self.moonshot_api_key = settings.moonshot_api_key
        self.openai_api_key = settings.openai_api_key
        self.model_provider = settings.model_provider
        self.moonshot_model = settings.moonshot_model
        self.openai_model = settings.openai_model
        
        # Initialize LangChain models (same as talkai_py)
        if self.model_provider == "openai" and self.openai_api_key:
            self.chat_model = ChatOpenAI(
                model=self.openai_model,
                openai_api_key=self.openai_api_key
            )
            self.openai_url = "https://api.openai.com/v1/chat/completions"
        else:
            # Use Moonshot as default (assuming moonshot-compatible API)
            self.chat_model = ChatOpenAI(
                model=self.moonshot_model,
                openai_api_base="https://api.moonshot.cn/v1",
                openai_api_key=self.moonshot_api_key
            )
            self.moonshot_url = "https://api.moonshot.cn/v1/chat/completions"
        
        # Initialize memory for each user session (dictionary to store per-user memory)
        self.user_memories = {}
        
        # Initialize sentence transformer for vocabulary suggestions
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None
    
    def _get_user_memory(self, user_id: str) -> ConversationBufferWindowMemory:
        """Get or create memory for a specific user (same as talkai_py memory management)"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationBufferWindowMemory(
                return_messages=True,
                memory_key="chat_history",
                input_key="human_input", 
                output_key="ai_output",
                k=settings.max_memory_turns or 3  # Same as talkai_py MAX_MEMORY_TURNS
            )
        return self.user_memories[user_id]
        
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
            
            async with httpx.AsyncClient(
                timeout=30.0,
                trust_env=False  # Don't use environment proxy settings
            ) as client:
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
            
            async with httpx.AsyncClient(
                timeout=30.0,
                trust_env=False  # Don't use environment proxy settings
            ) as client:
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
    
    def check_vocab_from_input(self, user_input: str) -> Dict[str, Any]:
        """
        Check vocabulary from user input using LangChain (same as talkai_py)
        
        Args:
            user_input: User's input text
            
        Returns:
            Dict containing corrected input and words deserve to learn
        """
        try:
            # Create prompt template (same as talkai_py)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt_for_check_vocab),
                ("human", "{human_input}")
            ])
            
            # Create chain (same as talkai_py)
            chain = prompt | self.chat_model
            
            # Invoke chain (same as talkai_py)
            response = chain.invoke({"human_input": user_input})
            
            response_text = response.content
            logger.debug(f"Grammar check response: {response_text[:200]}...")
            
            try:
                # Parse JSON response (same as talkai_py)
                parsed_response = json.loads(response_text)
                logger.info(f"Parsed grammar response: {parsed_response}")
                
                corrected_input = parsed_response.get("corrected_input")
                words_deserve_to_learn = parsed_response.get("words_deserve_to_learn", [])
                is_valid = parsed_response.get("is_valid", False)
                explanation = parsed_response.get("explanation", "")
                
                # Handle explanation being dict (same as talkai_py)
                if isinstance(explanation, dict):
                    explanation_parts = []
                    for word, desc in explanation.items():
                        explanation_parts.append(f"{word}: {desc}")
                    explanation = "; ".join(explanation_parts)
                elif not isinstance(explanation, str):
                    explanation = str(explanation)
                
                return {
                    "corrected_input": corrected_input,
                    "words_deserve_to_learn": words_deserve_to_learn,
                    "is_valid": is_valid,
                    "explanation": explanation
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                return {
                    "corrected_input": None,
                    "words_deserve_to_learn": [],
                    "is_valid": False,
                    "explanation": ""
                }
                
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return {
                "corrected_input": None,
                "words_deserve_to_learn": [],
                "is_valid": False,
                "explanation": ""
            }
    
    def generate_response_natural(
        self, 
        user_input: str, 
        user_profile: Dict[str, Any],
        user_id: str = "default_user",
        is_voice_input: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response to user input using LangChain components (same as talkai_py)
        
        Args:
            user_input: User's input text
            user_profile: User profile information
            user_id: User ID for memory management
            is_voice_input: Whether input is from voice
            
        Returns:
            Dict with response text and metadata
        """
        try:
            logger.info(f"Generating response for user {user_id}: {user_input[:50]}...")
            
            # Create system prompt based on user profile (same as talkai_py)
            system_prompt = self._create_system_prompt(user_profile)
            
            # Get user's memory (same as talkai_py memory management)
            memory = self._get_user_memory(user_id)
            
            # Create prompt template for natural conversation (same as talkai_py)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{human_input}")
            ])
            
            # Create chain (same as talkai_py)
            chain = prompt | self.chat_model
            
            # Generate response (same as talkai_py)
            response = chain.invoke({
                "chat_history": memory.load_memory_variables({}).get("chat_history", []),
                "human_input": user_input
            })
            
            # Save to memory (same as talkai_py)
            memory.save_context(
                {"human_input": user_input},
                {"ai_output": response.content}
            )
            
            result = {
                "text": response.content
            }
            
            logger.info(f"Generated response for user {user_id}: {response.content[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            error_message = "I'm sorry, I encountered an error. Please try again."
            return {
                "text": error_message,
                "error": str(e)
            }
    
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
    
    async def generate_auto_message(
        self, 
        user_profile: Dict[str, Any], 
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Generate automatic conversation starter when user is inactive
        
        This mimics the talkai_py auto-message feature that proactively
        suggests new conversation topics based on user level and context.
        
        Args:
            user_profile: User profile information
            conversation_history: Recent conversation context
            
        Returns:
            AI-generated conversation starter
        """
        try:
            # Create prompt for generating conversation starter
            auto_message_prompt = """
            You are an English learning tutor. The user has been inactive for a while. 
            Generate a friendly conversation starter to re-engage them in English practice.
            
            Guidelines:
            - Keep it natural and conversational
            - Ask an engaging question to restart dialogue
            - Match the user's learning level
            - Consider recent conversation topics to avoid repetition
            - Be encouraging and motivating
            
            Respond with ONLY the conversation starter message, no additional text.
            """
            
            # Add user profile context
            if user_profile:
                grade = user_profile.get("grade", "")
                age = user_profile.get("age", "")
                
                context_info = f"\nUser Level: {grade}"
                if age:
                    context_info += f"\nUser Age: {age}"
                
                auto_message_prompt += context_info
            
            # Add conversation history context if available
            if conversation_history:
                recent_topics = []
                for msg in conversation_history[-3:]:  # Last 3 messages for context
                    if msg.get("content") and len(msg["content"]) < 100:
                        recent_topics.append(msg["content"])
                
                if recent_topics:
                    auto_message_prompt += f"\n\nRecent topics discussed: {', '.join(recent_topics)}"
                    auto_message_prompt += "\nAvoid repeating these exact topics."
            
            # Level-specific prompts
            grade = user_profile.get("grade", "").lower() if user_profile else ""
            if "primary" in grade:
                auto_message_prompt += "\n\nUse simple vocabulary and ask about basic daily activities, hobbies, or school."
            elif "middle" in grade or "high" in grade:
                auto_message_prompt += "\n\nAsk about interests, future plans, current events, or personal experiences."
            elif "cet" in grade or "toefl" in grade or "ielts" in grade or "gre" in grade:
                auto_message_prompt += "\n\nDiscuss complex topics, current affairs, abstract concepts, or thought-provoking questions."
            
            messages = [
                {"role": "system", "content": auto_message_prompt},
                {"role": "user", "content": "Generate a conversation starter for me."}
            ]
            
            # Generate auto message
            response = await self._call_ai_api(messages, temperature=0.9)  # Higher creativity
            
            if not response:
                # Fallback messages based on user level
                fallback_messages = self._get_fallback_auto_messages(user_profile)
                import random
                return random.choice(fallback_messages)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Auto message generation failed: {e}")
            # Return simple fallback
            return "Hi there! How was your day? Tell me something interesting that happened to you recently!"
    
    def _get_fallback_auto_messages(self, user_profile: Dict[str, Any]) -> List[str]:
        """Get fallback auto messages when AI generation fails"""
        grade = user_profile.get("grade", "").lower() if user_profile else ""
        
        if "primary" in grade:
            return [
                "Hi! What's your favorite color and why?",
                "Tell me about your best friend!",
                "What did you eat for breakfast today?",
                "Do you like animals? What's your favorite?",
                "What's your favorite game to play?"
            ]
        elif "middle" in grade or "high" in grade:
            return [
                "What's the most interesting thing you learned this week?",
                "If you could travel anywhere, where would you go?",
                "What's a movie or book you enjoyed recently?",
                "Do you have any hobbies you're passionate about?",
                "What's something you're looking forward to?"
            ]
        else:  # Advanced level
            return [
                "What's your perspective on the role of technology in modern education?",
                "If you could solve one global problem, what would it be and why?",
                "What's a cultural difference you've noticed between your country and others?",
                "How do you think social media has changed human communication?",
                "What's a skill you'd love to master and how would it impact your life?"
            ]
    
    async def suggest_vocabulary(
        self, 
        user_id: str,
        user_input: str, 
        ai_response: str,
        db: Session
    ) -> List[str]:
        """
        Generate vocabulary suggestions based on semantic similarity.
        Uses the vocabulary embedding service with talkai_py algorithm.
        复制 find_vocabulary_from_last_turn 逻辑
        """
        try:
            from app.services.vocabulary_embedding import vocabulary_embedding_service
            
            suggestions = vocabulary_embedding_service.find_similar_vocabulary(
                user_input=user_input,
                ai_response=ai_response,
                user_id=user_id,
                db=db,
                top_n=settings.top_n_vocab or 5
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Vocabulary suggestions generation failed: {e}")
            return []
    
    async def update_vocabulary_from_correction(
        self,
        grammar_result: Dict[str, Any],
        user_input: str, 
        user_id: str,
        db: Session
    ):
        """
        Update vocabulary database based on grammar correction results.
        Uses the enhanced vocabulary service with talkai_py algorithm.
        复制 talkai_py 的 update_vocab_oneturn_async 逻辑
        """
        try:
            from app.services.vocabulary import vocabulary_service
            
            # Convert grammar_result to the format expected by vocabulary service
            # 确保与 talkai_py 的格式一致
            correction_result = {
                "is_valid": grammar_result.get("is_valid", False),
                "corrected_input": grammar_result.get("corrected_input"),
                "words_deserve_to_learn": []
            }
            
            # Convert words_deserve_to_learn format (from grammar check result)
            if grammar_result.get("words_deserve_to_learn"):
                correction_result["words_deserve_to_learn"] = grammar_result["words_deserve_to_learn"]
            # Fallback to vocab_to_learn if using different format
            elif grammar_result.get("vocab_to_learn"):
                for vocab_item in grammar_result["vocab_to_learn"]:
                    word_item = {
                        "original": vocab_item.get("original", ""),
                        "corrected": vocab_item.get("corrected", ""),
                        "error_type": vocab_item.get("error_type", "vocabulary"),
                        "explanation": vocab_item.get("explanation", "")
                    }
                    correction_result["words_deserve_to_learn"].append(word_item)
            
            # Use vocabulary service to update vocabulary (same as talkai_py)
            success = await vocabulary_service.update_vocabulary_from_correction(
                user_id=user_id,
                correction_result=correction_result,
                user_input=user_input,
                db=db
            )
            
            if success:
                logger.info(f"Successfully updated vocabulary from correction for user {user_id}")
            else:
                logger.warning(f"Failed to update vocabulary from correction for user {user_id}")
                
        except Exception as e:
            logger.error(f"Vocabulary update from correction failed: {e}")


# Global AI service instance
ai_service = AIService()