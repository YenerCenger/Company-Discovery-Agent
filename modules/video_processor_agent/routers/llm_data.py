"""
LLM Data Router - Detailed JSON data export for LLM processing.

This router provides detailed analysis results in JSON format optimized for LLM consumption.
Returns comprehensive video analysis data with all segments, objects, OCR, and metadata.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from bson import ObjectId
from datetime import datetime

from modules.video_processor_agent.core.database import get_analysis_collection
from modules.video_processor_agent.models.models import AnalysisResult

# Setup router and logger
router = APIRouter(prefix="/llm", tags=["LLM Data"])
logger = logging.getLogger(__name__)


def convert_objectid_to_str(obj: dict) -> dict:
    """
    Recursively convert ObjectId fields to strings for JSON serialization.
    
    Args:
        obj: Dictionary that may contain ObjectId fields
        
    Returns:
        Dictionary with ObjectId fields converted to strings
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = convert_objectid_to_str(value)
            elif isinstance(value, list):
                result[key] = [convert_objectid_to_str(item) if isinstance(item, dict) else str(item) if isinstance(item, ObjectId) else item for item in value]
            else:
                result[key] = value
        return result
    return obj


@router.get("/data", response_model=dict)
async def get_all_analysis_data(
    company_name: Optional[str] = Query(None, description="Filter by company name"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    video_id: Optional[str] = Query(None, description="Get specific video analysis"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    include_failed: bool = Query(False, description="Include failed analyses")
) -> dict:
    """
    Get all analysis results in detailed JSON format for LLM processing.
    
    Returns comprehensive video analysis data including:
    - All segments with transcripts, objects, OCR
    - Aggregated objects and OCR texts
    - Metadata (views, likes, comments)
    - Processing timestamps
    
    Args:
        company_name: Filter by company name (optional)
        company_id: Filter by company ID (optional)
        video_id: Get specific video analysis (optional)
        limit: Maximum number of results (1-1000, default: 100)
        include_failed: Include failed analyses (default: False)
    
    Returns:
        Detailed JSON response with all analysis data
    
    Raises:
        HTTPException: If invalid parameters or database error
    """
    try:
        collection = get_analysis_collection()
        
        # Build query
        query: dict = {}
        
        if video_id:
            try:
                query["_id"] = ObjectId(video_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid video_id format: {video_id}"
                )
        else:
            if company_name:
                query["company_name"] = company_name
            
            if company_id:
                try:
                    query["company_id"] = ObjectId(company_id)
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid company_id format: {company_id}"
                    )
            
            if not include_failed:
                query["status"] = {"$ne": "failed"}
        
        # Fetch results
        cursor = collection.find(query).sort("processed_at", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        
        if not results:
            return {
                "success": True,
                "count": 0,
                "data": [],
                "message": "No analysis results found"
            }
        
        # Convert to AnalysisResult models and then to dict
        analysis_results = []
        for doc in results:
            try:
                # Convert ObjectId to string for JSON serialization
                doc_clean = convert_objectid_to_str(doc)
                
                # Parse with Pydantic model for validation
                result = AnalysisResult.model_validate(doc_clean)
                
                # Convert to dict with all fields
                result_dict = result.model_dump(
                    by_alias=True,
                    mode="json",
                    exclude_none=False
                )
                
                analysis_results.append(result_dict)
            except Exception as e:
                logger.warning(f"Failed to parse document {doc.get('_id')}: {e}")
                continue
        
        # Calculate aggregate statistics
        total_segments = sum(len(r.get("segments", [])) for r in analysis_results)
        all_objects = set()
        all_ocr_texts = set()
        
        for result in analysis_results:
            all_objects.update(result.get("all_objects", []))
            all_ocr_texts.update(result.get("all_ocr_text", []))
        
        return {
            "success": True,
            "count": len(analysis_results),
            "statistics": {
                "total_videos": len(analysis_results),
                "total_segments": total_segments,
                "unique_objects": sorted(list(all_objects)),
                "unique_ocr_texts": sorted(list(all_ocr_texts)),
                "object_count": len(all_objects),
                "ocr_text_count": len(all_ocr_texts)
            },
            "data": analysis_results,
            "query": {
                "company_name": company_name,
                "company_id": company_id,
                "video_id": video_id,
                "limit": limit,
                "include_failed": include_failed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analysis data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analysis data: {str(e)}"
        )


@router.get("/data/{video_id}", response_model=dict)
async def get_video_analysis_data(video_id: str) -> dict:
    """
    Get detailed analysis data for a specific video.
    
    Args:
        video_id: Video analysis ID (MongoDB ObjectId)
    
    Returns:
        Detailed JSON response with video analysis data
    
    Raises:
        HTTPException: If video not found or invalid ID
    """
    try:
        object_id = ObjectId(video_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid video_id format: {video_id}"
        )
    
    collection = get_analysis_collection()
    doc = await collection.find_one({"_id": object_id})
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video analysis not found: {video_id}"
        )
    
    # Convert ObjectId to string
    doc_clean = convert_objectid_to_str(doc)
    
    # Parse with Pydantic model
    result = AnalysisResult.model_validate(doc_clean)
    result_dict = result.model_dump(
        by_alias=True,
        mode="json",
        exclude_none=False
    )
    
    return {
        "success": True,
        "data": result_dict
    }


@router.get("/data/company/{company_name}", response_model=dict)
async def get_company_analysis_data(
    company_name: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
) -> dict:
    """
    Get all analysis data for a specific company.
    
    Args:
        company_name: Company name
        limit: Maximum number of results (1-1000, default: 100)
    
    Returns:
        Detailed JSON response with all company video analyses
    """
    return await get_all_analysis_data(
        company_name=company_name,
        limit=limit,
        include_failed=False
    )


