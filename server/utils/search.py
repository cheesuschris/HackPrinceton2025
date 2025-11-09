import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SERP_API = "https://serpapi.com/search.json"

def search_web(query, num_results=3):
    """Use SerpAPI to get top search results for a query."""
    params = {
        "q": query,
        "api_key": os.environ.get("SERPAPI_KEY"),
        "num": num_results
    }
    try:
        resp = requests.get(SERP_API, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("organic_results", [])
        links = [r["link"] for r in results if "link" in r]
        return links[:num_results]
    except Exception as e:
        print("Search error:", e)
        return []

def scrape_page(url):
    """Extract readable text from a web page."""
    try:
        # Add headers to avoid compression issues
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',  # Don't request zstd
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        
        # Use response.text which handles encoding automatically
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text[:8000]  # limit size for model input
    except Exception as e:
        print("Scrape error:", e)
        return ""

if __name__ == "__main__":
    # --- Temporary test section ---
    brand = "Sweetcrispy"
    product = "Ergonomic Office Desk Chair Mesh Adjustable Swivel Mid-Back Computer Chair with Lumbar Support Comfy Flip-up Arms for Home Office"

    # Build search query
    query = f"{brand} {product} sustainability OR carbon footprint OR materials OR environmental impact"
    print(f"Searching for: {query}\n")

    # Search top pages
    links = search_web(query)
    if not links:
        print("No results found or SerpAPI key issue.")
        exit()

    print("Top results:")
    for i, link in enumerate(links, 1):
        print(f"{i}. {link}")

    print("\nScraping first page for text...\n")
    text = scrape_page(links[0])
    text2 = scrape_page(links[1])
    text3 = scrape_page(links[2])
    
    print(text[:1000], "...\n")
    #print(text2[:1000], "...\n")
    print(text3, "...\n")
