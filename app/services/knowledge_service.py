"""
Knowledge Base Management Service
Handles FAQ, policies, and event sync
"""
import logging
import httpx
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db import VectorStore, KnowledgeBase, get_db_context
from app.services.gemini_service import gemini_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Default FAQ data for TicketGo
DEFAULT_KNOWLEDGE_BASE = [
    # === FAQ - Mua vé ===
    {
        "title": "Cách mua vé trên TicketGo",
        "content": """Để mua vé trên TicketGo, bạn thực hiện các bước sau:
1. Tìm kiếm sự kiện bạn muốn tham gia trên trang chủ hoặc mục Sự kiện
2. Chọn sự kiện và xem chi tiết về thời gian, địa điểm, giá vé
3. Chọn loại vé và số lượng muốn mua
4. Chọn ghế ngồi (nếu có sơ đồ ghế)
5. Điền thông tin người tham dự
6. Chọn phương thức thanh toán và hoàn tất
7. Nhận vé điện tử qua email và trong mục "Vé của tôi"

Lưu ý: Bạn cần đăng nhập hoặc đăng ký tài khoản trước khi mua vé.""",
        "category": "faq",
        "metadata": {"tags": ["mua vé", "hướng dẫn", "đặt vé"]}
    },
    {
        "title": "Các phương thức thanh toán",
        "content": """TicketGo hỗ trợ các phương thức thanh toán sau:

1. **VNPay**: Thanh toán qua ví VNPay hoặc thẻ ngân hàng nội địa/quốc tế liên kết VNPay
2. **Thẻ ATM nội địa**: Các ngân hàng Việt Nam có đăng ký Internet Banking
3. **Thẻ quốc tế**: Visa, MasterCard, JCB

Thời gian thanh toán: Bạn có 15 phút để hoàn tất thanh toán sau khi tạo đơn hàng. Sau thời gian này, đơn hàng sẽ tự động hủy và ghế sẽ được mở bán lại.

Lưu ý: Mọi giao dịch đều được bảo mật theo tiêu chuẩn quốc tế.""",
        "category": "faq",
        "metadata": {"tags": ["thanh toán", "VNPay", "thẻ ngân hàng"]}
    },
    {
        "title": "Kiểm tra và xem vé đã mua",
        "content": """Để xem vé đã mua trên TicketGo:

1. Đăng nhập vào tài khoản TicketGo
2. Vào mục "Vé của tôi" trên menu
3. Xem danh sách tất cả vé đã mua
4. Nhấn vào từng vé để xem chi tiết và mã QR

Vé điện tử cũng được gửi đến email đăng ký ngay sau khi thanh toán thành công.

Mã QR trên vé dùng để check-in tại sự kiện. Vui lòng không chia sẻ mã QR với người khác.""",
        "category": "faq",
        "metadata": {"tags": ["xem vé", "vé của tôi", "QR code"]}
    },
    
    # === FAQ - Check-in ===
    {
        "title": "Quy trình check-in tại sự kiện",
        "content": """Quy trình check-in tại sự kiện TicketGo:

1. **Chuẩn bị vé**: Mở ứng dụng hoặc email có mã QR vé
2. **Đến cổng check-in**: Tìm khu vực check-in tại địa điểm sự kiện
3. **Quét mã QR**: Đưa mã QR để nhân viên quét bằng thiết bị
4. **Xác nhận**: Nhân viên xác nhận thông tin và cho phép vào

Lưu ý quan trọng:
- Mỗi vé chỉ check-in được 1 lần
- Đến sớm 30-60 phút để tránh xếp hàng
- Mang theo giấy tờ tùy thân để đối chiếu nếu cần
- Vé đã check-in không thể chuyển nhượng""",
        "category": "faq",
        "metadata": {"tags": ["check-in", "quét vé", "sự kiện"]}
    },
    
    # === Chính sách ===
    {
        "title": "Chính sách hoàn vé và hủy đơn",
        "content": """Chính sách hoàn vé của TicketGo:

**Trước khi thanh toán:**
- Có thể hủy đơn hàng bất cứ lúc nào
- Ghế đã chọn sẽ được giải phóng

**Sau khi thanh toán:**
- Vé đã thanh toán KHÔNG được hoàn lại tiền
- Không hỗ trợ đổi ngày/giờ/loại vé
- Có thể chuyển nhượng vé cho người khác

**Trường hợp đặc biệt:**
- Sự kiện bị hủy: Hoàn 100% tiền vé
- Sự kiện dời lịch: Vé vẫn có hiệu lực hoặc hoàn tiền theo chính sách BTC

Mọi thắc mắc về hoàn vé, vui lòng liên hệ hotline: 1900-xxxx""",
        "category": "policy",
        "metadata": {"tags": ["hoàn vé", "hủy đơn", "chính sách"]}
    },
    {
        "title": "Chính sách chuyển nhượng vé",
        "content": """Chính sách chuyển nhượng vé trên TicketGo:

**Điều kiện chuyển nhượng:**
- Vé phải ở trạng thái ACTIVE (chưa sử dụng)
- Sự kiện chưa bắt đầu
- Người nhận phải có tài khoản TicketGo

**Cách chuyển nhượng:**
1. Vào mục "Vé của tôi"
2. Chọn vé muốn chuyển
3. Nhấn "Chuyển nhượng vé"
4. Nhập email người nhận
5. Xác nhận chuyển nhượng

**Lưu ý:**
- Sau khi chuyển, bạn không còn quyền sử dụng vé
- Người nhận sẽ nhận được vé mới với mã QR mới
- Không thể hoàn tác việc chuyển nhượng
- Mỗi vé chỉ chuyển nhượng được 1 lần""",
        "category": "policy",
        "metadata": {"tags": ["chuyển nhượng", "transfer", "đổi chủ"]}
    },
    {
        "title": "Chính sách bảo mật thông tin",
        "content": """TicketGo cam kết bảo mật thông tin khách hàng:

**Thông tin thu thập:**
- Thông tin cá nhân: Họ tên, email, số điện thoại
- Thông tin thanh toán: Được xử lý qua cổng thanh toán bảo mật

**Cam kết bảo mật:**
- Không chia sẻ thông tin cho bên thứ 3 khi chưa có sự đồng ý
- Mã hóa dữ liệu theo tiêu chuẩn SSL/TLS
- Tuân thủ quy định về bảo vệ dữ liệu cá nhân

**Quyền của khách hàng:**
- Yêu cầu xem, chỉnh sửa thông tin cá nhân
- Yêu cầu xóa tài khoản
- Từ chối nhận email marketing

Liên hệ: privacy@ticketgo.vn""",
        "category": "policy",
        "metadata": {"tags": ["bảo mật", "privacy", "GDPR"]}
    },
    
    # === Hướng dẫn ===
    {
        "title": "Hướng dẫn đăng ký tài khoản",
        "content": """Cách đăng ký tài khoản TicketGo:

**Bước 1:** Truy cập ticketgo.vn hoặc mở ứng dụng
**Bước 2:** Nhấn nút "Đăng ký" hoặc "Đăng nhập"
**Bước 3:** Chọn tab "Đăng ký" 
**Bước 4:** Điền thông tin:
- Họ và tên
- Email (sẽ dùng để nhận vé)
- Số điện thoại
- Mật khẩu (tối thiểu 6 ký tự)

**Bước 5:** Nhấn "Đăng ký"
**Bước 6:** Xác nhận email (nếu có)

Sau khi đăng ký, bạn có thể đăng nhập và bắt đầu mua vé ngay!

Lưu ý: Email đăng ký sẽ được dùng để nhận vé điện tử.""",
        "category": "guide",
        "metadata": {"tags": ["đăng ký", "tạo tài khoản", "sign up"]}
    },
    {
        "title": "Hướng dẫn chọn ghế ngồi",
        "content": """Hướng dẫn chọn ghế trên TicketGo:

**Các loại ghế:**
🟢 Xanh lá: Ghế còn trống, có thể chọn
🟡 Vàng: Ghế đang được giữ tạm thời
🔴 Đỏ: Ghế đã được đặt
⚪ Xám: Ghế không bán

**Cách chọn ghế:**
1. Trong trang chi tiết sự kiện, chọn "Chọn ghế"
2. Xem sơ đồ ghế, di chuột để xem thông tin
3. Click vào ghế muốn chọn (ghế xanh)
4. Ghế được chọn sẽ chuyển sang màu tím
5. Có thể chọn nhiều ghế (tùy giới hạn)
6. Nhấn "Tiếp tục" để thanh toán

**Mẹo chọn ghế:**
- Chọn ghế ở giữa để có góc nhìn tốt nhất
- Ghế gần sân khấu thường đắt hơn
- Đặt sớm để có nhiều lựa chọn""",
        "category": "guide",
        "metadata": {"tags": ["chọn ghế", "sơ đồ ghế", "seat map"]}
    },
    
    # === Thông tin chung ===
    {
        "title": "Giới thiệu về TicketGo",
        "content": """TicketGo là nền tảng bán vé sự kiện trực tuyến hàng đầu Việt Nam.

**Các loại sự kiện:**
- 🎵 Nhạc sống: Concert, Festival, Live Show
- 🎭 Sân khấu & Nghệ thuật: Kịch, Hài, Múa, Opera
- ⚽ Thể thao: Bóng đá, Giải đấu, Marathon
- 🎪 Khác: Workshop, Hội thảo, Triển lãm

**Tính năng nổi bật:**
- Đặt vé nhanh chóng, bảo mật
- Chọn ghế trực quan trên sơ đồ
- Vé điện tử với mã QR
- Check-in nhanh bằng quét QR
- Chuyển nhượng vé dễ dàng

**Cam kết:**
- 100% vé chính hãng
- Thanh toán an toàn
- Hỗ trợ 24/7

Website: ticketgo.vn
Hotline: 1900-xxxx""",
        "category": "guide",
        "metadata": {"tags": ["giới thiệu", "about", "TicketGo"]}
    },
    {
        "title": "Câu hỏi về lỗi thanh toán",
        "content": """Xử lý khi gặp lỗi thanh toán trên TicketGo:

**Lỗi thường gặp:**

1. **"Giao dịch thất bại"**
   - Kiểm tra số dư tài khoản
   - Kiểm tra hạn mức giao dịch online
   - Thử lại hoặc đổi phương thức thanh toán

2. **"Hết thời gian thanh toán"**
   - Đơn hàng tự hủy sau 15 phút
   - Vui lòng đặt lại từ đầu
   - Ghế đã chọn có thể bị người khác đặt

3. **"Thẻ không được chấp nhận"**
   - Kiểm tra thẻ đã đăng ký Internet Banking
   - Liên hệ ngân hàng để mở chức năng thanh toán online

4. **Bị trừ tiền nhưng không nhận vé**
   - Đợi 5-10 phút để hệ thống xử lý
   - Kiểm tra email (cả spam)
   - Liên hệ hotline nếu vẫn không nhận được

Hotline hỗ trợ: 1900-xxxx (8h-22h hàng ngày)""",
        "category": "faq",
        "metadata": {"tags": ["lỗi thanh toán", "payment error", "hỗ trợ"]}
    },
]


class KnowledgeService:
    """Service to manage knowledge base"""
    
    async def seed_default_knowledge(self, db: Session) -> int:
        """Seed default FAQ and policies"""
        count = 0
        
        for item in DEFAULT_KNOWLEDGE_BASE:
            # Check if already exists
            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.title == item["title"]
            ).first()
            
            if existing:
                logger.info(f"Skipping existing: {item['title']}")
                continue
            
            try:
                # Generate embedding
                text_to_embed = f"{item['title']}\n{item['content']}"
                embedding = await gemini_service.generate_embedding(text_to_embed)
                
                # Add to database
                VectorStore.add_document(
                    db,
                    title=item["title"],
                    content=item["content"],
                    category=item["category"],
                    embedding=embedding,
                    metadata=item.get("metadata")
                )
                
                count += 1
                logger.info(f"Added: {item['title']}")
                
            except Exception as e:
                logger.error(f"Error adding {item['title']}: {e}")
        
        return count
    
    async def sync_events_from_main_api(
        self, 
        db: Session,
        event_ids: Optional[List[int]] = None
    ) -> int:
        """Sync events from main Spring Boot API to knowledge base"""
        try:
            async with httpx.AsyncClient() as client:
                # Fetch events from main API
                url = f"{settings.main_api_url}/public/events"
                params = {"size": 100, "status": "PUBLISHED"}
                
                response = await client.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                events = data.get("content", [])
                
                if event_ids:
                    events = [e for e in events if e["id"] in event_ids]
                
                count = 0
                for event in events:
                    try:
                        await self._index_event(db, event)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error indexing event {event.get('id')}: {e}")
                
                logger.info(f"Synced {count} events from main API")
                return count
                
        except Exception as e:
            logger.error(f"Error syncing events: {e}")
            raise
    
    async def _index_event(self, db: Session, event: dict) -> None:
        """Index a single event to knowledge base"""
        event_id = event.get("id")
        
        # Build content for the event
        content = f"""Sự kiện: {event.get('title')}

📅 Thời gian: {event.get('startDate', 'Chưa xác định')}
📍 Địa điểm: {event.get('venue', '')} - {event.get('address', '')}
🏷️ Thể loại: {event.get('categoryName', '')}
🎫 Giá vé: từ {event.get('minPrice', 0):,.0f}đ đến {event.get('maxPrice', 0):,.0f}đ

{event.get('shortDescription', '')}

Trạng thái: {'Đang mở bán' if event.get('status') == 'PUBLISHED' else 'Chưa mở bán'}"""

        title = f"Sự kiện: {event.get('title')}"
        
        # Check if event already indexed
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.category == "event",
            KnowledgeBase.metadata["event_id"].astext == str(event_id)
        ).first()
        
        # Generate embedding
        embedding = await gemini_service.generate_embedding(f"{title}\n{content}")
        
        if existing:
            # Update existing
            existing.content = content
            existing.embedding = embedding
            existing.metadata = {"event_id": event_id, "slug": event.get("slug")}
            db.commit()
        else:
            # Add new
            VectorStore.add_document(
                db,
                title=title,
                content=content,
                category="event",
                embedding=embedding,
                metadata={"event_id": event_id, "slug": event.get("slug")}
            )
    
    def get_all_knowledge(
        self, 
        db: Session, 
        category: Optional[str] = None
    ) -> List[KnowledgeBase]:
        """Get all knowledge base items"""
        return VectorStore.get_all_documents(db, category)
    
    def delete_knowledge(self, db: Session, doc_id: int) -> bool:
        """Delete a knowledge base item"""
        return VectorStore.delete_document(db, doc_id)


# Singleton instance
knowledge_service = KnowledgeService()
