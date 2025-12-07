import json
from typing import Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
from modules.report_analysis_agent.services.utils import generate_report_id, get_report_directory


def save_report(json_data: Dict[str, Any], md_text: str) -> Dict[str, str]:
    """
    Save report as both JSON and Markdown files.
    
    Args:
        json_data: Report data as dictionary
        md_text: Markdown formatted report text
    
    Returns:
        Dictionary with file paths
    """
    report_id = generate_report_id()
    report_dir = get_report_directory()
    
    # Save JSON
    json_path = report_dir / f"{report_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Save Markdown
    md_path = report_dir / f"{report_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    
    return {
        "json_path": str(json_path),
        "md_path": str(md_path),
        "report_id": report_id
    }


def build_report(
    preprocessing_summary: Dict[str, Any],
    stats_summary: Dict[str, Any],
    interpretation_output: Dict[str, Any],
    recommendations: Dict[str, Any],
    company_name: str
) -> Tuple[Dict[str, Any], str]:
    """
    Build complete report in both JSON and Markdown formats.
    
    Returns:
        Tuple of (json_data, markdown_text)
    """
    # Build JSON report
    json_report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "company": company_name,
            "report_version": "1.0"
        },
        "preprocessing_summary": preprocessing_summary,
        "statistics_summary": stats_summary,
        "llm_interpretation": interpretation_output,
        "llm_recommendations": recommendations,
        "final_notes": {
            "summary": "Analysis completed successfully",
            "next_steps": "Review recommendations and implement top priority actions"
        }
    }
    
    # Build Markdown report
    md_report = build_markdown_report(
        preprocessing_summary,
        stats_summary,
        interpretation_output,
        recommendations,
        company_name
    )
    
    return json_report, md_report


def build_markdown_report(
    preprocessing_summary: Dict[str, Any],
    stats_summary: Dict[str, Any],
    interpretation_output: Dict[str, Any],
    recommendations: Dict[str, Any],
    company_name: str
) -> str:
    """Build Markdown formatted report with error handling"""
    
    # Check for errors in interpretation or recommendations
    has_interpretation_error = "error" in interpretation_output and interpretation_output.get("error")
    has_recommendation_error = "error" in recommendations and recommendations.get("error")
    
    error_note = ""
    if has_interpretation_error or has_recommendation_error:
        error_note = "\n\n**⚠️ ANALYSIS ERRORS:**\n"
        if has_interpretation_error:
            error_note += f"- Interpretation Error: {interpretation_output.get('error')}\n"
        if has_recommendation_error:
            error_note += f"- Recommendation Error: {recommendations.get('error')}\n"
    
    md = f"""# Video Analysis Report

**Company:** {company_name}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{error_note}

---

## Executive Summary

This report analyzes video performance data to extract winning patterns, identify effective content strategies, and provide actionable recommendations for {company_name}.

**Key Metrics:**
- Total Videos Analyzed: {stats_summary.get('total_videos', 0)}
- Average Viral Score: {stats_summary.get('viral_score_stats', {}).get('mean', 0):.2f}
- Top Viral Score: {stats_summary.get('viral_score_stats', {}).get('max', 0):.2f}

---

## Trend Findings

### Top Performers

"""
    
    top_performers = stats_summary.get('top_performers', [])
    for i, performer in enumerate(top_performers[:5], 1):
        md += f"{i}. **Video {performer.get('id', 'N/A')}** - Viral Score: {performer.get('viral_score', 0):.2f} ({performer.get('emotional_tone', 'N/A')})\n"
    
    md += f"""
### Emotional Tone Distribution

"""
    tone_dist = stats_summary.get('emotional_tone_distribution', {})
    for tone, count in tone_dist.items():
        md += f"- **{tone.title()}**: {count} videos\n"
    
    md += f"""
### Viral Score Statistics

- **Mean**: {stats_summary.get('viral_score_stats', {}).get('mean', 0):.2f}
- **Median**: {stats_summary.get('viral_score_stats', {}).get('median', 0):.2f}
- **Standard Deviation**: {stats_summary.get('viral_score_stats', {}).get('std', 0):.2f}
- **Range**: {stats_summary.get('viral_score_stats', {}).get('min', 0):.2f} - {stats_summary.get('viral_score_stats', {}).get('max', 0):.2f}

---

## Marketing Recommendations

Bu bölüm, {company_name} için özel olarak hazırlanmış pazarlama önerilerini içerir. Bu öneriler, analiz edilen başarılı videolardan çıkarılan pattern'lere dayanmaktadır.

"""
    
    marketing_recs = recommendations.get('marketing_recommendations', {})
    
    # Tone Recommendations
    tone_recs = marketing_recs.get('tone', {})
    if tone_recs:
        md += "### 🎭 Ton Önerileri\n\n"
        md += f"**Önerilen Ton:** {tone_recs.get('recommended_tone', 'N/A')}\n\n"
        md += f"**Açıklama:** {tone_recs.get('tone_description', 'N/A')}\n\n"
        
        tone_examples = tone_recs.get('tone_examples', [])
        if tone_examples:
            md += "**Örnekler:**\n"
            for example in tone_examples:
                md += f"- {example}\n"
            md += "\n"
        
        tone_avoid = tone_recs.get('tone_avoid', [])
        if tone_avoid:
            md += "**Kaçınılması Gereken Tonlar:**\n"
            for avoid in tone_avoid:
                md += f"- {avoid}\n"
            md += "\n"
    
    # Voice Style Recommendations
    voice_recs = marketing_recs.get('voice_style', {})
    if voice_recs:
        md += "### 🎤 Ses Stili Önerileri\n\n"
        md += f"**Önerilen Ses Stili:** {voice_recs.get('voice_type', 'N/A')}\n\n"
        md += f"**Açıklama:** {voice_recs.get('voice_description', 'N/A')}\n\n"
        
        voice_chars = voice_recs.get('voice_characteristics', [])
        if voice_chars:
            md += "**Ses Özellikleri:**\n"
            for char in voice_chars:
                md += f"- {char}\n"
            md += "\n"
        
        voice_example = voice_recs.get('voice_examples', '')
        if voice_example:
            md += f"**Örnek Kullanım:**\n{voice_example}\n\n"
    
    # Camera Angle Recommendations
    angle_recs = marketing_recs.get('camera_angles', {})
    if angle_recs:
        md += "### 📹 Kamera Açısı Önerileri\n\n"
        
        primary_angles = angle_recs.get('primary_angles', [])
        if primary_angles:
            md += "**Önerilen Kamera Açıları:**\n"
            for angle in primary_angles:
                md += f"- {angle}\n"
            md += "\n"
        
        angle_reasoning = angle_recs.get('angle_reasoning', '')
        if angle_reasoning:
            md += f"**Neden Bu Açılar:** {angle_reasoning}\n\n"
        
        angle_usage = angle_recs.get('angle_usage', '')
        if angle_usage:
            md += f"**Kullanım:** {angle_usage}\n\n"
        
        angles_avoid = angle_recs.get('angles_to_avoid', [])
        if angles_avoid:
            md += "**Kaçınılması Gereken Açılar:**\n"
            for avoid in angles_avoid:
                md += f"- {avoid}\n"
            md += "\n"
    
    # Visual Style Recommendations
    visual_recs = marketing_recs.get('visual_style', {})
    if visual_recs:
        md += "### 🎨 Görsel Stil Önerileri\n\n"
        md += f"**Renk Paleti:** {visual_recs.get('color_palette', 'N/A')}\n\n"
        md += f"**Işıklandırma:** {visual_recs.get('lighting_style', 'N/A')}\n\n"
        md += f"**Kompozisyon:** {visual_recs.get('composition_style', 'N/A')}\n\n"
        md += f"**Görsel Ruh Hali:** {visual_recs.get('visual_mood', 'N/A')}\n\n"
    
    # Audio/Music Recommendations
    audio_recs = marketing_recs.get('audio_music', {})
    if audio_recs:
        md += "### 🎵 Ses ve Müzik Önerileri\n\n"
        md += f"**Müzik Stili:** {audio_recs.get('music_style', 'N/A')}\n\n"
        md += f"**Tempo:** {audio_recs.get('music_tempo', 'N/A')}\n\n"
        md += f"**Ses Efektleri:** {audio_recs.get('sound_effects', 'N/A')}\n\n"
        md += f"**Seslendirme Dengesi:** {audio_recs.get('voiceover_style', 'N/A')}\n\n"
    
    md += "---\n\n"
    
    # Key Takeaways
    key_takeaways = recommendations.get('key_takeaways', {})
    if key_takeaways:
        md += "## 🎯 En Önemli Öneriler\n\n"
        top_recs = key_takeaways.get('top_3_recommendations', [])
        if top_recs:
            for i, rec in enumerate(top_recs, 1):
                md += f"{i}. **{rec}**\n"
            md += "\n"
        
        why_works = key_takeaways.get('why_these_work', '')
        if why_works:
            md += f"**Neden Bu Öneriler İşe Yarar:**\n{why_works}\n\n"
        md += "---\n\n"
    
    md += f"""
## Hook Patterns

"""
    
    winning_patterns = interpretation_output.get('winning_patterns', {})
    common_hooks = winning_patterns.get('common_hooks', [])
    if common_hooks:
        md += "### Common Hook Patterns\n\n"
        for hook in common_hooks:
            md += f"- {hook}\n"
        md += "\n"
    
    emotional_triggers = winning_patterns.get('emotional_triggers', [])
    if emotional_triggers:
        md += "### Emotional Triggers\n\n"
        for trigger in emotional_triggers:
            md += f"- {trigger}\n"
        md += "\n"
    
    md += f"""
### Content Structure

{winning_patterns.get('content_structure', 'No specific patterns identified.')}

### Visual Elements

{winning_patterns.get('visual_elements', 'No specific visual patterns identified.')}

---

## CTA Insights

"""
    
    cta_analysis = interpretation_output.get('cta_analysis', {})
    effective_cta_types = cta_analysis.get('effective_cta_types', [])
    if effective_cta_types:
        md += "### Effective CTA Types\n\n"
        for cta_type in effective_cta_types:
            md += f"- {cta_type}\n"
        md += "\n"
    
    md += f"""
### CTA Placement Strategy

{cta_analysis.get('cta_placement', 'No specific placement strategy identified.')}

### CTA Language

{cta_analysis.get('cta_language', 'No specific language patterns identified.')}

---

## Recommended Video Formulas

"""
    
    viral_scripts = recommendations.get('viral_scripts', {})
    hook_formulas = viral_scripts.get('hook_formulas', [])
    if hook_formulas:
        md += "### Hook Formulas\n\n"
        for formula in hook_formulas:
            md += f"- {formula}\n"
        md += "\n"
    
    script_templates = viral_scripts.get('script_templates', [])
    if script_templates:
        md += "### Script Templates\n\n"
        for template in script_templates:
            md += f"#### {template.get('title', 'Template')}\n\n"
            md += f"**Structure**: {template.get('structure', 'N/A')}\n\n"
            md += f"**Duration**: {template.get('duration', 'N/A')}\n\n"
            if template.get('tone'):
                md += f"**Ton**: {template.get('tone', 'N/A')}\n\n"
            if template.get('voice_style'):
                md += f"**Ses Stili**: {template.get('voice_style', 'N/A')}\n\n"
            md += f"**Example**:\n```\n{template.get('example', 'N/A')}\n```\n\n"
    
    md += f"""
### Pacing Recommendations

{viral_scripts.get('pacing_recommendations', 'No specific pacing recommendations.')}

---

## Platform Strategy

"""
    
    platform_strategy = recommendations.get('platform_strategy', {})
    
    for platform in ['tiktok', 'instagram', 'youtube']:
        platform_data = platform_strategy.get(platform, {})
        if platform_data:
            md += f"### {platform.title()}\n\n"
            md += f"- **Format**: {platform_data.get('format', 'N/A')}\n"
            md += f"- **Length**: {platform_data.get('length', 'N/A')}\n"
            md += f"- **Content Type**: {platform_data.get('content_type', 'N/A')}\n"
            if platform_data.get('tone'):
                md += f"- **Önerilen Ton**: {platform_data.get('tone', 'N/A')}\n"
            if platform_data.get('camera_angle'):
                md += f"- **Önerilen Kamera Açısı**: {platform_data.get('camera_angle', 'N/A')}\n"
            md += "\n"
    
    md += "---\n\n"
    
    md += "## City-Specific Suggestions\n\n"
    city_strategy = recommendations.get('city_specific_strategy', {})
    
    local_hooks = city_strategy.get('local_hooks', [])
    if local_hooks:
        md += "### Local Hooks\n\n"
        for hook in local_hooks:
            md += f"- {hook}\n"
        md += "\n"
    
    local_refs = city_strategy.get('local_references', [])
    if local_refs:
        md += "### Local References\n\n"
        for ref in local_refs:
            md += f"- {ref}\n"
        md += "\n"
    
    md += f"""
### Cultural Notes

{city_strategy.get('cultural_notes', 'No specific cultural considerations.')}

### Trending Topics

"""
    trending = city_strategy.get('trending_topics', [])
    if trending:
        for topic in trending:
            md += f"- {topic}\n"
    else:
        md += "- No specific trending topics identified.\n"
    
    md += "\n---\n\n"
    
    md += "## Final Action Plan\n\n"
    action_plan = recommendations.get('action_plan', {})
    
    immediate_actions = action_plan.get('immediate_actions', [])
    if immediate_actions:
        md += "### Immediate Actions\n\n"
        for i, action in enumerate(immediate_actions, 1):
            md += f"{i}. {action}\n"
        md += "\n"
    
    md += f"""
### Content Calendar Suggestions

{action_plan.get('content_calendar_suggestions', 'No specific calendar suggestions.')}

### A/B Testing Ideas

"""
    ab_tests = action_plan.get('a_b_testing_ideas', [])
    if ab_tests:
        for test in ab_tests:
            md += f"- {test}\n"
    else:
        md += "- No specific A/B testing ideas.\n"
    
    md += "\n---\n\n"
    md += f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return md

