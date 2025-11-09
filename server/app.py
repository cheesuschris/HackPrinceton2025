from flask import Flask, jsonify, request, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS
import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from server.routes.product import bp as product_bp
from server.database import init_db

app = Flask(__name__, static_folder='static', template_folder='templates')

MONGO_URI = os.getenv('MONGO_URI')
app.config['MONGO_URI'] = MONGO_URI

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = os.urandom(16).hex()
app.config['SECRET_KEY'] = SECRET_KEY

DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

mongo = PyMongo(app)
CORS(app)

app.register_blueprint(product_bp)

@app.route('/')
def home():
    """Home route"""
    return jsonify({
        'message': 'Welcome to the Carbon0 Flask server',
        'status': 'running'
    })

@app.route('/cart/checkout', methods=['POST'])
def cart_checkout():
    try:
        data = request.get_json()
        amount = data.get('amount')
        if not mongo.db.TotalCarbonReduced.find_one():
            mongo.db.TotalCarbonReduced.insert_one({'Total': amount})
            return jsonify({
                'message': 'Carbon reduction tracked',
                'total': amount,
                'added': amount
            }), 201
        else:
            new_amount = mongo.db.TotalCarbonReduced.find_one().get('Total') + amount
            mongo.db.TotalCarbonReduced.update_one(
                {'_id': mongo.db.TotalCarbonReduced.find_one()['_id']},
                {'$set': {'Total': new_amount}}
            )
            return jsonify({
                'message': 'Carbon reduction updated',
                'Total': new_amount,
                'added': amount
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/carbon-total', methods=['GET'])
def get_carbon_total():
    try:
        doc = mongo.db.TotalCarbonReduced.find_one()
        if doc:
            total = doc.get('Total', 0)
            return jsonify({'total': total}), 200
        else:
            return jsonify({'total': 0}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/gemini-key', methods=['GET'])
def get_gemini_key():
    """Get Gemini API key (for frontend use)"""
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        return jsonify({
            'error': 'GEMINI_API_KEY environment variable not set'
        }), 500
    return jsonify({
        'key': gemini_key
    }), 200

@app.route('/cart', methods=['GET'])
def cart_page():
    """Carbon0 cart page for tracking alternatives and CO2 savings"""
    return send_from_directory('templates', 'cart.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/product', methods=['POST'])
def receive_product():
    """Receive product data from extension"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
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
            'brand': data.get('brand')
        }
        
        print(f"\n{'='*60}")
        print(f"Received product data: {product_data['name']} from {product_data['platform']}")
        print(f"{'='*60}")
        import json
        print(json.dumps(product_data, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        return jsonify({
            'message': 'Product data received successfully',
            'data': product_data,
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/product/search', methods=['POST'])
def search_product_info():
    """
    Search for product information using search_agent_tool.
    First updates state from product data, then searches for additional info.
    """
    try:
        data = request.get_json()
        
        # Print incoming request data
        print(f"\n{'='*80}")
        print("API REQUEST RECEIVED: /api/product/search")
        print(f"{'='*80}")
        print(f"Product Name: {data.get('name', 'N/A')}")
        print(f"Platform: {data.get('platform', 'N/A')}")
        print(f"URL: {data.get('url', 'N/A')}")
        print(f"Price: {data.get('price', 'N/A')}")
        print(f"Brand: {data.get('brand', 'N/A')}")
        print(f"{'='*80}\n")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Import helper and state
        try:
            from server.agents.helper import update_state_from_product_data
            from server.agents.state import ProductCO2State
        except ImportError:
            from agents.helper import update_state_from_product_data
            from agents.state import ProductCO2State
        
        # Initialize state
        # Note: product_name is required in TypedDict, so we'll set it to empty string initially
        initial_state: ProductCO2State = {
            "product_name": "",
            "product_url": None,
            "raw_description": None,
            "materials": None,
            "weight_kg": None,
            "manufacturing_location": None,
            "shipping_distance_km": None,
            "packaging_type": None,
            "co2_score": None,
            "data_sources": [],
            "missing_fields": [],
            "stage": "init",
            "error": None
        }
        
        # Prepare product data from request
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
            'description': data.get('description'),
            'materials': data.get('materials'),
            'weight': data.get('weight'),
            'packaging': data.get('packaging')
        }
        
        # Step 1: Update state from product data
        print(f"\n{'='*80}")
        print("STEP 1: Updating state from product data")
        print(f"{'='*80}")
        updated_state = update_state_from_product_data(initial_state, product_data)
        print(f"State updated. Stage: {updated_state.get('stage')}")
        print(f"Missing fields: {updated_state.get('missing_fields')}")
        
        # Step 2: Use search_agent_tool to get additional product info
        product_name = product_data.get('name') or updated_state.get('product_name')
        
        if not product_name:
            return jsonify({
                'error': 'Product name is required for search',
                'state': updated_state
            }), 400
        
        print(f"\n{'='*80}")
        print(f"STEP 2: Searching for product: {product_name}")
        print(f"{'='*80}")
        
        # Import and use search_agent_tool
        try:
            from server.agents.search_agent_tool import get_product_data
        except ImportError:
            from agents.search_agent_tool import get_product_data
        
        # Search for product
        search_result = get_product_data.invoke({"product_name": product_name})
        
        # Extract Gemini analysis if available
        gemini_analysis = None
        if search_result.get("gemini_analysis"):
            gemini_analysis = search_result["gemini_analysis"][0] if search_result["gemini_analysis"] else None
        
        # Try to extract additional info from Gemini analysis
        if gemini_analysis and gemini_analysis.get("gemini_analysis", {}).get("success"):
            analysis_text = gemini_analysis.get("gemini_analysis", {}).get("analysis", "")
            
            # Update state with additional info from Gemini (if we can parse it)
            # For now, we'll include the raw analysis text
            updated_state["raw_description"] = analysis_text or updated_state.get("raw_description")
        
        # Combine results
        result = {
            'state': updated_state,
            'search_results': {
                'screenshots': search_result.get('screenshot_results', []),
                'gemini_analysis': gemini_analysis,
                'json_filepath': search_result.get('json_filepath')
            },
            'product_name': product_name,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }
        
        # Save combined results to JSON file
        base_dir = os.path.dirname(__file__)
        os.makedirs(base_dir, exist_ok=True)
        
        # Create safe filename
        safe_product_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_product_name = safe_product_name.replace(' ', '_')[:50]
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"product_search_result_{safe_product_name}_{timestamp_str}.json"
        json_filepath = os.path.join(base_dir, json_filename)
        
        # Save to JSON file
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        # Add JSON filepath to result
        result['json_filepath'] = json_filepath
        
        print(f"\n{'='*80}")
        print("SEARCH COMPLETE - FINAL RESULTS")
        print(f"{'='*80}")
        print(f"Product Name: {product_name}")
        print(f"Stage: {updated_state.get('stage')}")
        print(f"Missing fields: {updated_state.get('missing_fields')}")
        print(f"State - Product Name: {updated_state.get('product_name')}")
        print(f"State - Brand: {updated_state.get('brand')}")
        print(f"State - Price: {updated_state.get('price')}")
        print(f"State - Materials: {updated_state.get('materials')}")
        print(f"State - Manufacturing Location: {updated_state.get('manufacturing_location')}")
        print(f"State - Weight: {updated_state.get('weight_kg')}")
        
        if gemini_analysis and gemini_analysis.get("gemini_analysis", {}).get("success"):
            analysis_text = gemini_analysis.get("gemini_analysis", {}).get("analysis", "")
            print(f"\nGemini Analysis Preview (first 300 chars):")
            print(f"{analysis_text[:300]}...")
        
        print(f"\nResults saved to: {json_filepath}")
        if search_result.get('json_filepath'):
            print(f"Search JSON saved to: {search_result.get('json_filepath')}")
        
        print(f"\n{'='*80}")
        print("RETURNING RESPONSE TO FRONTEND")
        print(f"{'='*80}\n")
        
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


if __name__ == '__main__':
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)