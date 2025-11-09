// Content script for extracting product information from e-commerce pages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getProductInfo') {
    const productInfo = extractProductInfo();
    sendResponse(productInfo);
  }
  return true;
});

function extractProductInfo() {
  const url = window.location.href;
  const platform = detectPlatform(url);
  
  // Use platform-specific extraction
  if (platform === 'Amazon') {
    return extractAmazon();
  } else if (platform === 'Walmart') {
    return extractWalmart();
  } else if (platform === 'Etsy') {
    return extractEtsy();
  } else if (platform === 'Best Buy') {
    return extractBestBuy();
  } else if (platform === 'Target') {
    return extractTarget();
  } else if (platform === 'eBay') {
    return extractEbay();
  }
  
  return { platform, url };
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

function extractAmazon() {
  return {
    platform: 'Amazon',
    title: document.querySelector('#productTitle')?.textContent?.trim() || 
           document.querySelector('h1.a-size-large')?.textContent?.trim() || '',
    price: document.querySelector('.a-price-whole')?.textContent?.trim() || 
           document.querySelector('#priceblock_ourprice')?.textContent?.trim() || '',
    rating: document.querySelector('#acrPopover')?.getAttribute('title') || 
            document.querySelector('.a-icon-alt')?.textContent?.trim() || '',
    seller: document.querySelector('#sellerProfileTriggerId')?.textContent?.trim() || 
            document.querySelector('#merchant-info a')?.textContent?.trim() || '',
    shippingFrom: document.querySelector('#glow-ingress-line2')?.textContent?.trim() || '',
    brand: document.querySelector('#bylineInfo')?.textContent?.trim() || 
           document.querySelector('#brand')?.textContent?.trim() || '',
    availability: document.querySelector('#availability span')?.textContent?.trim() || '',
    reviews: Array.from(document.querySelectorAll('.review-text-content')).slice(0, 3).map(r => r.textContent.trim())
  };
}

function extractWalmart() {
  return {
    platform: 'Walmart',
    title: document.querySelector('h1[itemprop="name"]')?.textContent?.trim() || 
           document.querySelector('h1.prod-ProductTitle')?.textContent?.trim() || '',
    price: document.querySelector('[itemprop="price"]')?.textContent?.trim() || 
           document.querySelector('.price-current')?.textContent?.trim() || '',
    rating: document.querySelector('[itemprop="ratingValue"]')?.textContent?.trim() || '',
    seller: 'Walmart',
    shippingFrom: '',
    brand: document.querySelector('[itemprop="brand"]')?.textContent?.trim() || '',
    availability: document.querySelector('.prod-fulfillment-messaging-text')?.textContent?.trim() || '',
    reviews: []
  };
}

function extractEtsy() {
  return {
    platform: 'Etsy',
    title: document.querySelector('h1[data-buy-box-listing-title]')?.textContent?.trim() || 
           document.querySelector('h1.listing-page-title')?.textContent?.trim() || '',
    price: document.querySelector('.currency-value')?.textContent?.trim() || '',
    rating: document.querySelector('.shop2-review-attribution')?.textContent?.trim() || '',
    seller: document.querySelector('.shop-name')?.textContent?.trim() || '',
    shippingFrom: document.querySelector('.shop-location')?.textContent?.trim() || '',
    brand: '',
    availability: '',
    reviews: []
  };
}

function extractBestBuy() {
  return {
    platform: 'Best Buy',
    title: document.querySelector('.sku-title h1')?.textContent?.trim() || 
           document.querySelector('[data-testid="product-title"]')?.textContent?.trim() || '',
    price: document.querySelector('.priceView-customer-price span')?.textContent?.trim() || '',
    rating: document.querySelector('.ugc-review-summary')?.textContent?.trim() || '',
    seller: 'Best Buy',
    shippingFrom: '',
    brand: document.querySelector('.product-data-brand')?.textContent?.trim() || '',
    availability: document.querySelector('.fulfillment-fulfillment-summary')?.textContent?.trim() || '',
    reviews: []
  };
}

function extractTarget() {
  return {
    platform: 'Target',
    title: document.querySelector('h1[data-test="product-title"]')?.textContent?.trim() || 
           document.querySelector('h1.styles__ProductTitle')?.textContent?.trim() || '',
    price: document.querySelector('[data-test="product-price"]')?.textContent?.trim() || '',
    rating: document.querySelector('[data-test="rating"]')?.textContent?.trim() || '',
    seller: 'Target',
    shippingFrom: '',
    brand: document.querySelector('[data-test="item-details-specifications"]')?.textContent?.trim() || '',
    availability: '',
    reviews: []
  };
}

function extractEbay() {
  return {
    platform: 'eBay',
    title: document.querySelector('#x-item-title-label')?.textContent?.trim() || 
           document.querySelector('h1.it-ttl')?.textContent?.trim() || '',
    price: document.querySelector('#prcIsum')?.textContent?.trim() || 
           document.querySelector('.notranslate')?.textContent?.trim() || '',
    rating: '',
    seller: document.querySelector('.mbg-nw')?.textContent?.trim() || '',
    shippingFrom: document.querySelector('.u-flL.condText')?.textContent?.trim() || '',
    brand: '',
    availability: '',
    reviews: []
  };
}
