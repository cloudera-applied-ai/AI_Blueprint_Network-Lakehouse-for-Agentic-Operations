"""AI optimization endpoints - control LLM usage rates and caching"""
from fastapi import APIRouter
from ..config import settings

router = APIRouter(prefix=settings.API_V1_STR, tags=["ai-optimization"])


@router.get("/ai-optimization")
def get_ai_optimization_settings():
    """Get current AI optimization settings."""
    from ..background_tasks import background_generator
    return {
        "settings": background_generator.get_ai_optimization_settings(),
        "stats": {
            "ai_analyses_llm": background_generator.stats.get("ai_analyses_llm", 0),
            "ai_analyses_rule_based": background_generator.stats.get("ai_analyses_rule_based", 0),
            "ai_analyses_cached": background_generator.stats.get("ai_analyses_cached", 0),
            "ai_analyses_cooled_down": background_generator.stats.get("ai_analyses_cooled_down", 0),
        },
        "description": {
            "llm_sample_rate": "Use LLM for 1 in N alerts (higher = less AI cost). Set to 1 for all LLM, 10 for 10%.",
            "node_cooldown_minutes": "Minutes before re-analyzing same node. Set to 0 to disable.",
            "cache_ttl_minutes": "How long to cache analysis results. Set to 0 to disable caching.",
        }
    }


@router.put("/ai-optimization")
def update_ai_optimization_settings(
    llm_sample_rate: int = None,
    node_cooldown_minutes: int = None,
    cache_ttl_minutes: int = None,
):
    """Update AI optimization settings to reduce LLM usage and costs."""
    from ..background_tasks import background_generator
    updated = background_generator.set_ai_optimization_settings(
        llm_sample_rate=llm_sample_rate,
        node_cooldown_minutes=node_cooldown_minutes,
        cache_ttl_minutes=cache_ttl_minutes,
    )
    return {"updated": True, "settings": updated}


@router.post("/ai-optimization/clear-cache")
def clear_ai_caches():
    """Clear all AI analysis caches and node cooldowns"""
    from ..background_tasks import background_generator
    return background_generator.clear_ai_caches()
