import os
import json
import shutil
import tempfile
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_product_images(image_paths, product_name=None):
    if not image_paths:
        return {"error": "No image paths provided"}
    
    try:
        # Prepare the prompt
        prompt = f"""Analyze these product images and extract ALL available product information. Please provide a detailed, structured analysis including:

**BASIC INFORMATION:**
1. Product Name/Title - The exact product name as shown
2. Brand Name - The manufacturer or brand name
3. Price - Current price, original price (if on sale), and any discounts
4. Rating - Overall rating (e.g., 4.5/5 stars) and number of reviews if visible
5. Availability/Stock Status - Whether the product is in stock, out of stock, or limited availability

**PRODUCT DETAILS:**
6. Materials - List all materials used in the product (e.g., metal, plastic, fabric, wood, mesh, etc.)
7. Dimensions/Size - Product dimensions, weight, capacity, or size specifications
8. Key Features - All notable features and specifications listed
9. Product Description - Detailed description of what the product is and what it does
10. Color Options - Available colors or color variants if shown

**REVIEWS & FEEDBACK:**
11. Pros - Extract positive aspects mentioned in reviews or product highlights (list as bullet points)
12. Cons - Extract negative aspects, complaints, or limitations mentioned in reviews (list as bullet points)
13. Customer Reviews Summary - Overall sentiment and common themes from reviews if visible

**ADDITIONAL INFORMATION:**
14. Shipping Information - Shipping costs, delivery time, shipping from location
15. Seller Information - Seller name, seller rating, fulfillment method (if visible)
16. Warranty/Return Policy - Any warranty or return policy information
17. Related Products or Accessories - Any related items shown
18. Any other relevant details visible in the images

Please be thorough and extract every piece of information you can see in these images. Format your response clearly with sections and bullet points where appropriate.
"""
        
        if product_name:
            prompt += f"\nThe product being searched for is: {product_name}\n"
        
        # Prepare contents list with prompt and images
        contents = [prompt]
        
        # Upload and add images
        for idx, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                print(f"Warning: Image not found: {image_path}")
                continue
            
            # For the first image, upload it
            if idx == 0:
                try:
                    uploaded_file = client.files.upload(file=image_path)
                    contents.append(uploaded_file)
                    print(f"  Uploaded image {idx + 1}: {os.path.basename(image_path)}")
                except Exception as e:
                    print(f"  Error uploading image {idx + 1}: {e}")
                    # Fallback to inline data
                    with open(image_path, 'rb') as f:
                        img_bytes = f.read()
                    contents.append(
                        types.Part.from_bytes(
                            data=img_bytes,
                            mime_type='image/png'
                        )
                    )
            else:
                # For subsequent images, use inline data
                try:
                    with open(image_path, 'rb') as f:
                        img_bytes = f.read()
                    contents.append(
                        types.Part.from_bytes(
                            data=img_bytes,
                            mime_type='image/png'
                        )
                    )
                    print(f"  Added image {idx + 1}: {os.path.basename(image_path)}")
                except Exception as e:
                    print(f"  Error reading image {idx + 1}: {e}")
                    continue
        
        if len(contents) == 1:  # Only prompt, no images
            return {"error": "No valid images could be processed"}
        
        # Generate content with Gemini
        print(f"  Sending {len(contents) - 1} images to Gemini for analysis...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=contents
        )
        
        # Extract the response text
        analysis_text = response.text if hasattr(response, 'text') else str(response)
        
        return {
            "success": True,
            "analysis": analysis_text,
            "images_analyzed": len(contents) - 1,
            "model": "gemini-2.0-flash-exp"
        }
        
    except Exception as e:
        print(f"Error analyzing images with Gemini: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def analyze_screenshot_parts(screenshot_data):
    # Extract image file paths from screenshot data
    image_paths = []
    for screenshot in screenshot_data.get("screenshots", []):
        filepath = screenshot.get("filepath")
        if filepath and os.path.exists(filepath):
            image_paths.append(filepath)
    
    if not image_paths:
        return {"error": "No valid screenshot files found"}
    
    # Analyze with Gemini
    return analyze_product_images(
        image_paths=image_paths,
        product_name=screenshot_data.get("title")
    )


def search_and_analyze_product(product_name, save_json=True, output_dir=None):
    """
    Integrated function that searches for a product, takes screenshots, analyzes with Gemini,
    uses temporary files, and returns/saves JSON result.
    
    Args:
        product_name: Name of the product to search for
        save_json: Whether to save the result as JSON file (default: True)
        output_dir: Directory to save JSON file (default: current directory)
    
    Returns:
        Dictionary with complete product analysis including screenshots and Gemini analysis
    """
    # Import search_agent_tool function
    try:
        from .search_agent_tool import get_product_data
    except ImportError:
        from search_agent_tool import get_product_data
    
    temp_dir = None
    temp_image_paths = []
    
    try:
        # Create temporary directory for screenshots
        temp_dir = tempfile.mkdtemp(prefix="product_screenshots_")
        print(f"Created temporary directory: {temp_dir}")
        
        # Get product data with screenshots
        print(f"\n{'='*80}")
        print(f"Searching for product: {product_name}")
        print(f"{'='*80}")
        
        # Call search function - we'll need to modify it to use temp dir
        # For now, let's get the screenshots and copy them to temp
        screenshot_results = get_product_data.invoke({"product_name": product_name})
        
        if "error" in screenshot_results or not screenshot_results.get("screenshot_results"):
            return {
                "success": False,
                "error": screenshot_results.get("error", "No screenshots captured"),
                "product_name": product_name
            }
        
        # Process each result
        final_results = []
        
        for result in screenshot_results.get("screenshot_results", []):
            # Copy screenshots to temp directory
            temp_image_paths = []
            original_image_paths = []
            
            for screenshot in result.get("screenshots", []):
                original_path = screenshot.get("filepath")
                if original_path and os.path.exists(original_path):
                    # Copy to temp directory
                    filename = os.path.basename(original_path)
                    temp_path = os.path.join(temp_dir, filename)
                    shutil.copy2(original_path, temp_path)
                    temp_image_paths.append(temp_path)
                    original_image_paths.append(original_path)
            
            if not temp_image_paths:
                continue
            
            # Analyze with Gemini
            print(f"\nAnalyzing {len(temp_image_paths)} images with Gemini...")
            gemini_result = analyze_product_images(
                image_paths=temp_image_paths,
                product_name=result.get("title")
            )
            
            # Combine results
            combined_result = {
                "product_name": product_name,
                "search_result": {
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "snippet": result.get("snippet"),
                    "screenshot_count": len(temp_image_paths)
                },
                "gemini_analysis": gemini_result,
                "timestamp": datetime.now().isoformat(),
                "success": gemini_result.get("success", False)
            }
            
            final_results.append(combined_result)
            
            # Clean up temp images for this result
            for temp_path in temp_image_paths:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    print(f"Warning: Could not delete temp file {temp_path}: {e}")
        
        # Prepare final JSON result
        json_result = {
            "product_name": product_name,
            "timestamp": datetime.now().isoformat(),
            "results": final_results,
            "total_results": len(final_results)
        }
        
        # Save JSON if requested
        if save_json:
            if output_dir is None:
                output_dir = os.path.dirname(os.path.dirname(__file__))
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Create filename
            safe_product_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_product_name = safe_product_name.replace(' ', '_')[:50]
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"product_analysis_{safe_product_name}_{timestamp_str}.json"
            json_filepath = os.path.join(output_dir, json_filename)
            
            # Save JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(json_result, f, indent=2, ensure_ascii=False)
            
            print(f"\nJSON result saved to: {json_filepath}")
            json_result["json_filepath"] = json_filepath
        
        return json_result
        
    except Exception as e:
        print(f"Error in search_and_analyze_product: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "product_name": product_name
        }
    
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Warning: Could not delete temp directory {temp_dir}: {e}")


if __name__ == "__main__":
    # Example usage of integrated function
    product_name = "Sweetcrispy Ergonomic Office Desk Chair Mesh Adjustable Swivel Mid-Back Computer Chair with Lumbar Support"
    
    print("="*80)
    print("INTEGRATED PRODUCT SEARCH AND ANALYSIS")
    print("="*80)
    
    result = search_and_analyze_product(product_name, save_json=True)
    
    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    
    if result.get("success") or result.get("total_results", 0) > 0:
        print(f"\nProduct: {result.get('product_name')}")
        print(f"Total Results: {result.get('total_results', 0)}")
        print(f"Timestamp: {result.get('timestamp')}")
        
        if result.get("json_filepath"):
            print(f"\nJSON saved to: {result.get('json_filepath')}")
        
        # Print first result analysis
        if result.get("results"):
            first_result = result["results"][0]
            if first_result.get("gemini_analysis", {}).get("success"):
                print(f"\n{'='*80}")
                print("GEMINI ANALYSIS (First Result)")
                print(f"{'='*80}")
                analysis = first_result["gemini_analysis"].get("analysis", "")
                print(analysis[:2000])  # Print first 2000 chars
                if len(analysis) > 2000:
                    print(f"\n... (truncated, see JSON file for full analysis)")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

