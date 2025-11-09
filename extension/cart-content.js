// Content script for the cart page
// Handles product data passed via URL parameters

(function() {
  // Extract product data from URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const productParam = urlParams.get('product');
  
  if (productParam) {
    try {
      const productData = JSON.parse(decodeURIComponent(productParam));
      console.log('Product data received:', productData);
      
      // Dispatch custom event with product data
      window.dispatchEvent(new CustomEvent('carbon0-product-added', {
        detail: productData
      }));
    } catch (error) {
      console.error('Error parsing product data:', error);
    }
  }
})();
