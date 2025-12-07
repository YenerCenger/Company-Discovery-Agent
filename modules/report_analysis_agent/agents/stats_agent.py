from typing import List, Dict, Any
from modules.report_analysis_agent.models.video_model import VideoPreprocessed
from collections import Counter, defaultdict
from sklearn.cluster import KMeans
import numpy as np


def compute_statistics(videos: List[VideoPreprocessed]) -> Dict[str, Any]:
    """
    Compute statistical metrics:
    - viral_score ranking
    - top performer selection
    - entity clustering (KMeans)
    - emotional tone aggregation
    - thematic grouping
    """
    if not videos:
        return {
            "total_videos": 0,
            "top_performers": [],
            "viral_score_stats": {},
            "emotional_tone_distribution": {},
            "entity_clusters": {},
            "thematic_groups": {}
        }
    
    # Viral score ranking
    ranked_videos = sorted(videos, key=lambda v: v.viral_score, reverse=True)
    top_performers = [
        {
            "id": v.id,
            "viral_score": v.viral_score,
            "url": v.url,
            "emotional_tone": v.emotional_tone
        }
        for v in ranked_videos[:5]  # Top 5
    ]
    
    # Viral score statistics (overall)
    viral_scores = [v.viral_score for v in videos]
    viral_score_stats = {
        "mean": float(np.mean(viral_scores)),
        "median": float(np.median(viral_scores)),
        "std": float(np.std(viral_scores)),
        "min": float(np.min(viral_scores)),
        "max": float(np.max(viral_scores)),
    }

    # Platform-level performance (which platforms are most effective?)
    platform_scores: Dict[str, List[float]] = defaultdict(list)
    for v in videos:
        platform_scores[v.platform].append(v.viral_score)

    platform_performance = []
    for platform, scores in platform_scores.items():
        platform_performance.append(
            {
                "platform": platform,
                "avg_viral_score": float(np.mean(scores)),
                "video_count": len(scores),
            }
        )

    # Sort platforms by average viral score (desc)
    platform_performance = sorted(
        platform_performance,
        key=lambda p: p["avg_viral_score"],
        reverse=True,
    )
    
    # Emotional tone aggregation
    emotional_tones = [v.emotional_tone for v in videos]
    tone_distribution = {k: int(v) for k, v in Counter(emotional_tones).items()}
    
    # Entity clustering
    entity_clusters = perform_entity_clustering(videos)
    
    # Thematic grouping (based on common entities and objects)
    thematic_groups = group_by_themes(videos)
    
    return {
        "total_videos": len(videos),
        "top_performers": top_performers,
        "viral_score_stats": viral_score_stats,
        "platform_performance": platform_performance,
        "emotional_tone_distribution": tone_distribution,
        "entity_clusters": entity_clusters,
        "thematic_groups": thematic_groups
    }


def perform_entity_clustering(videos: List[VideoPreprocessed], n_clusters: int = 3) -> Dict[str, Any]:
    """Cluster videos based on entity frequency"""
    if len(videos) < n_clusters:
        return {"clusters": [], "n_clusters": len(videos)}
    
    # Collect all unique entities
    all_entities = set()
    for video in videos:
        all_entities.update(video.key_entities)
    
    all_entities = sorted(list(all_entities))
    
    if not all_entities:
        return {"clusters": [], "n_clusters": 0}
    
    # Create feature vectors (entity frequency per video)
    feature_vectors = []
    for video in videos:
        vector = [video.entity_frequency.get(entity, 0) for entity in all_entities]
        feature_vectors.append(vector)
    
    feature_vectors = np.array(feature_vectors)
    
    # Apply KMeans clustering
    try:
        kmeans = KMeans(n_clusters=min(n_clusters, len(videos)), random_state=42, n_init=10)
        clusters = kmeans.fit_predict(feature_vectors)
        
        # Group videos by cluster
        cluster_groups = {}
        for idx, cluster_id in enumerate(clusters):
            # Convert numpy int32 to Python int for JSON serialization
            cluster_id_int = int(cluster_id)
            if cluster_id_int not in cluster_groups:
                cluster_groups[cluster_id_int] = []
            cluster_groups[cluster_id_int].append({
                "video_id": videos[idx].id,
                "entities": videos[idx].key_entities,
                "viral_score": videos[idx].viral_score
            })
        
        return {
            "clusters": cluster_groups,
            "n_clusters": int(len(cluster_groups)),
            "entity_vocabulary": all_entities
        }
    except Exception as e:
        return {"clusters": {}, "n_clusters": 0, "error": str(e)}


def group_by_themes(videos: List[VideoPreprocessed]) -> Dict[str, List[str]]:
    """Group videos by common themes (entities + objects)"""
    themes = {}
    
    for video in videos:
        # Create theme key from top entities and objects
        theme_key = "_".join(sorted(video.key_entities[:3] + video.objects[:2]))
        
        if theme_key not in themes:
            themes[theme_key] = []
        
        themes[theme_key].append({
            "video_id": video.id,
            "viral_score": video.viral_score,
            "entities": video.key_entities,
            "objects": video.objects
        })
    
    # Filter themes with at least 2 videos
    significant_themes = {
        k: v for k, v in themes.items() if len(v) >= 2
    }
    
    return significant_themes













