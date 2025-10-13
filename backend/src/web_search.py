import requests
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def search_web(query, num_results=5):
    """
    Search the web using Serper API
    Returns list of search results with title, link, snippet
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {
            "error": "SERPER_API_KEY not found in .env file",
            "results": []
        }
    
    url = "https://google.serper.dev/search"
    
    payload = {
        "q": query,
        "num": num_results
    }
    
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()

        results = []
        if "organic" in data:
            for item in data["organic"]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "position": item.get("position", 0)
                })
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Web search failed: {str(e)}",
            "results": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "results": []
        }

def format_web_results(search_data):
    """Format web search results for display"""
    if search_data.get("error"):
        return f"Web search error: {search_data['error']}"
    
    if not search_data.get("results"):
        return "No web search results found."
    
    formatted = "**Web Search Results:**\n\n"
    for i, result in enumerate(search_data["results"], 1):
        formatted += f"{i}. **{result['title']}**\n"
        formatted += f" {result['snippet']}\n"
        formatted += f" {result['link']}\n\n"
    
    return formatted
