"""
MongoDB Service - Video Processor Agent'ın MongoDB'sine bağlanır.

Bu servis, Video Processor Agent'ın analiz ettiği videoları MongoDB'den çeker
ve Report Analysis Agent'ın kullanabileceği formata dönüştürür.
"""
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
from modules.video_processor_agent.core.config import settings as video_processor_settings
from modules.report_analysis_agent.models.video_model import (
    VideoData, APIResponse, Statistics, Query, Metadata, Segment
)

logger = logging.getLogger(__name__)


class MongoDBService:
    """MongoDB'den video analiz sonuçlarını çeken servis."""
    
    def __init__(self):
        self.settings = video_processor_settings
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
    
    async def connect(self):
        """MongoDB'ye bağlan."""
        if self.client is None:
            # Settings'deki doğru attribute isimleri: MONGO_URL, DB_NAME
            self.client = AsyncIOMotorClient(self.settings.MONGO_URL)
            self.db = self.client[self.settings.DB_NAME]
            self.collection = self.db["analysis_results"]  # Collection adı sabit
            logger.info(f"Connected to MongoDB: {self.settings.DB_NAME}/analysis_results")
    
    async def close(self):
        """MongoDB bağlantısını kapat."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.collection = None
            logger.info("MongoDB connection closed")
    
    async def get_analysis_by_company(
        self, 
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 100,
        include_failed: bool = False
    ) -> List[dict]:
        """
        Şirkete göre analiz sonuçlarını getir.
        
        Args:
            company_name: Şirket adı (opsiyonel)
            company_id: PostgreSQL company ID (opsiyonel)
            limit: Maksimum sonuç sayısı
            include_failed: Başarısız analizleri dahil et
        
        Returns:
            Analiz sonuçları listesi
        """
        await self.connect()
        
        # Build query
        query = {}
        
        if company_name:
            query["company_name"] = company_name
        
        if company_id:
            query["postgresql_company_id"] = company_id
        
        if not include_failed:
            query["status"] = "completed"
        
        # Execute query
        cursor = self.collection.find(query).sort("processed_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            results.append(doc)
        
        logger.info(f"Found {len(results)} analysis results")
        return results
    
    async def get_all_completed_analyses(self, limit: int = 100) -> List[dict]:
        """Tüm tamamlanmış analizleri getir."""
        await self.connect()
        
        cursor = self.collection.find({"status": "completed"}).sort("processed_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            results.append(doc)
        
        return results
    
    def _convert_to_video_data(self, doc: dict) -> VideoData:
        """
        MongoDB dokümanını VideoData modeline dönüştür.
        
        Args:
            doc: MongoDB dokümanı
        
        Returns:
            VideoData instance
        """
        # Convert _id to string
        doc_id = str(doc.get("_id", ""))
        
        # Build Metadata
        metadata_dict = doc.get("metadata", {})
        metadata = Metadata(
            platform=metadata_dict.get("platform", "instagram"),
            view_count=metadata_dict.get("view_count", 0),
            like_count=metadata_dict.get("like_count", 0),
            comment_count=metadata_dict.get("comment_count", 0)
        )
        
        # Build Segments
        segments = []
        for seg in doc.get("segments", []):
            segment = Segment(
                start_time=seg.get("start_time", 0),
                end_time=seg.get("end_time", 0),
                transcript=seg.get("transcript", ""),
                visual_objects=seg.get("visual_objects", []),
                ocr_text=seg.get("ocr_text", []),
                sentiment=seg.get("sentiment"),
                key_entities=seg.get("key_entities", [])
            )
            segments.append(segment)
        
        # Handle processed_at - could be datetime or string
        processed_at = doc.get("processed_at", datetime.now())
        if isinstance(processed_at, datetime):
            processed_at_str = processed_at.isoformat()
        else:
            processed_at_str = str(processed_at)
        
        # Build VideoData
        video_data = VideoData(
            _id=doc_id,
            company_id=str(doc.get("company_id", doc.get("postgresql_company_id", ""))),
            company_name=doc.get("company_name", "Unknown"),
            video_filename=doc.get("video_filename", "unknown.mp4"),
            video_url=doc.get("video_url"),
            processed_at=processed_at_str,
            metadata=metadata,
            segments=segments,
            summary=doc.get("summary"),
            all_objects=doc.get("all_objects", []),
            all_ocr_text=doc.get("all_ocr_text", []),
            dominant_emotion=doc.get("dominant_emotion"),
            status=doc.get("status", "completed")
        )
        
        return video_data
    
    async def get_api_response(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        video_id: Optional[str] = None,
        limit: int = 100,
        include_failed: bool = False
    ) -> APIResponse:
        """
        MongoDB'den verileri çekip APIResponse formatında döndür.
        
        Args:
            company_name: Şirket adı (opsiyonel)
            company_id: PostgreSQL company ID (opsiyonel)
            video_id: Belirli bir video ID (opsiyonel)
            limit: Maksimum sonuç sayısı
            include_failed: Başarısız analizleri dahil et
        
        Returns:
            APIResponse instance
        """
        await self.connect()
        
        # Build query
        query = {}
        
        if company_name:
            query["company_name"] = company_name
        
        if company_id:
            query["postgresql_company_id"] = company_id
        
        if video_id:
            # Try both _id and postgresql_job_id
            from bson import ObjectId
            try:
                query["_id"] = ObjectId(video_id)
            except:
                query["postgresql_job_id"] = video_id
        
        if not include_failed:
            query["status"] = "completed"
        
        # Execute query
        cursor = self.collection.find(query).sort("processed_at", -1).limit(limit)
        
        docs = []
        async for doc in cursor:
            docs.append(doc)
        
        # Convert to VideoData list
        video_data_list = [self._convert_to_video_data(doc) for doc in docs]
        
        # Calculate statistics
        all_objects = set()
        all_ocr_texts = set()
        total_segments = 0
        
        for video in video_data_list:
            all_objects.update(video.all_objects)
            all_ocr_texts.update(video.all_ocr_text)
            total_segments += len(video.segments)
        
        statistics = Statistics(
            total_videos=len(video_data_list),
            total_segments=total_segments,
            unique_objects=list(all_objects),
            unique_ocr_texts=list(all_ocr_texts),
            object_count=len(all_objects),
            ocr_text_count=len(all_ocr_texts)
        )
        
        # Build query info
        query_info = Query(
            company_name=company_name,
            company_id=company_id,
            video_id=video_id,
            limit=limit,
            include_failed=include_failed
        )
        
        return APIResponse(
            success=True,
            count=len(video_data_list),
            statistics=statistics,
            data=video_data_list,
            query=query_info
        )


# Singleton instance
_mongodb_service: Optional[MongoDBService] = None


def get_mongodb_service() -> MongoDBService:
    """MongoDB servisinin singleton instance'ını döndür."""
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService()
    return _mongodb_service
