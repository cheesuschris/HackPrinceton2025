from serpapi import GoogleSearch
import os
from dotenv import load_dotenv
import json

load_dotenv()
SERP_API_KEY = os.getenv("SERPAPI_KEY")

# Import LLM service
try:
    from server.services.llm import call_llm
except ImportError:
    try:
        from services.llm import call_llm
    except ImportError:
        call_llm = None

def product_query(product_name):
    if not call_llm:
        # Fallback query if LLM not available
        return f"sustainable eco-friendly {product_name}"
    
    prompt = f"""
    Given this product: "{product_name}", Dont make the query exactly like the original product. write a Google search query to find alternative 
    products that are from sustainable, eco-friendly brands. Does not need to be from same brand. ckReturn ONLY the search query, 
    no explanations. 
    """
    
    try:
        query = call_llm(prompt, model="gemini-2.5-flash", temperature=1, max_tokens=100)
        return query.strip().strip('"').strip("'")
    except Exception:
        # Fallback query if LLM fails
        return f"sustainable eco-friendly {product_name}"



def get_sustainable_alternatives(product_name: str) -> dict:
    query = product_query(product_name)
    print(query)
    params = {
        "engine": "google_shopping",
        "q": query,
        "num": 5,
        "api_key": SERP_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    items = results.get("shopping_results", [])[:5]

    alternatives = []
    for item in items:
        # Try multiple possible field names for link
        link_url = item.get("link") or item.get("url") or item.get("product_link") or item.get("product_url") or ''
        
        alternatives.append({
            "title": item.get("title"),
            "price": item.get("price"),
            "link": link_url,
            "source": item.get("source"),
            "thumbnail": item.get("thumbnail"),
            "rating": item.get("rating"),
            "reviews": item.get("reviews")
        })

    if not alternatives:
        return {"error": "No sustainable alternatives found"}

    return {"alternatives": alternatives}


def get_sustainable_alternatives_with_analysis(analysis_text: str, product_name: str) -> dict:
    """
    Get sustainable alternatives using product analysis text.
    Uses the analysis to create a better search query.
    """
    if not call_llm:
        # Fallback to basic function if LLM not available
        return get_sustainable_alternatives(product_name)
    
    # Create a query using both product name and analysis
    prompt = f"""Given this product analysis and product name, write a Google Shopping search query to find sustainable, eco-friendly alternative products.

Product Name: {product_name}

Product Analysis:
{analysis_text[:2000]}

Write a concise Google Shopping search query (max 10 words) to find sustainable alternatives. Return ONLY the search query, no explanations."""
    
    try:
        query = call_llm(prompt, model="gemini-2.5-flash", temperature=0.3, max_tokens=100)
        query = query.strip().strip('"').strip("'")
    except Exception:
        # Fallback query
        query = f"sustainable eco-friendly {product_name}"
    
    print(f"Search query for alternatives: {query}")
    
    params = {
        "engine": "google_shopping",
        "q": query,
        "num": 5,
        "api_key": SERP_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    items = results.get("shopping_results", [])[:5]

    alternatives = []
    for item in items:
        # Debug: Print raw item to see what fields are available
        print(f"Raw SerpAPI item keys: {list(item.keys())}")
        
        # Try multiple possible field names for link
        link_url = item.get("link") or item.get("url") or item.get("product_link") or item.get("product_url") or ''
        
        alternatives.append({
            "title": item.get("title"),
            "price": item.get("price"),
            "link": link_url,
            "source": item.get("source"),
            "thumbnail": item.get("thumbnail"),
            "rating": item.get("rating"),
            "reviews": item.get("reviews")
        })
        
        print(f"Extracted link: {link_url[:80] if link_url else 'EMPTY'}")

    if not alternatives:
        return {"error": "No sustainable alternatives found"}

    return {"alternatives": alternatives, "query": query}


if __name__ == "__main__":
    product = "Legendary Whitetails Men's Flannel Shirt Long Sleeve Button Down 100% Cotton"
    print(get_sustainable_alternatives(product))

