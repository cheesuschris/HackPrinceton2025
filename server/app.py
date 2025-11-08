from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_cors import CORS
import os
import requests
import base64
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

KNOT_CLIENT_ID = os.getenv('KNOT_CLIENT_ID', '')
KNOT_SECRET = os.getenv('KNOT_SECRET', '')
KNOT_API_BASE = os.getenv('KNOT_API_BASE', 'https://development.knotapi.com')

@app.route('/')
def home():
    """Home route"""
    return jsonify({
        'message': 'Welcome to the Carbon0 Flask server',
        'status': 'running'
    })

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
    """Landing page for Knot cart"""
    return send_from_directory('templates', 'landing.html')

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

@app.route('/api/knot/session', methods=['POST'])
def create_knot_session():
    """Create a Knot API session"""
    try:
        if not KNOT_CLIENT_ID or not KNOT_SECRET:
            print("ERROR: Knot API credentials not configured!")
            print(f"KNOT_CLIENT_ID: {'SET' if KNOT_CLIENT_ID else 'NOT SET'}")
            print(f"KNOT_SECRET: {'SET' if KNOT_SECRET else 'NOT SET'}")
            return jsonify({
                'error': 'Knot API credentials not configured. Please set KNOT_CLIENT_ID and KNOT_SECRET environment variables.',
                'status': 'error',
                'details': 'Set credentials with: export KNOT_CLIENT_ID="your_id" && export KNOT_SECRET="your_secret"'
            }), 500
        
        data = request.get_json(silent=True) or {}
        external_user_id = data.get('external_user_id', f'carbon0_user_{uuid.uuid4().hex[:12]}')
        
        print(f"Creating Knot session with client_id: {KNOT_CLIENT_ID[:10]}...")
        print(f"External user ID: {external_user_id}")
        
        auth_string = f"{KNOT_CLIENT_ID}:{KNOT_SECRET}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'type': 'link',
            'external_user_id': external_user_id
        }
        
        endpoint = f'{KNOT_API_BASE}/session/create'
        print(f"API endpoint: {endpoint}")
        print(f"Payload: {payload}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Knot API response status: {response.status_code}")
        print(f"Knot API response: {response.text}")
        
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data.get('session') or session_data.get('session_id')
            print(f"Session created: {session_id}")
            return jsonify({
                'session_id': session_id,
                'status': 'success'
            }), 200
        else:
            error_msg = f'Knot API error: {response.status_code}'
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
            except:
                error_msg += f" - {response.text}"
            
            return jsonify({
                'error': error_msg,
                'status': 'error'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {str(e)}")
        return jsonify({
            'error': f'Network error connecting to Knot API: {str(e)}',
            'status': 'error'
        }), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/knot/cart', methods=['POST'])
def add_to_knot_cart():
    """Add product to Knot cart"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        product = data.get('product')
        
        if not session_id or not product:
            return jsonify({
                'error': 'Missing session_id or product data',
                'status': 'error'
            }), 400
        
        if not KNOT_CLIENT_ID or not KNOT_SECRET:
            return jsonify({
                'error': 'Knot API credentials not configured',
                'status': 'error'
            }), 500
        
        cart_data = {
            'session_id': session_id,
            'items': [{
                'name': product.get('name'),
                'price': product.get('price'),
                'url': product.get('url'),
                'image': product.get('image'),
                'merchant': product.get('merchant')
            }]
        }
        
        print(f"Adding to Knot cart: {product.get('name')}")
        print(f"Cart data: {cart_data}")
        
        auth_string = f"{KNOT_CLIENT_ID}:{KNOT_SECRET}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }
        
        endpoints_to_try = [
            f'{KNOT_API_BASE}/v2/cart/sync',
            f'{KNOT_API_BASE}/cart/add',
            f'{KNOT_API_BASE}/v2/cart/add',
            f'{KNOT_API_BASE}/shopping/cart/sync',
        ]
        
        response = None
        last_error = None
        
        for endpoint in endpoints_to_try:
            print(f"Trying cart API endpoint: {endpoint}")
            try:
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=cart_data,
                    timeout=10
                )
                print(f"Response status: {response.status_code}")
                if response.status_code != 404:
                    break
            except Exception as e:
                last_error = e
                continue
        
        if not response:
            raise Exception(f"All endpoints failed. Last error: {last_error}")
        
        print(f"Knot cart API response status: {response.status_code}")
        print(f"Knot cart API response: {response.text}")
        
        if response.status_code == 200:
            return jsonify({
                'message': 'Product added to Knot cart successfully',
                'status': 'success'
            }), 200
        else:
            error_msg = f'Knot API error: {response.status_code}'
            error_details = {}
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
                error_details = error_data
            except:
                error_msg += f" - {response.text}"
                error_details = {'raw_response': response.text}
            
            print(f"Cart error details: {error_details}")
            
            return jsonify({
                'error': error_msg,
                'error_details': error_details,
                'status': 'error'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {str(e)}")
        return jsonify({
            'error': f'Network error connecting to Knot API: {str(e)}',
            'status': 'error'
        }), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
