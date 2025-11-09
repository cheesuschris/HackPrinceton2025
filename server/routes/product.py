from flask import Blueprint, request, jsonify
import logging
import json

bp = Blueprint("product", __name__, url_prefix="/api")

logger = logging.getLogger(__name__)

# Import search agent and transform
try:
    from server.agents.search_agent_tool import get_product_data
except ImportError:
    try:
        from agents.search_agent_tool import get_product_data
    except ImportError:
        get_product_data = None

try:
    from server.agents.transform import transform_product
except ImportError:
    try:
        from agents.transform import transform_product
    except ImportError:
        transform_product = None

# Helper function to safely parse JSON from LLM response
def _safe_load_json(text: str):
    """Safely parse JSON from LLM response, handling markdown fences and other formats"""
    import re
    if not text:
        return None
    
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try extracting JSON from markdown code blocks
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass
    
    # Try finding first balanced JSON object
    start = text.find('{')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except Exception:
                        pass
    
    raise ValueError(f"Unable to parse JSON from text: {text[:200]}")

# Import LLM service
try:
    from server.services.llm import call_llm
except ImportError:
    try:
        from services.llm import call_llm
    except ImportError:
        call_llm = None

# Import carbon calculation service
try:
    from server.services.carbon_calc import calculate_carbon_footprint
except ImportError:
    try:
        from services.carbon_calc import calculate_carbon_footprint
    except ImportError:
        calculate_carbon_footprint = None

# Import recommender
try:
    from server.agents.recommend import get_sustainable_alternatives_with_analysis
except ImportError:
    try:
        from agents.recommend import get_sustainable_alternatives_with_analysis
    except ImportError:
        get_sustainable_alternatives_with_analysis = None


@bp.route('/product', methods=['POST'])
def receive_product():
    """Receive product data from extension and run full pipeline"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Basic product shape passed to pipeline
        product_data = {
            'platform': data.get('platform'),
            'url': data.get('url'),
            'image': data.get('image'),
            'name': data.get('name'),
            'price': data.get('price'),
            'rating': data.get('rating'),
            'shipper': data.get('shipper'),
            'seller': data.get('seller'),
            'reviews': data.get('reviews', []),
            'shippingFrom': data.get('shippingFrom'),
            'fulfilledBy': data.get('fulfilledBy'),
            'availability': data.get('availability'),
            'brand': data.get('brand'),
            'sku': data.get('sku') or data.get('id')
        }

        logger.info("Received product: %s", product_data.get('name'))

        # Step 1: Run search agent (analyzer)
        search_result = None
        if get_product_data is None:
            pass
        else:
            product_name = product_data.get('name')
            if not product_name:
                return jsonify({
                    'error': 'Product name is required for search',
                    'status': 'error'
                }), 400
            
            try:
                search_result = get_product_data.invoke({"product_name": product_name})
            except Exception as e:
                import traceback
                traceback.print_exc()

        # Step 2: Run transform
        transform_result = None
        if transform_product is None:
            pass
        else:
            try:
                transform_result = transform_product(product_data, max_tokens=2048)
            except Exception as e:
                import traceback
                traceback.print_exc()

        # Step 3: Fill missing values using analysis and LLM
        filled_transform_result = None
        if transform_result and search_result and call_llm:
            # Extract analysis text from search_result
            analysis_text = ""
            if search_result.get("gemini_analysis"):
                gemini_analysis = search_result["gemini_analysis"][0] if search_result["gemini_analysis"] else None
                if gemini_analysis and gemini_analysis.get("gemini_analysis", {}).get("success"):
                    analysis_text = gemini_analysis.get("gemini_analysis", {}).get("analysis", "")
            
            if analysis_text:
                # Create prompt to fill missing values
                prompt = f"""You are a data completion agent. Your task is to fill in missing (null) values in a carbon footprint calculation input JSON based on product analysis.

The product analysis provides detailed information about the product:
{analysis_text}

Current transform result (with some null values):
{json.dumps(transform_result, indent=2, ensure_ascii=False)}

Your task:
1. Identify all null values in the transform result
2. Use the product analysis to estimate reasonable values for these null fields
3. Return ONLY a valid JSON object with the same structure as the transform result, but with null values filled in based on estimation
4. Keep all existing non-null values exactly as they are
5. For numeric fields, provide reasonable estimates (e.g., weight in kg, distances in km, emission factors)
6. For string fields, provide reasonable values (e.g., material names, locations)
7. Mark estimated values in the "source" fields as "estimated_from_analysis" or "model_based_estimate"

Return ONLY the JSON object, no explanations or markdown. The JSON must be valid and parseable.

Example structure:
{{
  "materials": [
    {{
      "name": "material_name",
      "weight": 0.5,
      "weight_source": "estimated_from_analysis",
      "emission_factor": 2.5,
      "emission_factor_source": "estimated_from_analysis"
    }}
  ],
  "manufacturing_factor": {{
    "value": 1.2,
    "source": "estimated_from_analysis"
  }},
  "transport": {{
    "origin": "China",
    "distance_km": 10000,
    "mode": "ship",
    "emission_factor_ton_km": 0.01,
    "source": "estimated_from_analysis"
  }},
  "packaging": {{
    "weight": 0.1,
    "emission_factor": 2.0,
    "source": "estimated_from_analysis"
  }},
  "product_weight": {{
    "value": 1.5,
    "source": "estimated_from_analysis"
  }}
}}

Now fill in the null values in the transform result based on the analysis:"""

                try:
                    llm_response = call_llm(prompt, model="gemini-2.5-flash", temperature=0.3, max_tokens=4096)
                    filled_transform_result = _safe_load_json(llm_response)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    filled_transform_result = transform_result  # Use original if filling fails
            else:
                filled_transform_result = transform_result  # Use original if no analysis
        else:
            filled_transform_result = transform_result  # Use original if we can't fill

        # Step 4: Calculate carbon footprint
        carbon_result = None
        if filled_transform_result and calculate_carbon_footprint:
            try:
                carbon_result = calculate_carbon_footprint(filled_transform_result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                carbon_result = None

        # Step 5: Get sustainable alternatives using analysis
        alternatives_result = None
        if search_result and get_sustainable_alternatives_with_analysis:
            # Extract analysis text and product name
            analysis_text = ""
            product_name = product_data.get('name', '')
            
            if search_result.get("gemini_analysis"):
                gemini_analysis = search_result["gemini_analysis"][0] if search_result["gemini_analysis"] else None
                if gemini_analysis and gemini_analysis.get("gemini_analysis", {}).get("success"):
                    analysis_text = gemini_analysis.get("gemini_analysis", {}).get("analysis", "")
            
            if analysis_text and product_name:
                try:
                    alternatives_result = get_sustainable_alternatives_with_analysis(analysis_text, product_name)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    alternatives_result = None

        # Print only the final filled transform result and carbon score
        print(f"\n{'='*80}")
        print("FILLED TRANSFORM RESULT:")
        print(f"{'='*80}")
        print(json.dumps(filled_transform_result, indent=2, ensure_ascii=False, default=str))
        print(f"{'='*80}\n")
        
        if carbon_result:
            print(f"\n{'='*80}")
            print("CARBON FOOTPRINT CALCULATION:")
            print(f"{'='*80}")
            print(json.dumps(carbon_result, indent=2, ensure_ascii=False, default=str))
            print(f"{'='*80}\n")

        # Build response compatible with frontend expectations
        response = {
            'message': 'Product analyzed and transformed',
            'status': 'success'
        }
        
        # Add C0Score for frontend compatibility - this is what the frontend expects
        if carbon_result:
            cf_total = carbon_result.get('cf_total')
            if cf_total is not None:
                response['C0Score'] = float(cf_total)
            else:
                # Fallback: try to calculate from breakdown
                breakdown = carbon_result.get('breakdown', {})
                if breakdown:
                    cf_total = sum(float(v) for v in breakdown.values() if v is not None)
                    response['C0Score'] = float(cf_total)
        else:
            # Set a default if carbon calculation failed
            response['C0Score'] = None
        
        # Format alternatives for frontend (link1, link2, etc.) - top 5 alternatives
        if alternatives_result and alternatives_result.get('alternatives'):
            alternatives = alternatives_result['alternatives']
            print(f"\nFound {len(alternatives)} alternatives")
            for i in range(min(5, len(alternatives))):
                alt = alternatives[i]
                idx = i + 1
                
                # Debug: Print what's in the alternative
                print(f"  Alternative {idx} raw data: {alt}")
                
                # Try multiple possible field names for link
                link_url = alt.get('link') or alt.get('url') or alt.get('product_link') or alt.get('web_url') or ''
                response[f"link{idx}"] = link_url
                response[f"link{idx}Image"] = alt.get('thumbnail', '') or alt.get('image', '') or ''
                response[f"link{idx}Explanation"] = f"Sustainable alternative: {alt.get('title', '')} - Price: {alt.get('price', 'N/A')}"
                # Note: C0Score for alternatives would need to be calculated separately
                response[f"link{idx}C0Score"] = None
                print(f"  Added link{idx}: {alt.get('title', 'N/A')[:50]} | Link: {link_url[:50] if link_url else 'EMPTY'}")
        else:
            print(f"\nNo alternatives found. alternatives_result: {alternatives_result}")
        
        # Save final output to JSON file
        import os
        from datetime import datetime
        
        base_dir = os.path.dirname(os.path.dirname(__file__))
        os.makedirs(base_dir, exist_ok=True)
        
        # Create final output structure
        final_output = {
            'carbon_score': response.get('C0Score'),
            'links': []
        }
        
        # Add all links to final output
        for i in range(1, 6):
            link_url = response.get(f'link{i}', '')
            link_image = response.get(f'link{i}Image', '')
            link_explanation = response.get(f'link{i}Explanation', '')
            link_c0_score = response.get(f'link{i}C0Score')
            
            # Add link if we have at least a URL or explanation (some might have explanation but no URL)
            if link_url or link_explanation:
                link_data = {
                    'link': link_url or '',
                    'image': link_image or '',
                    'explanation': link_explanation or '',
                    'c0_score': link_c0_score
                }
                final_output['links'].append(link_data)
                print(f"  Added to final_output links: {link_data['explanation'][:50] if link_data['explanation'] else 'No explanation'}")
        
        # Save to JSON file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"final_output_{timestamp_str}.json"
        json_filepath = os.path.join(base_dir, json_filename)
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False, default=str)
        
        # Add final_output structure and filepath to response
        response['final_output'] = final_output
        response['final_output_file'] = json_filepath
        
        # Debug: Print final response structure
        print(f"\n{'='*80}")
        print("FINAL RESPONSE TO FRONTEND:")
        print(f"{'='*80}")
        print(f"C0Score: {response.get('C0Score')}")
        print(f"link1: {response.get('link1', 'NOT SET')}")
        print(f"link1Image: {response.get('link1Image', 'NOT SET')}")
        print(f"link1Explanation: {response.get('link1Explanation', 'NOT SET')[:50] if response.get('link1Explanation') else 'NOT SET'}")
        print(f"Final output saved to: {json_filepath}")
        print(f"{'='*80}\n")

        return jsonify(response), 200

    except Exception:
        logger.exception("Error in receive_product")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500
