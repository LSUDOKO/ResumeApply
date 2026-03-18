import asyncio
import os
from dotenv import load_dotenv
from tools.fast_search_tool import fast_search_tool

load_dotenv()

async def test_search():
    print("Testing fast_search_tool...")
    try:
        result = await fast_search_tool("Python Developer")
        print(f"Success! Found {result.get('results_count')} jobs.")
        for job in result.get("jobs", [])[:3]:
            print(f"- {job.get('title')} at {job.get('company')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
