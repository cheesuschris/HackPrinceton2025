const API_URL = 'http://localhost:5000/api/product';
const BACKEND_URL = 'http://localhost:5000';

// Storage keys
const STORAGE_KEY_PRODUCT_DATA = 'carbon0_product_data';
const STORAGE_KEY_ANALYSIS = 'carbon0_analysis';
const STORAGE_KEY_FINAL_OUTPUT = 'carbon0_final_output';

// Load and display stored data when popup opens
async function loadStoredData() {
  try {
    const result = await chrome.storage.local.get([
      STORAGE_KEY_PRODUCT_DATA,
      STORAGE_KEY_ANALYSIS,
      STORAGE_KEY_FINAL_OUTPUT
    ]);
    
    if (result[STORAGE_KEY_PRODUCT_DATA] && result[STORAGE_KEY_ANALYSIS]) {
      console.log('Loading stored data from chrome.storage');
      await displayStoredResults(result[STORAGE_KEY_PRODUCT_DATA], result[STORAGE_KEY_ANALYSIS], result[STORAGE_KEY_FINAL_OUTPUT]);
      return true;
    }
  } catch (error) {
    console.error('Error loading stored data:', error);
  }
  return false;
}

// Save data to chrome.storage
async function saveToStorage(productData, analysisData, finalOutputData) {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEY_PRODUCT_DATA]: productData,
      [STORAGE_KEY_ANALYSIS]: analysisData,
      [STORAGE_KEY_FINAL_OUTPUT]: finalOutputData
    });
    console.log('Data saved to chrome.storage');
  } catch (error) {
    console.error('Error saving to storage:', error);
  }
}

// Clear stored data
async function clearStoredData() {
  try {
    await chrome.storage.local.remove([
      STORAGE_KEY_PRODUCT_DATA,
      STORAGE_KEY_ANALYSIS,
      STORAGE_KEY_FINAL_OUTPUT
    ]);
    console.log('Stored data cleared');
  } catch (error) {
    console.error('Error clearing storage:', error);
  }
}

// Display stored results
async function displayStoredResults(productData, analysisData, finalOutputData) {
  const infoDiv = document.getElementById('productInfo');
  
  let html = '';
  html += `<div class="header">Product Description:</div>`
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
  if (productData.image) {
    html += `<div class="product-detail"><img src="${productData.image}" style="max-width: 100%; height: auto; margin-top: 10px; border-radius: 5px;" /></div>`;
  }

  // Display carbon score
  const carbonScore = finalOutputData?.carbon_score || analysisData?.C0Score;
  const displayScore = carbonScore !== undefined && carbonScore !== null ? carbonScore : 'N/A';
  html += `<div class="success" style="font-weight: bold; font-size: 16px; margin-top: 15px; padding: 20px; background: #4caf50; color: white; border-radius: 5px;">Calculated C0 Score: ${displayScore}<br>Check out these eco-friendly alternatives...</div>`;

  infoDiv.innerHTML = html;
  
  // Display alternatives
  await showAlternatives(productData, analysisData);
  
  // Add a clear button
  const clearBtn = document.createElement('button');
  clearBtn.textContent = 'Clear Results & Analyze New Product';
  clearBtn.style.marginTop = '10px';
  clearBtn.style.background = '#f44336';
  clearBtn.onclick = async () => {
    await clearStoredData();
    location.reload();
  };
  infoDiv.appendChild(clearBtn);
}

// Initialize: Try to load stored data when popup opens
document.addEventListener('DOMContentLoaded', async () => {
  const hasStoredData = await loadStoredData();
  if (!hasStoredData) {
    // Show default message if no stored data
    document.getElementById('productInfo').innerHTML = '<div style="font-weight: bold; font-size: 20px; text-align: center;">Click on the button below to analyze this product\'s carbon footprint!</div>';
  }
});

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
  // Clear any existing stored data when starting a new analysis
  await clearStoredData();
  
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
      availability: geminiData.availability || null,
      brand: geminiData.brand || null,
    };

    await handleProductData(productData, tab.url, true);
    
  } catch (error) {
    console.error('Screenshot extraction failed:', error);    
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
    availability: response.availability || null,
    brand: response.brand || null
  };

  let html = '';
  html += `<div class="header">Product Description:</div>`
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
  if (response.image) {
      html += `<div class="product-detail"><img src="${response.image}" style="max-width: 100%; height: auto; margin-top: 10px; border-radius: 5px;" /></div>`;
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
      
      // Debug: Log the full response
      console.log('API Response received:', result);
      
      // Try to fetch final_output from JSON file if filepath is provided
      let finalOutputData = null;
      if (result.final_output_file) {
        try {
          // Extract filename from filepath (e.g., "final_output_20251109_071249.json")
          const filename = result.final_output_file.split(/[/\\]/).pop();
          console.log('Fetching final_output from file:', filename);
          
          const fileResponse = await fetch(`${BACKEND_URL}/api/final-output/${filename}`);
          if (fileResponse.ok) {
            finalOutputData = await fileResponse.json();
            console.log('Loaded final_output from JSON file:', finalOutputData);
          } else {
            console.warn('Failed to fetch final_output file, using response data');
          }
        } catch (error) {
          console.warn('Error fetching final_output file:', error);
        }
      }
      
      // Extract data from final_output structure (prefer JSON file, then response, then direct fields)
      let carbonScore = result.C0Score;
      let links = [];
      
      // Priority 1: Use data from JSON file if available
      if (finalOutputData) {
        carbonScore = finalOutputData.carbon_score;
        links = finalOutputData.links || [];
        console.log('Using data from final_output JSON file');
      }
      // Priority 2: Use final_output structure from response
      else if (result.final_output) {
        carbonScore = result.final_output.carbon_score;
        links = result.final_output.links || [];
        console.log('Using final_output from API response');
      }
      // Priority 3: Fallback to direct fields
      else {
        console.log('Using direct fields from API response');
        for (let i = 1; i <= 5; i++) {
          const link = result[`link${i}`];
          if (link) {
            links.push({
              link: link,
              image: result[`link${i}Image`] || '',
              explanation: result[`link${i}Explanation`] || '',
              c0_score: result[`link${i}C0Score`] || null
            });
          }
        }
      }
      
      console.log('Carbon Score:', carbonScore);
      console.log('Links found:', links.length);
      
      const parseScore = (value) => {
        if (typeof value === 'number') return value;
        if (typeof value === 'string') {
          const parsed = parseFloat(value);
          return Number.isFinite(parsed) ? parsed : null;
        }
        return null;
      };

      const productScore = parseScore(carbonScore);
      const alternativeScores = links
        .map((link) => parseScore(link.c0_score))
        .filter((score) => score !== null);
      const bestScore = productScore !== null &&
        alternativeScores.length > 0 &&
        alternativeScores.every((score) => productScore < score);

      // Display C0Score - handle undefined/null properly
      const displayScore = carbonScore !== undefined && carbonScore !== null ? carbonScore : 'N/A';
      
      if (bestScore) {
        html += `<div class="success" style="font-weight: bold; font-size: 16px; margin-top: 15px; padding: 20px; background: #4caf50; color: white; border-radius: 5px;">Calculated C0 Score: ${displayScore}<br>Congrats, this was the best C0 score among similar products! Feel free to explore eco-friendly alternatives...</div>`;
      } else {
        html += `<div class="success" style="font-weight: bold; font-size: 16px; margin-top: 15px; padding: 20px; background: #4caf50; color: white; border-radius: 5px;">Calculated C0 Score: ${displayScore}<br>Check out these eco-friendly alternatives...</div>`;
      }

      infoDiv.innerHTML = html;
      
      // Convert links array to the format showAlternatives expects
      const alternativesData = {
        C0Score: carbonScore
      };
      links.forEach((link, index) => {
        const idx = index + 1;
        alternativesData[`link${idx}`] = link.link;
        alternativesData[`link${idx}Image`] = link.image;
        alternativesData[`link${idx}Explanation`] = link.explanation;
        alternativesData[`link${idx}C0Score`] = link.c0_score;
      });
      
      await showAlternatives(productData, alternativesData);
      
      // Save to storage for persistence
      await saveToStorage(productData, alternativesData, finalOutputData || result.final_output);
      
      // Add a clear button
      const clearBtn = document.createElement('button');
      clearBtn.textContent = 'Clear Results & Analyze New Product';
      clearBtn.style.marginTop = '10px';
      clearBtn.style.background = '#f44336';
      clearBtn.onclick = async () => {
        await clearStoredData();
        location.reload();
      };
      infoDiv.appendChild(clearBtn);
    } else {
      html += `<div class="error" style="font-weight: bold; font-size: 16px; margin-top: 15px; padding: 20px; background: #f44336; color: white; border-radius: 5px;">Failed to send data. Status: ${apiResponse.status}</div>`;
      infoDiv.innerHTML = html;
    }
  } catch (error) {
    html += `<div class="error" style="font-weight: bold; font-size: 16px; margin-top: 15px; padding: 20px; background: #f44336; color: white; border-radius: 5px;">Error: ${error.message}. Make sure the backend server is running.</div>`;
    infoDiv.innerHTML = html;
  }

  document.getElementById('readBtn').disabled = false;
  document.getElementById('readBtn').textContent = 'Analyze Product';
}

async function showAlternatives(originalProduct, analysis) {
  const infoDiv = document.getElementById('productInfo');
  let html = infoDiv.innerHTML;

  // Debug: Log what we're receiving
  console.log('showAlternatives - analysis object:', analysis);
  console.log('analysis.link1:', analysis.link1);
  console.log('analysis.link1Image:', analysis.link1Image);
  console.log('analysis.link1Explanation:', analysis.link1Explanation);

  const alternatives = [];
  for (let i = 1; i <= 5; i++) {
    const linkKey = `link${i}`;
    const imageKey = `link${i}Image`;
    const explanationKey = `link${i}Explanation`;
    const scoreKey = `link${i}C0Score`;
    
    const alt = {
      index: i,
      link: analysis[linkKey] || '',
      C0Score: analysis[scoreKey] || null,
      explanation: analysis[explanationKey] || '',
      image: analysis[imageKey] || ''
    };
    
    console.log(`Alternative ${i}:`, alt);
    
    // Only add if we have at least a link
    if (alt.link && alt.link.trim() !== '') {
      alternatives.push(alt);
    }
  }
  
  console.log(`Found ${alternatives.length} alternatives to display`);

  if (!alternatives.length) {
    infoDiv.innerHTML = `${html}<div class="error" style="font-weight: bold; font-size: 16px; margin-top: 15px; padding: 20px; background: #ffebee; color: #d32f2f; border-radius: 5px;">No eco-friendly alternatives were returned. Try another product or check the backend logs.</div>`;
    return;
  }

  html += `<div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #2e7d32;"><strong style="color: #2e7d32; font-size: 16px;">Eco-Friendly Alternatives:</strong></div>`;
  alternatives.forEach((alt) => {
    html += `
      <div style="margin-top: 15px; padding: 12px; background: #f1f8f4; border-radius: 6px; border-left: 4px solid #2e7d32;">
        <div style="font-weight: bold; color: #333; margin-bottom: 5px;">Suggestion ${alt.index}</div>
        <div style="color: #4caf50; font-size: 13px; margin: 3px 0;"><strong>Website:</strong> <a href="${alt.link}" target="_blank">${alt.link}</a></div>
        <div style="color: #4caf50; font-size: 13px; margin: 3px 0;"><strong>C0 Score:</strong> ${alt.C0Score ?? 'N/A'}</div>
        <div style="color: #4caf50; font-size: 13px; margin: 3px 0;"><strong>Suggestion Explanation:</strong> ${alt.explanation || 'Not provided'}</div>
        ${alt.image ? `<div style="color: #4caf50; font-size: 13px; margin: 3px 0;"><strong>Image:</strong> <img src="${alt.image}" alt="Alternative ${alt.index}" style="max-width: 100%; height: auto; margin-top: 10px; border-radius: 5px;" /></div>` : ''}
        <button class="add-to-cart-btn" data-index="${alt.index}" style="margin-top: 8px; background: #2e7d32; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 14px;">Add to Carbon0 Cart</button>
      </div>
    `;
  });
  
  infoDiv.innerHTML = html;
  
  alternatives.forEach((alt) => {
    const btn = infoDiv.querySelector(`.add-to-cart-btn[data-index="${alt.index}"]`);
    if (btn) {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        await addToCarbon0Cart(alt, originalProduct, e.target);
      });
    }
  });
}

async function addToCarbon0Cart(alternative, originalProduct, btn) {
  if (!btn) {
    return;
  }
  
  btn.disabled = true;
  btn.textContent = 'Adding...';
  
  try {
    const cartData = {
      alternative: {
        url: alternative.link,
        image: alternative.image,
        C0Score: alternative.C0Score,
        explanation: alternative.explanation
      },
      original: {
        name: originalProduct.name,
        price: originalProduct.price,
        url: originalProduct.url,
        image: originalProduct.image,
        platform: originalProduct.platform
      }
    };
    
    chrome.tabs.query({ url: `${BACKEND_URL}/cart*` }, (tabs) => {
      if (tabs.length > 0) {
        chrome.tabs.update(tabs[0].id, { 
          url: `${BACKEND_URL}/cart?product=${encodeURIComponent(JSON.stringify(cartData))}`,
          active: false 
        });
      } else {
        chrome.tabs.create({ 
          url: `${BACKEND_URL}/cart?product=${encodeURIComponent(JSON.stringify(cartData))}`,
          active: false 
        });
      }
    });
    
    btn.textContent = 'Added!';
    btn.style.background = '#4caf50';
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = 'Add to Carbon0 Cart';
      btn.style.background = '#2e7d32';
    }, 2000);
    
  } catch (error) {
    console.error('Cart error:', error);
    btn.textContent = `Error`;
    btn.style.background = '#f44336';
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = 'Add to Carbon0 Cart';
      btn.style.background = '#2e7d32';
    }, 2000);
  }
}
