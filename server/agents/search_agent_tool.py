import os
import json
import tempfile
import shutil
from serpapi import GoogleSearch
from dotenv import load_dotenv
from langchain.tools import tool
from playwright.sync_api import sync_playwright
import base64
from datetime import datetime
import re
from PIL import Image

load_dotenv()
SERP_API_KEY = os.getenv("SERPAPI_KEY")


@tool("search_product_info", return_direct=False)
def get_product_data(product_name: str) -> dict:
    """Search for a product online using SerpAPI and take screenshots of the top search results using Playwright."""
    params = {
        "engine": "google",
        "q": product_name,
        "num": 3,
        "api_key": SERP_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results.get("organic_results", [])[:1]

    if not organic_results:
        return {"error": "No search results found"}

    # Create screenshots directory
    screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    
    screenshot_results = []

    with sync_playwright() as p:
        # Launch browser with additional options
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']  # Help avoid bot detection
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            # Add extra headers to look more like a real browser
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        )
        page = context.new_page()
        
        # Set additional page properties to avoid detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        for idx, result in enumerate(organic_results, 1):
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")

            if not link:
                continue

            print(f"\n{'='*80}")
            print(f"Processing URL {idx}: {link}")
            print(f"{'='*80}")

            try:
                # Navigate to the page - use 'load' instead of 'networkidle' for better reliability
                # Amazon pages often have continuous network activity that never becomes idle
                print(f"  Navigating to page...")
                try:
                    page.goto(link, wait_until='load', timeout=60000)
                except Exception as nav_error:
                    # If load times out, try with domcontentloaded (faster, less reliable)
                    print(f"  'load' timed out, trying 'domcontentloaded'...")
                    try:
                        page.goto(link, wait_until='domcontentloaded', timeout=60000)
                    except Exception:
                        # Last resort: just navigate without waiting
                        print(f"  Navigation wait failed, proceeding anyway...")
                        page.goto(link, timeout=60000)
                
                # Wait for page to stabilize and dynamic content to load
                print(f"  Waiting for page content to load...")
                page.wait_for_timeout(3000)  # Increased wait time
                
                # Try to wait for common page elements (optional, won't fail if not found)
                try:
                    page.wait_for_selector('body', timeout=5000)
                except:
                    pass
                
                # Create filename base
                safe_title = re.sub(r'[^\w\s-]', '', title)[:50]  # Sanitize title
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                all_screenshots = []
                
                # Take one full-page screenshot
                print(f"Taking full-page screenshot...")
                filename_full = f"{idx}_{safe_title}_{timestamp}_full.png"
                filepath_full = os.path.join(screenshots_dir, filename_full)
                
                screenshot_bytes = page.screenshot(path=filepath_full, full_page=True)
                
                print(f"  Full screenshot saved: {filename_full} ({len(screenshot_bytes)} bytes)")
                
                # Divide the image into 5 parts
                print(f"  Dividing image into 5 parts...")
                image = Image.open(filepath_full)
                width, height = image.size
                part_height = height // 5
                
                print(f"    Image size: {width}x{height} pixels")
                print(f"    Each part height: {part_height} pixels")
                
                for part_num in range(5):
                    # Calculate crop coordinates
                    top = part_num * part_height
                    bottom = (part_num + 1) * part_height if part_num < 4 else height
                    
                    # Crop the image
                    part_image = image.crop((0, top, width, bottom))
                    
                    # Save the part
                    filename_part = f"{idx}_{safe_title}_{timestamp}_part{part_num + 1}.png"
                    filepath_part = os.path.join(screenshots_dir, filename_part)
                    part_image.save(filepath_part)
                    
                    # Convert to base64 - read the saved file
                    with open(filepath_part, 'rb') as f:
                        part_bytes = f.read()
                    screenshot_base64 = base64.b64encode(part_bytes).decode('utf-8')
                    
                    all_screenshots.append({
                        "screenshot_number": part_num + 1,
                        "scroll_position": f"part_{part_num + 1}_of_5",
                        "filepath": filepath_part,
                        "filename": filename_part,
                        "screenshot_base64": screenshot_base64,
                        "screenshot_size_bytes": len(part_bytes),
                        "crop_coordinates": {"top": top, "bottom": bottom, "left": 0, "right": width}
                    })
                    
                    print(f"    Part {part_num + 1} saved: {filename_part} ({len(part_bytes)} bytes)")
                
                # Store all screenshot data
                screenshot_data = {
                    "url": link,
                    "title": title,
                    "snippet": snippet,
                    "total_screenshots": len(all_screenshots),
                    "screenshots": all_screenshots
                }
                
                screenshot_results.append(screenshot_data)
                print(f"\nSuccessfully captured and divided screenshot into 5 parts for: {link}")

            except Exception as e:
                print(f"Error taking screenshots of {link}: {e}")
                import traceback
                traceback.print_exc()
                continue

        browser.close()

    # Analyze screenshots with Gemini and save JSON
    if screenshot_results:
        print(f"\n{'='*80}")
        print("ANALYZING SCREENSHOTS WITH GEMINI")
        print(f"{'='*80}")
        
        try:
            # Import Gemini analysis function
            try:
                from .gemini_image import analyze_product_images
            except ImportError:
                from gemini_image import analyze_product_images
            
            # Create temp directory for images
            temp_dir = tempfile.mkdtemp(prefix="product_analysis_")
            temp_image_paths = []
            
            try:
                final_results = []
                
                for result in screenshot_results:
                    # Copy screenshots to temp directory
                    temp_image_paths = []
                    
                    for screenshot in result.get("screenshots", []):
                        original_path = screenshot.get("filepath")
                        if original_path and os.path.exists(original_path):
                            filename = os.path.basename(original_path)
                            temp_path = os.path.join(temp_dir, filename)
                            shutil.copy2(original_path, temp_path)
                            temp_image_paths.append(temp_path)
                    
                    if not temp_image_paths:
                        continue
                    
                    # Analyze with Gemini
                    print(f"\nAnalyzing {len(temp_image_paths)} images for: {result.get('title')}")
                    gemini_result = analyze_product_images(
                        image_paths=temp_image_paths,
                        product_name=result.get("title")
                    )
                    
                    # Combine results
                    combined_result = {
                        "search_result": {
                            "url": result.get("url"),
                            "title": result.get("title"),
                            "snippet": result.get("snippet"),
                            "screenshot_count": len(temp_image_paths)
                        },
                        "gemini_analysis": gemini_result,
                        "success": gemini_result.get("success", False)
                    }
                    
                    final_results.append(combined_result)
                    
                    # Clean up temp images
                    for temp_path in temp_image_paths:
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except Exception as e:
                            print(f"Warning: Could not delete temp file {temp_path}: {e}")
                
                # Prepare JSON result
                json_result = {
                    "product_name": product_name,
                    "timestamp": datetime.now().isoformat(),
                    "results": final_results,
                    "total_results": len(final_results)
                }
                
                # Save JSON file
                base_dir = os.path.dirname(os.path.dirname(__file__))
                os.makedirs(base_dir, exist_ok=True)
                
                safe_product_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_product_name = safe_product_name.replace(' ', '_')[:50]
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_filename = f"product_analysis_{safe_product_name}_{timestamp_str}.json"
                json_filepath = os.path.join(base_dir, json_filename)
                
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_result, f, indent=2, ensure_ascii=False)
                
                print(f"\n{'='*80}")
                print(f"JSON RESULT SAVED")
                print(f"{'='*80}")
                print(f"File: {json_filepath}")
                print(f"Total Results: {len(final_results)}")
                
                # Return combined result
                return {
                    "screenshot_results": screenshot_results,
                    "gemini_analysis": final_results,
                    "json_filepath": json_filepath,
                    "json_result": json_result
                }
                
            finally:
                # Clean up temp directory
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        print(f"Warning: Could not delete temp directory {temp_dir}: {e}")
        
        except Exception as e:
            print(f"Error in Gemini analysis: {e}")
            import traceback
            traceback.print_exc()
            # Return screenshots even if Gemini fails
            return {"screenshot_results": screenshot_results, "gemini_error": str(e)}

    return {"screenshot_results": screenshot_results}


if __name__ == "__main__":
    product = "Sweetcrispy Ergonomic Office Desk Chair Mesh Adjustable Swivel Mid-Back Computer Chair with Lumbar Support"
    res = get_product_data.invoke({"product_name": product})
    print("\n" + "="*80)
    print("FINAL RESULTS SUMMARY")
    print("="*80)
    
    # Show JSON file path if saved
    if res.get("json_filepath"):
        print(f"\n✓ JSON saved to: {res.get('json_filepath')}")
        print(f"✓ Total Results: {res.get('json_result', {}).get('total_results', 0)}")
    
    # Show screenshot results
    for idx, result in enumerate(res.get("screenshot_results", []), 1):
        print(f"\n--- Screenshot Result {idx} ---")
        print(f"URL: {result.get('url')}")
        print(f"Title: {result.get('title')}")
        print(f"Total Screenshots: {result.get('total_screenshots', 0)}")
        print(f"\nScreenshot Files:")
        for screenshot in result.get('screenshots', []):
            print(f"  - {screenshot.get('filename')} ({screenshot.get('screenshot_size_bytes', 0)} bytes)")
    
    # Show Gemini analysis results
    if res.get("gemini_analysis"):
        print(f"\n{'='*80}")
        print("GEMINI ANALYSIS RESULTS")
        print(f"{'='*80}")
        for idx, analysis in enumerate(res.get("gemini_analysis", []), 1):
            print(f"\n--- Analysis {idx} ---")
            print(f"Product: {analysis.get('search_result', {}).get('title')}")
            if analysis.get("gemini_analysis", {}).get("success"):
                gemini_text = analysis.get("gemini_analysis", {}).get("analysis", "")
                print(f"\nAnalysis Preview (first 500 chars):")
                print(gemini_text[:500])
                if len(gemini_text) > 500:
                    print(f"\n... (see JSON file for full analysis)")
            else:
                print(f"Error: {analysis.get('gemini_analysis', {}).get('error', 'Unknown error')}")
    
    print("\n" + "="*80)
