const KNOT_API_BASE = 'https://api.knotapi.com';

async function createKnotSession(backendUrl) {
  try {
    const response = await fetch(`${backendUrl}/api/knot/session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to create Knot session');
    }
    
    const data = await response.json();
    return data.session_id;
  } catch (error) {
    console.error('Knot session creation failed:', error);
    return null;
  }
}

async function addToKnotCart(productData, sessionId, backendUrl) {
  try {
    const response = await fetch(`${backendUrl}/api/knot/cart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        product: {
          name: productData.name,
          price: productData.price,
          url: productData.url,
          image: productData.image,
          merchant: productData.merchant || 'Unknown'
        }
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to add to Knot cart');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Add to cart failed:', error);
    return null;
  }
}

function initializeKnotSDK(sessionId) {
  return new Promise((resolve, reject) => {
    if (window.Knot) {
      window.Knot.init({
        sessionId: sessionId,
        onSuccess: (data) => {
          console.log('Knot success:', data);
          resolve(data);
        },
        onError: (error) => {
          console.error('Knot error:', error);
          reject(error);
        },
        onExit: () => {
          console.log('Knot exited');
        }
      });
    } else {
      reject(new Error('Knot SDK not loaded'));
    }
  });
}

