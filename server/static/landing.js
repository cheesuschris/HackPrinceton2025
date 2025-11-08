const urlParams = new URLSearchParams(window.location.search);
const sessionId = urlParams.get('sessionId');
const productJson = urlParams.get('product');

let product = null;
if (productJson) {
  try {
    product = JSON.parse(decodeURIComponent(productJson));
  } catch (e) {
    console.error('Failed to parse product:', e);
  }
}

const cartContainer = document.getElementById('cart-container');
const cartStatus = document.getElementById('cart-status');

function updateStatus(message, isError = false) {
  cartStatus.innerHTML = `<strong>${message}</strong>`;
  cartStatus.style.background = isError ? '#ffebee' : '#f1f8f4';
  cartStatus.style.borderLeftColor = isError ? '#c62828' : '#2e7d32';
}

function displayProduct(product) {
  cartContainer.innerHTML = `
    <div class="product-item">
      ${product.image ? `<img src="${product.image}" alt="${product.name}" class="product-image" onerror="this.style.display='none'">` : ''}
      <div class="product-info">
        <div class="product-name">${product.name || 'Product'}</div>
        ${product.merchant ? `<div class="product-details"><strong>Merchant:</strong> ${product.merchant}</div>` : ''}
        ${product.url ? `<div class="product-details"><strong>URL:</strong> <a href="${product.url}" target="_blank">View Product</a></div>` : ''}
        ${product.price ? `<div class="product-price">${product.price}</div>` : ''}
      </div>
    </div>
  `;
}

if (!sessionId) {
  updateStatus('Error: No session ID provided', true);
  cartContainer.innerHTML = '<div class="error">Please add products from the Carbon0 extension.</div>';
} else if (!product) {
  updateStatus('Error: No product data provided', true);
  cartContainer.innerHTML = '<div class="error">Please add products from the Carbon0 extension.</div>';
} else {
  updateStatus('Initializing Knot cart...');
  displayProduct(product);
  
  if (typeof window.Knot === 'undefined') {
    setTimeout(() => {
      if (typeof window.Knot === 'undefined') {
        updateStatus('Error: Knot SDK failed to load', true);
        cartContainer.innerHTML += '<div class="error">Knot SDK could not be loaded. Please refresh the page.</div>';
      } else {
        initializeKnot();
      }
    }, 2000);
  } else {
    initializeKnot();
  }
}

function initializeKnot() {
  try {
    updateStatus('Adding product to Knot cart...');
    
    window.Knot.init({
      sessionId: sessionId,
      onSuccess: (data) => {
        console.log('Knot initialized:', data);
        updateStatus('Cart ready! Product added successfully.');
        
        if (window.Knot.addToCart) {
          window.Knot.addToCart({
            name: product.name,
            price: product.price,
            url: product.url,
            image: product.image,
            merchant: product.merchant
          });
        }
      },
      onError: (error) => {
        console.error('Knot error:', error);
        updateStatus('Error initializing Knot cart', true);
        cartContainer.innerHTML += `<div class="error">Knot API error: ${error.message || 'Unknown error'}</div>`;
      },
      onExit: () => {
        console.log('Knot exited');
      }
    });
  } catch (error) {
    console.error('Error initializing Knot:', error);
    updateStatus('Error: ' + error.message, true);
  }
}

