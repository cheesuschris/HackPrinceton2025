import os
import sys
import json
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_core.tools import tool

server_dir = Path(__file__).parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from services.llm import call_llm

load_dotenv()
SERP_API = "https://serpapi.com/search.json"

DEBUG_LOG = []
DEBUG_FILE = Path(__file__).parent / "tools_debug.json"
PRODUCT_FILE = Path(__file__).parent / "product.json"


def log_debug(step: str, data: dict):
    entry = {"timestamp": datetime.now().isoformat(), "step": step, "data": data}
    DEBUG_LOG.append(entry)
    try:
        with open(DEBUG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEBUG_LOG, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"Warning: Could not write debug log: {e}")


@tool
def search_one_tool(query: str, num_results: int = 1) -> dict:
    """Search the web for results and scrape their content.
    
    Args:
        query: The search query string
        num_results: Number of results to return (default: 1)
    
    Returns:
        A dictionary with the query and a list of results, each containing url and content.
    """
    log_debug("search_one_start", {"query": query})
    links = []
    params = {"q": query, "api_key": os.environ.get("SERPAPI_KEY"), "num": num_results}
    try:
        resp = requests.get(SERP_API, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("organic_results", [])
        links = [r["link"] for r in results if "link" in r][:num_results]
        log_debug("search_one_links", {"links": links})
    except Exception as e:
        log_debug("search_one_error", {"error": str(e)})
        return {"query": query, "results": []}

    pages = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    for url in links:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = " ".join(p.get_text() for p in soup.find_all("p"))
            pages.append({"url": url, "content": text})
            log_debug("search_one_scrape_success", {"url": url, "length": len(text)})
        except Exception as e:
            log_debug("search_one_scrape_error", {"url": url, "error": str(e)})
    return {"query": query, "results": pages}


@tool
def extract_product_info_tool(data: dict) -> dict:
    """Extract structured product information from search results using AI.
    
    Args:
        data: A dictionary containing 'query' and 'results' (list of dicts with 'url' and 'content')
    
    Returns:
        A dictionary with the query and extracted product information for each result.
    """
    query = data.get("query", "")
    results = data.get("results", [])
    if not results:
        return {"query": query, "extracted": []}

    extracted_all = []
    for r in results:
        url = r.get("url", "")
        text = r.get("content", "")
        prompt = f"""
You are a product analyst extracting structured information.

Product: {query}
Source URL: {url}

From the text below, extract if possible:
- Product name
- Brand
- Price
- Pros (short bullet list)
- Cons (short bullet list)
- Rating (if mentioned)
- Materials, manufacturing, packaging, transport info
- Any sustainability metrics (carbon footprint, recyclable %, etc.)

Return valid JSON with these fields.
Text:
{text}
"""
        try:
            extracted = call_llm(prompt, model="gemini-2.5-flash", temperature=0.0, max_tokens=4096)
            extracted_all.append({
                "url": url,
                "extracted_full_text": extracted
            })
            log_debug("extract_product_info_success", {"url": url, "result_length": len(extracted)})
        except Exception as e:
            log_debug("extract_product_info_error", {"url": url, "error": str(e)})

    return {"query": query, "extracted": extracted_all}


def parse_json_from_text(text: str) -> dict:
    """Extract JSON from text that might be wrapped in markdown code blocks."""
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
    if text.endswith("```"):
        text = text[:-3]  # Remove closing ```
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


@tool
def save_product_to_json_tool(data: dict) -> dict:
    """Save extracted product information to a JSON file, replacing existing data with new extracted info.
    
    Args:
        data: A dictionary containing 'query' and 'extracted' product data
    
    Returns:
        A dictionary with status, file path, and product info.
    """
    query = data.get("query", "")
    extracted = data.get("extracted", [])
    
    try:
        # Load existing products (dict keyed by query)
        products = {}
        if PRODUCT_FILE.exists():
            with open(PRODUCT_FILE, "r", encoding="utf-8") as f:
                products = json.load(f)
        
        # Process extracted results - combine all parsed data (no merging with existing)
        new_product_info = {}
        new_sources = []
        
        for item in extracted:
            url = item.get("url", "")
            extracted_text = item.get("extracted_full_text", "")
            
            # Parse JSON from extracted text
            parsed_data = parse_json_from_text(extracted_text)
            
            if parsed_data:
                # Combine new data directly (replace, don't merge)
                new_product_info = {**new_product_info, **parsed_data}
                
                # Track this source (only URL and timestamp, no redundant extracted_data)
                new_sources.append({
                    "url": url,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Create or update product entry
        if query not in products:
            products[query] = {
                "query": query,
                "product_info": {},
                "sources": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        # Update product entry with new data (replace, don't merge)
        products[query]["product_info"] = new_product_info
        products[query]["sources"] = new_sources
        products[query]["last_updated"] = datetime.now().isoformat()
        
        # Save back to file
        with open(PRODUCT_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        
        log_debug("save_product_to_json_success", {
            "query": query,
            "sources_count": len(new_sources)
        })
        
        return {
            "status": "saved",
            "file": str(PRODUCT_FILE),
            "query": query,
            "product_info": new_product_info,
            "sources_count": len(new_sources)
        }
    except Exception as e:
        error_msg = str(e)
        log_debug("save_product_to_json_error", {"error": error_msg})
        return {"status": "error", "error": error_msg}




if __name__ == "__main__":
    query = "Sweetcrispy Ergonomic Office Desk Chair Mesh Adjustable Swivel"
    search_result = search_one_tool.invoke({"query": query, "num_results": 1})
    print("Search Results:")
    print(json.dumps(search_result, indent=2, ensure_ascii=False))
    print("\n" + "="*50 + "\n")
    extracted = extract_product_info_tool.invoke({"data": search_result})
    print("Extracted Product Info:")
    print(json.dumps(extracted, indent=2, ensure_ascii=False))
    print("\n" + "="*50 + "\n")
    saved = save_product_to_json_tool.invoke({"data": extracted})
    print("Save Result:")
    print(json.dumps(saved, indent=2, ensure_ascii=False))
    print(f"\nSaved to {PRODUCT_FILE}")
