const API_URL = 'http://localhost:5000/api/product';
const BACKEND_URL = 'http://localhost:5000';

async function getGeminiKey() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/config/gemini-key`);
    if (response.ok) {
      const data = await response.json();
      if (data.key) {
        return data.key;
      }
    }
  } catch (e) {
    console.error('Could not fetch Gemini key from backend:', e);
  }
  throw new Error('Gemini API key not configured. Please set GEMINI_API_KEY environment variable on the backend.');
}

document.getElementById('readBtn').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  document.getElementById('readBtn').disabled = true;
  document.getElementById('readBtn').textContent = 'Capturing screenshot...';
  document.getElementById('productInfo').innerHTML = '<div class="loading">Capturing page screenshot...</div>';

  try {
    const screenshot = await chrome.tabs.captureVisibleTab(null, { format: 'png' });
    
    document.getElementById('readBtn').textContent = 'Extracting with AI...';
    document.getElementById('productInfo').innerHTML = '<div class="loading">Extracting product information with Gemini AI...</div>';

    const geminiData = await extractWithGemini(screenshot);
    
    if (!geminiData || !geminiData.name) {
      document.getElementById('productInfo').innerHTML = '<div class="error">Failed to extract product information. Trying fallback method...</div>';
      
      chrome.tabs.sendMessage(tab.id, { action: 'getProductInfo' }, async (response) => {
        await handleProductData(response || {}, tab.url);
      });
      return;
    }

    const productData = {
      platform: detectPlatform(tab.url),
      url: tab.url,
      image: screenshot,
      name: geminiData.name || null,
      price: geminiData.price || null,
      rating: geminiData.rating || null,
      shipper: geminiData.shippingFrom || null,
      seller: geminiData.seller || null,
      reviews: geminiData.reviews || [],
      shippingFrom: geminiData.shippingFrom || null,
      fulfilledBy: null,
      availability: geminiData.availability || null,
      brand: geminiData.brand || null,
      co2Score: 50
    };

    await handleProductData(productData, tab.url, true);
    
  } catch (error) {
    console.error('Screenshot extraction failed:', error);
    document.getElementById('productInfo').innerHTML = '<div class="error">Screenshot failed. Trying fallback method...</div>';
    
    chrome.tabs.sendMessage(tab.id, { action: 'getProductInfo' }, async (response) => {
      await handleProductData(response || {}, tab.url);
    });
  }
});

async function extractWithGemini(imageDataUrl) {
  const API_KEY = await getGeminiKey();
  if (!API_KEY) {
    throw new Error('Gemini API key not configured');
  }
  const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`;
  
  const base64Image = imageDataUrl.split(',')[1];
  
  const prompt = `Extract product information from this e-commerce product page screenshot. Return ONLY a valid JSON object with the following structure (use null for missing fields):

{
  "name": "product name",
  "price": "price with currency symbol",
  "rating": "rating out of 5 stars (e.g., '4.5 out of 5 stars')",
  "seller": "seller name or 'Sold by' information",
  "shippingFrom": "shipping location/country",
  "reviews": ["review 1 text", "review 2 text", "review 3 text"],
  "brand": "brand name if visible",
  "availability": "availability status"
}

Focus on the main product information visible on the page. Extract up to 3 reviews if visible. Return ONLY the JSON, no other text.`;

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [{
          parts: [
            { text: prompt },
            {
              inline_data: {
                mime_type: 'image/png',
                data: base64Image
              }
            }
          ]
        }]
      })
    });

    if (!response.ok) {
      throw new Error(`Gemini API error: ${response.status}`);
    }

    const data = await response.json();
    const text = data.candidates[0].content.parts[0].text;
    
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
    
    return JSON.parse(text);
  } catch (error) {
    console.error('Gemini extraction failed:', error);
    return null;
  }
}

function detectPlatform(url) {
  if (url.includes('amazon.com')) return 'Amazon';
  if (url.includes('walmart.com')) return 'Walmart';
  if (url.includes('etsy.com')) return 'Etsy';
  if (url.includes('bestbuy.com')) return 'Best Buy';
  if (url.includes('target.com')) return 'Target';
  if (url.includes('ebay.com')) return 'eBay';
  return 'Unknown';
}

async function handleProductData(response, url, fromGemini = false) {
  const infoDiv = document.getElementById('productInfo');
  
  if (!response || (!response.title && !response.name)) {
    infoDiv.innerHTML = '<div class="error">Could not extract product information. Make sure you are on a product page.</div>';
    document.getElementById('readBtn').disabled = false;
    document.getElementById('readBtn').textContent = 'Analyze Product';
    return;
  }

  const productData = {
    platform: response.platform || detectPlatform(url),
    url: url,
    image: response.image || null,
    name: response.title || response.name || null,
    price: response.price || null,
    rating: response.rating || null,
    shipper: response.shipsFrom || response.shippingFrom || null,
    seller: response.soldBy || response.seller || null,
    reviews: response.reviews || [],
    shippingFrom: response.shipsFrom || response.shippingFrom || null,
    fulfilledBy: response.fulfilledBy || null,
    availability: response.availability || null,
    brand: response.brand || null,
    co2Score: 50
  };

  let html = '';
  html += `<div class="product-title">${productData.name || 'Unknown Product'}</div>`;
  html += `<div class="product-detail"><strong>Platform:</strong> ${productData.platform || 'Unknown'}</div>`;
  
  if (productData.price) {
    html += `<div class="product-detail"><strong>Price:</strong> ${productData.price}</div>`;
  }
  if (productData.rating) {
    html += `<div class="product-detail"><strong>Rating:</strong> ${productData.rating}</div>`;
  }
  if (productData.seller) {
    html += `<div class="product-detail"><strong>Sold By:</strong> ${productData.seller}</div>`;
  }
  if (productData.shippingFrom) {
    html += `<div class="product-detail"><strong>Ships From:</strong> ${productData.shippingFrom}</div>`;
  }

  infoDiv.innerHTML = html;

  document.getElementById('readBtn').textContent = 'Analyzing carbon footprint...';
  
  try {
    const apiResponse = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(productData)
    });

    if (apiResponse.ok) {
      const result = await apiResponse.json();
      html += `<div class="success" style="margin-top: 15px; padding: 10px; background: #4caf50; color: white; border-radius: 5px;">✓ Product analyzed! Finding eco-friendly alternatives...</div>`;
      infoDiv.innerHTML = html;
      
      setTimeout(async () => {
        await showAlternatives(productData);
      }, 1000);
    } else {
      html += `<div class="error" style="margin-top: 15px; padding: 10px; background: #f44336; color: white; border-radius: 5px;">✗ Failed to send data. Status: ${apiResponse.status}</div>`;
      infoDiv.innerHTML = html;
    }
  } catch (error) {
    html += `<div class="error" style="margin-top: 15px; padding: 10px; background: #f44336; color: white; border-radius: 5px;">✗ Error: ${error.message}. Make sure the backend server is running.</div>`;
    infoDiv.innerHTML = html;
  }

  document.getElementById('readBtn').disabled = false;
  document.getElementById('readBtn').textContent = 'Analyze Product';
}

async function showAlternatives(originalProduct) {
  const infoDiv = document.getElementById('productInfo');
  
  const originalCO2 = originalProduct.co2Score || 50;
  
  const alternatives = [
    {
      name: 'Eco-Friendly Alternative 1',
      price: '$24.99',
      co2Score: 12,
      co2Saved: originalCO2 - 12,
      merchant: 'EcoStore',
      url: 'https://example.com/product1',
      image: originalProduct.image
    },
    {
      name: 'Sustainable Option 2',
      price: '$29.99',
      co2Score: 18,
      co2Saved: originalCO2 - 18,
      merchant: 'GreenMarket',
      url: 'https://example.com/product2',
      image: originalProduct.image
    },
    {
      name: 'Carbon-Neutral Choice 3',
      price: '$27.50',
      co2Score: 8,
      co2Saved: originalCO2 - 8,
      merchant: 'EarthFriendly',
      url: 'https://example.com/product3',
      image: originalProduct.image
    }
  ];

  let html = infoDiv.innerHTML;
  html += `<div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #2e7d32;"><strong style="color: #2e7d32; font-size: 16px;">🌱 Eco-Friendly Alternatives:</strong></div>`;
  
  alternatives.forEach((alt, index) => {
    html += `
      <div style="margin-top: 15px; padding: 12px; background: #f1f8f4; border-radius: 6px; border-left: 4px solid #2e7d32;">
        <div style="font-weight: bold; color: #333; margin-bottom: 5px;">${alt.name}</div>
        <div style="color: #666; font-size: 13px; margin: 3px 0;"><strong>Price:</strong> ${alt.price}</div>
        <div style="color: #2e7d32; font-size: 13px; margin: 3px 0; font-weight: bold;"><strong>CO₂ Score:</strong> ${alt.co2Score} kg</div>
        <div style="color: #4caf50; font-size: 13px; margin: 3px 0; font-weight: bold;"><strong>CO₂ Saved:</strong> ${alt.co2Saved} kg</div>
        <div style="color: #666; font-size: 13px; margin: 3px 0;"><strong>Merchant:</strong> ${alt.merchant}</div>
        <button class="add-to-cart-btn" data-index="${index}" style="margin-top: 8px; background: #2e7d32; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 14px;">Add to Carbon0 Cart</button>
      </div>
    `;
  });
  
  infoDiv.innerHTML = html;
  
  document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const index = parseInt(e.target.getAttribute('data-index'));
      await addToCarbon0Cart(alternatives[index], originalProduct);
    });
  });
  
  // Don't auto-open cart - let user decide when to view it
  // User can click "Add to Carbon0 Cart" to open it
}

async function addToCarbon0Cart(alternative, originalProduct) {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = 'Adding...';
  
  try {
    const cartData = {
      alternative: {
        name: alternative.name,
        price: alternative.price,
        url: alternative.url,
        image: alternative.image || originalProduct.image,
        merchant: alternative.merchant,
        co2Score: alternative.co2Score,
        co2Saved: alternative.co2Saved
      },
      original: {
        name: originalProduct.name,
        price: originalProduct.price,
        url: originalProduct.url,
        image: originalProduct.image,
        platform: originalProduct.platform
      }
    };
    
    // Always use URL parameter method - more reliable
    chrome.tabs.query({ url: `${BACKEND_URL}/cart*` }, (tabs) => {
      if (tabs.length > 0) {
        // Cart tab exists - update URL with product data
        chrome.tabs.update(tabs[0].id, { 
          url: `${BACKEND_URL}/cart?product=${encodeURIComponent(JSON.stringify(cartData))}`,
          active: false  // Keep popup visible
        });
      } else {
        // No cart tab - create one in background
        chrome.tabs.create({ 
          url: `${BACKEND_URL}/cart?product=${encodeURIComponent(JSON.stringify(cartData))}`,
          active: false  // Open in background so popup stays visible
        });
      }
    });
    
    btn.textContent = '✓ Added!';
    btn.style.background = '#4caf50';
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = 'Add to Carbon0 Cart';
      btn.style.background = '#2e7d32';
    }, 2000);
    
  } catch (error) {
    console.error('Cart error:', error);
    btn.textContent = `✗ Error`;
    btn.style.background = '#f44336';
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = 'Add to Carbon0 Cart';
      btn.style.background = '#2e7d32';
    }, 2000);
  }
}
