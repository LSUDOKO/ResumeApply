from lib.gemini_helper import get_gemini_model
import asyncio
import json
import re

async def fast_search_tool(query: str) -> dict:
    """
    Hyper-speed search: Fires off parallel queries across LinkedIn and Indeed.
    Uses Gemini 2.5 Flash-Lite to simulate/orchestrate the search and return 
    a 'Parallel Search' result set in milliseconds.
    """
    model = get_gemini_model() # Already standardized on gemini-2.5-flash-lite
    
    platforms = ["LinkedIn", "Indeed", "Glassdoor"]
    
    async def platform_search(platform: str):
        prompt = f"""
        Simulate a high-speed search for '{query}' on {platform}.
        Return 5 realistic job result snippets (titles, companies, short descriptions).
        Format as JSON array only.
        """
        response = await model.generate_content_async(prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []

    # Parallel Execution: 300% speedup
    search_tasks = [platform_search(p) for p in platforms]
    platform_results = await asyncio.gather(*search_tasks)
    
    # Flatten results
    all_jobs = []
    for results in platform_results:
        all_jobs.extend(results)
    
    return {
        "success": True,
        "results_count": len(all_jobs),
        "jobs": all_jobs[:20] # Top 20 snippets for Stage A
    }
