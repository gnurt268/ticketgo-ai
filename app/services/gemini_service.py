"""
Google Gemini AI Service for chat and embeddings
"""
import logging
from typing import List, Optional
import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)


class GeminiService:
    """Service for Google Gemini AI operations"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.embedding_model = settings.gemini_embedding_model
        
        # System prompt for TicketGo chatbot
        self.system_prompt = """Bạn là TicketGo Assistant - trợ lý AI thông minh của nền tảng bán vé sự kiện TicketGo.

NHIỆM VỤ:
- Hỗ trợ khách hàng tìm kiếm và mua vé sự kiện
- Trả lời câu hỏi về chính sách, quy trình đặt vé, thanh toán
- Hướng dẫn sử dụng các tính năng của TicketGo
- Cung cấp thông tin về sự kiện dựa trên dữ liệu được cung cấp

QUY TẮC:
1. Luôn trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp
2. Dựa vào CONTEXT được cung cấp để trả lời chính xác
3. Nếu không có thông tin trong context, hãy nói rõ và đề xuất liên hệ hotline
4. Không bịa đặt thông tin về giá vé, thời gian, địa điểm
5. Với câu hỏi về đơn hàng cụ thể, hướng dẫn user đăng nhập để xem
6. Giữ câu trả lời ngắn gọn, dễ hiểu (tối đa 3-4 đoạn)

THÔNG TIN LIÊN HỆ:
- Hotline: 1900-xxxx
- Email: support@ticketgo.vn
- Website: https://ticketgo.vn

Hãy trả lời câu hỏi của khách hàng dựa trên context sau:
"""
    
    async def generate_response(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[List[dict]] = None
    ) -> str:
        """
        Generate response using Gemini with RAG context
        
        Args:
            user_message: User's question
            context: Retrieved context from knowledge base
            chat_history: Previous messages in conversation
        
        Returns:
            AI generated response
        """
        try:
            # Build the full prompt
            full_prompt = f"{self.system_prompt}\n\n"
            full_prompt += f"CONTEXT:\n{context}\n\n"
            
            # Add chat history if available
            if chat_history:
                full_prompt += "LỊCH SỬ HỘI THOẠI:\n"
                for msg in chat_history[-6:]:  # Last 6 messages for context
                    role = "Khách hàng" if msg["role"] == "user" else "Assistant"
                    full_prompt += f"{role}: {msg['content']}\n"
                full_prompt += "\n"
            
            full_prompt += f"CÂU HỎI HIỆN TẠI: {user_message}\n\n"
            full_prompt += "TRẢ LỜI:"
            
            # Generate response
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=1024,
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using Gemini
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (768 dimensions)
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for search query
        Uses different task_type optimized for retrieval
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Gemini query embedding error: {e}")
            raise
    
    async def generate_suggested_questions(
        self,
        user_message: str,
        assistant_response: str
    ) -> List[str]:
        """
        Generate follow-up question suggestions
        """
        try:
            prompt = f"""Dựa trên cuộc hội thoại sau, đề xuất 3 câu hỏi tiếp theo mà khách hàng có thể muốn hỏi.

Câu hỏi khách hàng: {user_message}
Trả lời: {assistant_response}

Chỉ trả về 3 câu hỏi ngắn gọn, mỗi câu trên 1 dòng, không đánh số:"""

            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=200,
                )
            )
            
            # Parse suggestions
            suggestions = [
                line.strip() 
                for line in response.text.strip().split('\n') 
                if line.strip() and not line.strip()[0].isdigit()
            ][:3]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []
    
    async def check_connection(self) -> bool:
        """Check if Gemini API is accessible"""
        try:
            response = await self.model.generate_content_async(
                "Xin chào",
                generation_config=genai.GenerationConfig(max_output_tokens=10)
            )
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini connection check failed: {e}")
            return False


# Singleton instance
gemini_service = GeminiService()
