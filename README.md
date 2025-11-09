## Carbon0
By Chris Wu, Safa Obuz, Ariji Chakma, Kaijie Lai

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Flask](https://img.shields.io/badge/Flask-3.1.2-000000?style=for-the-badge&logo=flask&logoColor=white)
![Chrome Extension](https://img.shields.io/badge/Chrome%20Extension-Manifest%20V3-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-1.5%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)

### Project Explanation
Carbon0 is a browser extension that analyzes product carbon footprints and finds eco-friendly alternatives. The extension extracts product information from major e-commerce platforms and sends it to a Flask backend for carbon footprint analysis.

### Tech Stack
- **Frontend**: Chrome Extension (Manifest V3)
- **Backend**: Flask (Python)
- **Supported Platforms**: Amazon, Walmart, Etsy, Best Buy, Target, eBay

### Features
- Multi-platform product information extraction
- Automatic carbon footprint analysis
- Eco-friendly alternative suggestions
- Review extraction (up to 3 examples)
- Shipping and seller information tracking

### To Run:

#### Backend Setup:
```bash
cd server
pip install -r requirements.txt
python app.py
```

The backend will run on `http://localhost:5000`

#### Extension Setup:
1. Open Chrome/Edge and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked" and select the extension folder
4. Navigate to any supported product page:
   - Amazon: `https://www.amazon.com/...`
   - Walmart: `https://www.walmart.com/...`
   - Etsy: `https://www.etsy.com/...`
   - Best Buy: `https://www.bestbuy.com/...`
   - Target: `https://www.target.com/...`
   - eBay: `https://www.ebay.com/...`
5. Click the Carbon0 extension icon in the toolbar
6. Click "Analyze Product" to extract and send product data

### API Endpoint

**POST** `/api/product`

Receives product data in JSON format:
```json
{
  "platform": "Amazon",
  "url": "https://www.amazon.com/...",
  "image": "https://...",
  "name": "Product Name",
  "price": "$29.99",
  "rating": "4.5 out of 5 stars",
  "shipper": null,
  "seller": "Amazon.com",
  "reviews": ["Review 1", "Review 2", "Review 3"],
  "shippingFrom": "United States",
  "fulfilledBy": null,
  "availability": "In Stock",
  "brand": "Brand Name"
}
```

### Video Demonstration
[YouTube](https://www.youtube.com/watch?v=FiQ_lsqBNIk)
