// Offline functionality for Nanay's Kakanin
class OfflineManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.init();
  }

  init() {
    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/kakanin/js/sw.js')
        .then(registration => {
          console.log('SW registered: ', registration);
        })
        .catch(registrationError => {
          console.log('SW registration failed: ', registrationError);
        });
    }

    // Listen for online/offline events
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());

    // Initial status check
    this.updateConnectionStatus();
  }

  handleOnline() {
    this.isOnline = true;
    this.updateConnectionStatus();
    this.syncOfflineData();
    this.showNotification('You are back online!', 'success');
  }

  handleOffline() {
    this.isOnline = false;
    this.updateConnectionStatus();
    this.showNotification('You are offline. Limited functionality available.', 'warning');
  }

  updateConnectionStatus() {
    const statusIndicator = document.getElementById('connection-status');
    if (statusIndicator) {
      if (this.isOnline) {
        statusIndicator.className = 'connection-status online';
        statusIndicator.innerHTML = '<i class="fas fa-wifi"></i> Online';
      } else {
        statusIndicator.className = 'connection-status offline';
        statusIndicator.innerHTML = '<i class="fas fa-wifi-slash"></i> Offline';
      }
    }

    // Show/hide offline elements
    const offlineElements = document.querySelectorAll('.offline-only');
    const onlineElements = document.querySelectorAll('.online-only');
    
    offlineElements.forEach(el => {
      el.style.display = this.isOnline ? 'none' : 'block';
    });
    
    onlineElements.forEach(el => {
      el.style.display = this.isOnline ? 'block' : 'none';
    });
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <span>${message}</span>
        <button onclick="this.parentElement.parentElement.remove()" class="notification-close">×</button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }

  syncOfflineData() {
    // Sync any offline orders or data
    const offlineOrders = this.getOfflineOrders();
    if (offlineOrders.length > 0) {
      this.submitOfflineOrders(offlineOrders);
    }
  }

  getOfflineOrders() {
    const orders = localStorage.getItem('offline_orders');
    return orders ? JSON.parse(orders) : [];
  }

  saveOfflineOrder(orderData) {
    const orders = this.getOfflineOrders();
    orders.push({
      ...orderData,
      timestamp: Date.now(),
      offline: true
    });
    localStorage.setItem('offline_orders', JSON.stringify(orders));
  }

  submitOfflineOrders(orders) {
    orders.forEach(order => {
      fetch('/api/orders/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify(order)
      })
      .then(response => response.json())
      .then(data => {
        console.log('Offline order synced:', data);
      })
      .catch(error => {
        console.error('Failed to sync offline order:', error);
      });
    });
    
    // Clear offline orders after sync
    localStorage.removeItem('offline_orders');
  }

  getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  }
}

// Skeleton screen functions
function showSkeleton(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div class="skeleton-container">
      <div class="skeleton-header">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-subtitle"></div>
      </div>
      <div class="skeleton-grid">
        ${Array(6).fill().map(() => `
          <div class="skeleton-card">
            <div class="skeleton-image"></div>
            <div class="skeleton-content">
              <div class="skeleton-line skeleton-text"></div>
              <div class="skeleton-line skeleton-text short"></div>
              <div class="skeleton-line skeleton-price"></div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function hideSkeleton(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const skeleton = container.querySelector('.skeleton-container');
  if (skeleton) {
    skeleton.remove();
  }
}

// Initialize offline manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.offlineManager = new OfflineManager();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { OfflineManager, showSkeleton, hideSkeleton };
}
