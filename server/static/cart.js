const STORAGE_KEY = 'carbon0_cart';

let cartData = [];

function loadCart() {
  const stored = localStorage.getItem(STORAGE_KEY);
  console.log('Loading cart from localStorage:', stored);
  if (stored) {
    try {
      cartData = JSON.parse(stored);
      console.log('Loaded cart data:', cartData);
    } catch (e) {
      console.error('Failed to parse cart data:', e);
      cartData = [];
    }
  } else {
    cartData = [];
  }
  renderCart();
}

function saveCart() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cartData));
  renderCart();
}

function addToCart(alternative, original) {
  console.log('addToCart called with:', { alternative, original });
  
  if (!alternative || !original) {
    console.error('Missing alternative or original data');
    return;
  }
  
  const existingIndex = cartData.findIndex(item => 
    item.original.url === original.url && 
    item.alternative.url === alternative.url
  );
  
  if (existingIndex >= 0) {
    console.log('Product already in cart');
    return;
  }
  
  cartData.push({
    id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    alternative: alternative,
    original: original,
    addedAt: new Date().toISOString()
  });
  
  console.log('Cart data after add:', cartData);
  saveCart();
}

function removeFromCart(id) {
  cartData = cartData.filter(item => item.id !== id);
  saveCart();
}

function calculateStats() {
  const totalAlternatives = cartData.length;
  const totalCO2Saved = cartData.reduce((sum, item) => sum + (item.alternative.co2Saved || 0), 0);
  const uniqueProducts = new Set(cartData.map(item => item.original.url)).size;
  
  document.getElementById('total-alternatives').textContent = totalAlternatives;
  document.getElementById('total-co2-saved').textContent = totalCO2Saved.toFixed(1) + ' kg';
  document.getElementById('total-products').textContent = uniqueProducts;
}

function renderCart() {
  const container = document.getElementById('cart-container');
  
  if (cartData.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <h2>Your cart is empty</h2>
        <p>Start browsing products and add eco-friendly alternatives to see your CO₂ savings!</p>
      </div>
    `;
    calculateStats();
    return;
  }
  
  const groupedByOriginal = {};
  cartData.forEach(item => {
    const key = item.original.url || item.original.name;
    if (!groupedByOriginal[key]) {
      groupedByOriginal[key] = {
        original: item.original,
        alternatives: []
      };
    }
    groupedByOriginal[key].alternatives.push(item);
  });
  
  let html = '';
  
  Object.values(groupedByOriginal).forEach(group => {
    html += `
      <div class="product-group">
        <div class="original-product">
          <div class="label">Original Product</div>
          <div class="product-name">${group.original.name || 'Product'}</div>
          <div class="product-details">
            ${group.original.price ? `<div class="detail-item"><strong>Price:</strong> ${group.original.price}</div>` : ''}
            ${group.original.platform ? `<div class="detail-item"><strong>Platform:</strong> ${group.original.platform}</div>` : ''}
          </div>
        </div>
        <div class="alternatives-list">
    `;
    
    group.alternatives.forEach(item => {
      const alt = item.alternative;
      html += `
        <div class="alternative-item">
          ${alt.image ? `<img src="${alt.image}" alt="${alt.name}" class="product-image" onerror="this.style.display='none'">` : ''}
          <div class="product-info">
            <div class="product-name">${alt.name}</div>
            <div class="product-details">
              ${alt.price ? `<div class="detail-item"><strong>Price:</strong> ${alt.price}</div>` : ''}
              ${alt.merchant ? `<div class="detail-item"><strong>Merchant:</strong> ${alt.merchant}</div>` : ''}
              ${alt.url ? `<div class="detail-item"><strong>URL:</strong> <a href="${alt.url}" target="_blank">View Product</a></div>` : ''}
            </div>
            <div style="margin-top: 8px;">
              ${alt.co2Score !== undefined ? `<span class="co2-badge">CO₂: ${alt.co2Score} kg</span>` : ''}
              ${alt.co2Saved !== undefined ? `<span class="co2-saved" style="margin-left: 8px;">Saved: ${alt.co2Saved} kg</span>` : ''}
            </div>
          </div>
          <button class="remove-btn" onclick="removeFromCart('${item.id}')">Remove</button>
        </div>
      `;
    });
    
    html += `
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
  calculateStats();
}

window.addEventListener('message', (event) => {
  console.log('Cart page received message:', event.data);
  if (event.data && event.data.action === 'addToCart') {
    console.log('Adding to cart via message:', event.data.data);
    addToCart(event.data.data.alternative, event.data.data.original);
  }
});

if (typeof window.removeFromCart === 'undefined') {
  window.removeFromCart = removeFromCart;
}

function handleUrlProduct() {
  const urlParams = new URLSearchParams(window.location.search);
  const productParam = urlParams.get('product');

  if (productParam) {
    try {
      const productData = JSON.parse(decodeURIComponent(productParam));
      console.log('Adding product from URL:', productData);
      if (productData.alternative && productData.original) {
        addToCart(productData.alternative, productData.original);
        window.history.replaceState({}, '', '/cart');
        return true;
      } else {
        console.error('Invalid product data structure:', productData);
      }
    } catch (e) {
      console.error('Failed to parse product data:', e);
    }
  }
  return false;
}

// Load existing cart first
loadCart();

// Then check for new product in URL
if (handleUrlProduct()) {
  console.log('Product added from URL parameter');
}

// Also listen for URL changes (when tab is updated)
let lastUrl = window.location.href;
setInterval(() => {
  if (window.location.href !== lastUrl) {
    lastUrl = window.location.href;
    if (handleUrlProduct()) {
      console.log('Product added from URL parameter (after navigation)');
    }
  }
}, 500);

