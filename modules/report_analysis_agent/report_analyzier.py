import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Query as FastAPIQuery
from fastapi.responses import JSONResponse
from modules.report_analysis_agent.models.request_models import AnalysisRequest, APIRequest
from modules.report_analysis_agent.models.video_model import APIResponse, VideoData, Company, Profile
from modules.report_analysis_agent.agents.preprocessing_agent import preprocess_videos, convert_video_data_to_input
from modules.report_analysis_agent.agents.stats_agent import compute_statistics
from modules.report_analysis_agent.agents.interpretation_agent import llm_interpretation
from modules.report_analysis_agent.agents.recommendation_agent import llm_recommendation
from modules.report_analysis_agent.services.report_builder import build_report, save_report
from modules.report_analysis_agent.services.mongodb_service import get_mongodb_service
import logging
import json
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Analysis Pipeline",
    description="Multi-stage video metadata analysis with LLM interpretation and recommendations",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Video Analysis Pipeline",
        "version": "1.0.0"
    }


def extract_company_from_videos(video_data_list: list[VideoData]) -> Company:
    """Extract company information from video data"""
    if not video_data_list:
        raise ValueError("No video data provided")
    
    first_video = video_data_list[0]
    return Company(
        id=first_video.company_id,
        name=first_video.company_name,
        official_website=None,
        hq_city=None,
        hq_country=None,
        rank_score=None
    )


def extract_profiles_from_videos(video_data_list: list[VideoData]) -> list[Profile]:
    """Extract profile information from video metadata"""
    profiles_dict: Dict[str, Profile] = {}
    
    for video in video_data_list:
        platform = video.metadata.platform
        if platform not in profiles_dict:
            # Create a profile entry for this platform
            profiles_dict[platform] = Profile(
                id=f"profile_{platform}",
                company_id=video.company_id,
                platform=platform,
                profile_url=None,
                followers=0,
                post_count=0,
                engagement_score=0.0
            )
    
    return list(profiles_dict.values())


@app.post("/analyze/api")
async def analyze_from_api(api_response: APIResponse, video_id: str | None = None):
    """
    Main analysis endpoint that accepts API response format:
    - Converts VideoData to VideoInput
    - Processes through the complete pipeline
    """
    try:
        if not api_response.success:
            raise HTTPException(
                status_code=400,
                detail="API response indicates failure"
            )
        
        if not api_response.data:
            raise HTTPException(
                status_code=400,
                detail="No video data provided in API response"
            )

        # If a specific video_id is provided, filter to that video only
        filtered_videos: list[VideoData]
        if video_id:
            filtered_videos = [v for v in api_response.data if v.id == video_id]
            if not filtered_videos:
                raise HTTPException(
                    status_code=404,
                    detail=f"Video with id '{video_id}' not found in API response"
                )
            logger.info(f"Received API response with {len(api_response.data)} videos, filtering to 1 video id={video_id}")
        else:
            filtered_videos = list(api_response.data)
            logger.info(f"Received API response with {len(filtered_videos)} videos (no filtering)")
        
        # Convert VideoData to VideoInput
        video_inputs = []
        for video_data in filtered_videos:
            if video_data.status != "completed":
                logger.warning(f"Skipping video {video_data.id} with status: {video_data.status}")
                continue
            
            try:
                video_input = convert_video_data_to_input(video_data)
                video_inputs.append(video_input)
            except Exception as e:
                logger.error(f"Error converting video {video_data.id}: {str(e)}")
                continue
        
        if not video_inputs:
            raise HTTPException(
                status_code=400,
                detail="No valid videos after conversion"
            )
        
        logger.info(f"Converted {len(video_inputs)} videos to internal format")
        
        # Step 1: Preprocessing
        logger.info("Step 1: Preprocessing videos...")
        preprocessed_videos = preprocess_videos(video_inputs)
        preprocessing_summary = {
            "input_count": len(video_inputs),
            "output_count": len(preprocessed_videos),
            "dropped_count": len(video_inputs) - len(preprocessed_videos)
        }
        logger.info(f"Preprocessing complete: {len(preprocessed_videos)} videos processed")
        
        if not preprocessed_videos:
            raise HTTPException(
                status_code=400,
                detail="No valid videos after preprocessing. All videos were incomplete."
            )
        
        # Step 2: Statistical Analysis
        logger.info("Step 2: Computing statistics...")
        stats_summary = compute_statistics(preprocessed_videos)
        logger.info("Statistics computation complete")
        
        # Extract company and profiles from the (possibly filtered) video data
        company = extract_company_from_videos(filtered_videos)
        profiles = extract_profiles_from_videos(filtered_videos)
        
        # Step 3: LLM Layer 1 - Interpretation
        logger.info("Step 3: Running LLM Layer 1 (Interpretation)...")
        interpretation_output = llm_interpretation(stats_summary, preprocessed_videos)
        logger.info("LLM Layer 1 complete")
        
        # Step 4: LLM Layer 2 - Recommendation
        logger.info("Step 4: Running LLM Layer 2 (Recommendation)...")
        recommendations = llm_recommendation(
            interpretation_output,
            company,
            profiles
        )
        logger.info("LLM Layer 2 complete")
        
        # Step 5: Build and Save Report
        logger.info("Step 5: Building and saving report...")
        json_report, md_report = build_report(
            preprocessing_summary,
            stats_summary,
            interpretation_output,
            recommendations,
            company.name
        )
        
        file_paths = save_report(json_report, md_report)
        logger.info(f"Report saved: {file_paths['report_id']}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "report_id": file_paths["report_id"],
                "json_path": file_paths["json_path"],
                "md_path": file_paths["md_path"],
                "summary": {
                    "videos_processed": len(preprocessed_videos),
                    "top_viral_score": stats_summary.get("viral_score_stats", {}).get("max", 0),
                    "average_viral_score": stats_summary.get("viral_score_stats", {}).get("mean", 0)
                }
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/analyze/test")
async def analyze_with_test_data():
    """
    Test endpoint that uses sample data from example_request.json
    Useful for testing the pipeline without real data
    """
    try:
        # Load example data
        example_file = Path("example_request.json")
        if not example_file.exists():
            raise HTTPException(
                status_code=404,
                detail="example_request.json file not found"
            )
        
        with open(example_file, "r", encoding="utf-8") as f:
            example_data = json.load(f)
        
        # Check if it's new API format or legacy format
        if "success" in example_data and "data" in example_data:
            # New API format
            api_response = APIResponse(**example_data)
            return await analyze_from_api(api_response)
        else:
            # Legacy format
            request = AnalysisRequest(**example_data)
            
            logger.info(f"Test request: Processing {len(request.videos)} videos")
            
            # Step 1: Preprocessing
            logger.info("Step 1: Preprocessing videos...")
            preprocessed_videos = preprocess_videos(request.videos)
            preprocessing_summary = {
                "input_count": len(request.videos),
                "output_count": len(preprocessed_videos),
                "dropped_count": len(request.videos) - len(preprocessed_videos)
            }
            logger.info(f"Preprocessing complete: {len(preprocessed_videos)} videos processed")
            
            if not preprocessed_videos:
                raise HTTPException(
                    status_code=400,
                    detail="No valid videos after preprocessing. All videos were incomplete."
                )
            
            # Step 2: Statistical Analysis
            logger.info("Step 2: Computing statistics...")
            stats_summary = compute_statistics(preprocessed_videos)
            logger.info("Statistics computation complete")
            
            # Step 3: LLM Layer 1 - Interpretation
            logger.info("Step 3: Running LLM Layer 1 (Interpretation)...")
            try:
                interpretation_output = llm_interpretation(stats_summary, preprocessed_videos)
                logger.info("LLM Layer 1 complete")
            except Exception as e:
                logger.error(f"❌ LLM Layer 1 failed: {str(e)}", exc_info=True)
                raise
            
            # Step 4: LLM Layer 2 - Recommendation
            logger.info("Step 4: Running LLM Layer 2 (Recommendation)...")
            recommendations = llm_recommendation(
                interpretation_output,
                request.company,
                request.profiles
            )
            logger.info("LLM Layer 2 complete")
            
            # Step 5: Build and Save Report
            logger.info("Step 5: Building and saving report...")
            json_report, md_report = build_report(
                preprocessing_summary,
                stats_summary,
                interpretation_output,
                recommendations,
                request.company.name
            )
            
            file_paths = save_report(json_report, md_report)
            logger.info(f"Report saved: {file_paths['report_id']}")
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Test analysis completed using example data",
                    "report_id": file_paths["report_id"],
                    "json_path": file_paths["json_path"],
                    "md_path": file_paths["md_path"],
                    "summary": {
                        "videos_processed": len(preprocessed_videos),
                        "top_viral_score": stats_summary.get("viral_score_stats", {}).get("max", 0),
                        "average_viral_score": stats_summary.get("viral_score_stats", {}).get("mean", 0)
                    }
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during test analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/analyze")
async def analyze_videos(request: AnalysisRequest):
    """
    Legacy endpoint for backward compatibility.
    Accepts old format with videos, company, profiles.
    """
    try:
        logger.info(f"Received analysis request for {len(request.videos)} videos")
        
        # Step 1: Preprocessing
        logger.info("Step 1: Preprocessing videos...")
        preprocessed_videos = preprocess_videos(request.videos)
        preprocessing_summary = {
            "input_count": len(request.videos),
            "output_count": len(preprocessed_videos),
            "dropped_count": len(request.videos) - len(preprocessed_videos)
        }
        logger.info(f"Preprocessing complete: {len(preprocessed_videos)} videos processed")
        
        if not preprocessed_videos:
            raise HTTPException(
                status_code=400,
                detail="No valid videos after preprocessing. All videos were incomplete."
            )
        
        # Step 2: Statistical Analysis
        logger.info("Step 2: Computing statistics...")
        stats_summary = compute_statistics(preprocessed_videos)
        logger.info("Statistics computation complete")
        
        # Step 3: LLM Layer 1 - Interpretation
        logger.info("Step 3: Running LLM Layer 1 (Interpretation)...")
        interpretation_output = llm_interpretation(stats_summary, preprocessed_videos)
        logger.info("LLM Layer 1 complete")
        
        # Step 4: LLM Layer 2 - Recommendation
        logger.info("Step 4: Running LLM Layer 2 (Recommendation)...")
        recommendations = llm_recommendation(
            interpretation_output,
            request.company,
            request.profiles
        )
        logger.info("LLM Layer 2 complete")
        
        # Step 5: Build and Save Report
        logger.info("Step 5: Building and saving report...")
        json_report, md_report = build_report(
            preprocessing_summary,
            stats_summary,
            interpretation_output,
            recommendations,
            request.company.name
        )
        
        file_paths = save_report(json_report, md_report)
        logger.info(f"Report saved: {file_paths['report_id']}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "report_id": file_paths["report_id"],
                "json_path": file_paths["json_path"],
                "md_path": file_paths["md_path"],
                "summary": {
                    "videos_processed": len(preprocessed_videos),
                    "top_viral_score": stats_summary.get("viral_score_stats", {}).get("max", 0),
                    "average_viral_score": stats_summary.get("viral_score_stats", {}).get("mean", 0)
                }
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ==================== MONGODB ENDPOINTS ====================
# Bu endpoint'ler Video Processor Agent'ın MongoDB'sindeki gerçek verilerle çalışır

@app.get("/mongodb/videos")
async def get_mongodb_videos(
    company_name: Optional[str] = None,
    company_id: Optional[str] = None,
    limit: int = FastAPIQuery(default=100, ge=1, le=500),
    include_failed: bool = False
):
    """
    MongoDB'den video analiz sonuçlarını getir.
    
    Bu endpoint Video Processor Agent'ın kaydettiği gerçek verileri döndürür.
    
    Args:
        company_name: Şirket adına göre filtrele (opsiyonel)
        company_id: PostgreSQL company ID'ye göre filtrele (opsiyonel)
        limit: Maksimum sonuç sayısı (default: 100)
        include_failed: Başarısız analizleri dahil et (default: False)
    """
    try:
        mongodb_service = get_mongodb_service()
        api_response = await mongodb_service.get_api_response(
            company_name=company_name,
            company_id=company_id,
            limit=limit,
            include_failed=include_failed
        )
        
        return api_response.model_dump()
        
    except Exception as e:
        logger.error(f"MongoDB video fetch error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB error: {str(e)}"
        )


@app.post("/analyze/mongodb")
async def analyze_from_mongodb(
    company_name: Optional[str] = None,
    company_id: Optional[str] = None,
    video_id: Optional[str] = None,
    limit: int = FastAPIQuery(default=100, ge=1, le=500)
):
    """
    MongoDB'deki gerçek verilerle analiz yap.
    
    Bu endpoint:
    1. MongoDB'den video analiz sonuçlarını çeker
    2. Preprocessing yapar
    3. İstatistik hesaplar
    4. LLM ile yorumlama yapar
    5. LLM ile öneriler üretir
    6. Rapor oluşturur
    
    Args:
        company_name: Şirket adına göre filtrele (opsiyonel)
        company_id: PostgreSQL company ID'ye göre filtrele (opsiyonel)
        video_id: Belirli bir video ID (opsiyonel)
        limit: Maksimum video sayısı (default: 100)
    """
    try:
        # Step 0: MongoDB'den veri çek
        logger.info("Step 0: Fetching data from MongoDB...")
        
        mongodb_service = get_mongodb_service()
        api_response = await mongodb_service.get_api_response(
            company_name=company_name,
            company_id=company_id,
            video_id=video_id,
            limit=limit,
            include_failed=False
        )
        
        if not api_response.data:
            raise HTTPException(
                status_code=404,
                detail="No video analysis results found in MongoDB"
            )
        
        logger.info(f"Fetched {len(api_response.data)} videos from MongoDB")
        
        # Step 1-5: Mevcut pipeline'ı kullan
        return await analyze_from_api(api_response, video_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MongoDB analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis error: {str(e)}"
        )


@app.post("/analyze/mongodb/company/{company_name}")
async def analyze_company_from_mongodb(
    company_name: str,
    limit: int = FastAPIQuery(default=100, ge=1, le=500)
):
    """
    Belirli bir şirketin tüm videolarını MongoDB'den analiz et.
    
    Args:
        company_name: Şirket adı
        limit: Maksimum video sayısı
    """
    return await analyze_from_mongodb(company_name=company_name, limit=limit)


@app.get("/mongodb/stats")
async def get_mongodb_stats():
    """
    MongoDB'deki genel istatistikleri getir.
    
    Toplam video sayısı, şirket sayısı, platform dağılımı vb.
    """
    try:
        mongodb_service = get_mongodb_service()
        await mongodb_service.connect()
        
        # Get all completed analyses
        pipeline = [
            {"$match": {"status": "completed"}},
            {"$group": {
                "_id": None,
                "total_videos": {"$sum": 1},
                "unique_companies": {"$addToSet": "$company_name"},
                "platforms": {"$addToSet": "$metadata.platform"},
                "total_segments": {"$sum": {"$size": {"$ifNull": ["$segments", []]}}},
                "total_objects": {"$sum": {"$size": {"$ifNull": ["$all_objects", []]}}}
            }}
        ]
        
        results = []
        async for doc in mongodb_service.collection.aggregate(pipeline):
            results.append(doc)
        
        if not results:
            return {
                "total_videos": 0,
                "unique_companies": 0,
                "platforms": [],
                "total_segments": 0,
                "total_objects": 0
            }
        
        stats = results[0]
        return {
            "total_videos": stats.get("total_videos", 0),
            "unique_companies": len(stats.get("unique_companies", [])),
            "company_names": stats.get("unique_companies", []),
            "platforms": stats.get("platforms", []),
            "total_segments": stats.get("total_segments", 0),
            "total_objects": stats.get("total_objects", 0)
        }
        
    except Exception as e:
        logger.error(f"MongoDB stats error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB stats error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "modules.report_analysis_agent.report_analyzier:app",
        host="0.0.0.0",
        port=8002,  # Report analysis uses port 8002
        reload=True,
        log_level="info"
    )
