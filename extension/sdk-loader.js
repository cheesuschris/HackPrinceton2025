let sdkLoaded = false;

window.addEventListener('load', () => {
  console.log('=== Carbon0 Extension Debug ===');
  console.log('Popup loaded, checking for Knot SDK...');
  console.log('window.Knot type:', typeof window.Knot);
  console.log('window.Knot value:', window.Knot);
  
  if (typeof window.Knot !== 'undefined') {
    console.log('✓ Knot SDK loaded successfully');
    console.log('Knot SDK methods:', Object.keys(window.Knot));
    sdkLoaded = true;
  } else {
    console.warn('✗ Knot SDK not yet loaded');
    setTimeout(() => {
      if (typeof window.Knot !== 'undefined') {
        console.log('✓ Knot SDK loaded after delay');
        sdkLoaded = true;
      } else {
        console.error('✗ Knot SDK still not loaded after delay');
      }
    }, 2000);
  }
});

function checkSDK() {
  console.log('=== SDK Check ===');
  console.log('window.Knot exists:', typeof window.Knot !== 'undefined');
  if (typeof window.Knot !== 'undefined') {
    console.log('Knot object:', window.Knot);
    console.log('Knot methods:', Object.keys(window.Knot));
  }
  return typeof window.Knot !== 'undefined';
}

window.checkSDK = checkSDK;

console.warn('Knot SDK cannot be loaded in Chrome extensions due to CSP restrictions.');
console.warn('Cart functionality will use backend API directly instead.');

