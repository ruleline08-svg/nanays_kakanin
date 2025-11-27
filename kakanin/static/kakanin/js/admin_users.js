function getCSRFToken() {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
  if (csrfToken) {
    return csrfToken.value;
  }
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return value;
    }
  }
  return '';
}

function toggleUserStatus(userId, newStatus) {
  const normalizedStatus = typeof newStatus === 'string'
    ? newStatus.trim().toLowerCase()
    : String(Boolean(newStatus));
  const shouldActivate = normalizedStatus === 'true';
  const actionLabel = shouldActivate ? 'activate' : 'deactivate';

  if (!window.confirm(`Are you sure you want to ${actionLabel} this user?`)) {
    return;
  }

  const csrfToken = getCSRFToken();
  if (!csrfToken) {
    window.alert('CSRF token not found. Please refresh the page.');
    return;
  }

  fetch(`/admin-user-toggle/${userId}/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ is_active: shouldActivate }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        window.location.reload();
      } else {
        window.alert(`Error: ${data.error}`);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      window.alert('Error updating user status');
    });
}

function deleteUser(userId, username) {
  if (!window.confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
    return;
  }

  const csrfToken = getCSRFToken();
  if (!csrfToken) {
    window.alert('CSRF token not found. Please refresh the page.');
    return;
  }

  fetch(`/admin-user-delete/${userId}/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        window.location.reload();
      } else {
        window.alert(`Error: ${data.error}`);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      window.alert('Error deleting user');
    });
}

const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');
const sidebarToggle = document.getElementById('sidebarToggle');
const mainContent = document.getElementById('mainContent');
if (sidebarToggle && sidebar && overlay && mainContent) {
  sidebarToggle.addEventListener('click', () => {
    if (window.innerWidth < 1024) {
      sidebar.classList.toggle('show');
      overlay.classList.toggle('hidden');
    } else {
      sidebar.classList.toggle('collapsed');
      mainContent.style.marginLeft = sidebar.classList.contains('collapsed') ? '80px' : '280px';
    }
  });
  overlay.addEventListener('click', () => {
    sidebar.classList.remove('show');
    overlay.classList.add('hidden');
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024) {
      overlay.classList.add('hidden');
      sidebar.classList.remove('show');
      mainContent.style.marginLeft = sidebar.classList.contains('collapsed') ? '80px' : '280px';
    } else {
      sidebar.classList.remove('collapsed');
      mainContent.style.marginLeft = '0';
    }
  });
}

function toggleDropdown(id) {
  const dropdown = document.getElementById(id);
  const allDropdowns = document.querySelectorAll('.dropdown-menu');
  allDropdowns.forEach((d) => {
    if (d.id !== id) {
      d.classList.remove('show');
    }
  });
  if (dropdown) {
    dropdown.classList.toggle('show');
  }
}

document.addEventListener('click', (event) => {
  if (!event.target.closest('.relative')) {
    document.querySelectorAll('.dropdown-menu').forEach((d) => d.classList.remove('show'));
  }
});

let reloadTimer = null;

function showToast(message, variant = 'info') {
  const container = document.getElementById('liveToastContainer');
  if (!container) {
    return;
  }

  const themes = {
    success: 'bg-green-600 text-white',
    error: 'bg-red-600 text-white',
    warning: 'bg-amber-500 text-white',
    info: 'bg-blue-600 text-white',
  };

  const icons = {
    success: 'fas fa-check-circle',
    error: 'fas fa-exclamation-circle',
    warning: 'fas fa-exclamation-triangle',
    info: 'fas fa-info-circle',
  };

  const toast = document.createElement('div');
  toast.className = `flex items-center gap-2 ${themes[variant] || themes.info} px-4 py-3 rounded-lg shadow-lg animate-fadeIn`;

  const iconEl = document.createElement('i');
  iconEl.className = `${icons[variant] || icons.info} text-lg`;
  toast.appendChild(iconEl);

  const textSpan = document.createElement('span');
  textSpan.className = 'flex-1 text-sm font-medium';
  textSpan.textContent = message;
  toast.appendChild(textSpan);

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.setAttribute('aria-label', 'Close');
  closeBtn.className = 'text-white/80 hover:text-white';
  closeBtn.addEventListener('click', () => {
    toast.remove();
  });

  const closeIcon = document.createElement('i');
  closeIcon.className = 'fas fa-times';
  closeBtn.appendChild(closeIcon);

  toast.appendChild(closeBtn);
  container.appendChild(toast);

  window.setTimeout(() => {
    toast.classList.add('animate-fadeOut');
    window.setTimeout(() => toast.remove(), 250);
  }, 2600);
}

const pageSearchInput = document.getElementById('pageSearchInput');
const clearPageSearch = document.getElementById('clearPageSearch');
const searchCounter = document.getElementById('searchCounter');

if (pageSearchInput && clearPageSearch && searchCounter) {
  let currentHighlights = [];
  let currentMatchIndex = 0;

  const removeHighlights = () => {
    currentHighlights.forEach((highlight) => {
      const parent = highlight.parentNode;
      parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
      parent.normalize();
    });
    currentHighlights = [];
    currentMatchIndex = 0;
    searchCounter.classList.add('hidden');
  };

  const highlightText = (searchTerm) => {
    removeHighlights();

    if (!searchTerm || searchTerm.trim() === '') {
      return;
    }

    const main = document.getElementById('mainContent');
    if (!main) {
      return;
    }

    const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (node.parentElement.tagName === 'SCRIPT' ||
            node.parentElement.tagName === 'STYLE' ||
            node.parentElement.classList.contains('highlight-match')) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    const nodesToHighlight = [];
    let node;

    while ((node = walker.nextNode())) {
      const text = node.textContent;
      if (text.toLowerCase().includes(searchTerm.toLowerCase())) {
        nodesToHighlight.push(node);
      }
    }

    nodesToHighlight.forEach((textNode) => {
      const text = textNode.textContent;
      const lowerText = text.toLowerCase();
      const lowerSearch = searchTerm.toLowerCase();

      let lastIndex = 0;
      const fragment = document.createDocumentFragment();

      let index = lowerText.indexOf(lowerSearch);
      while (index !== -1) {
        if (index > lastIndex) {
          fragment.appendChild(document.createTextNode(text.substring(lastIndex, index)));
        }

        const mark = document.createElement('mark');
        mark.className = 'highlight-match';
        mark.style.backgroundColor = '#fef08a';
        mark.style.padding = '2px 0';
        mark.style.borderRadius = '2px';
        mark.textContent = text.substring(index, index + searchTerm.length);
        fragment.appendChild(mark);
        currentHighlights.push(mark);

        lastIndex = index + searchTerm.length;
        index = lowerText.indexOf(lowerSearch, lastIndex);
      }

      if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
      }

      textNode.parentNode.replaceChild(fragment, textNode);
    });

    if (currentHighlights.length > 0) {
      searchCounter.textContent = `${currentHighlights.length} found`;
      searchCounter.classList.remove('hidden');

      if (currentHighlights[0]) {
        currentHighlights[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        currentHighlights[0].style.backgroundColor = '#fbbf24';
      }
    }
  };

  pageSearchInput.addEventListener('input', function onPageSearchInput() {
    const searchTerm = this.value.trim();

    if (searchTerm) {
      clearPageSearch.classList.remove('hidden');
      highlightText(searchTerm);
    } else {
      clearPageSearch.classList.add('hidden');
      removeHighlights();
    }
  });

  clearPageSearch.addEventListener('click', () => {
    pageSearchInput.value = '';
    clearPageSearch.classList.add('hidden');
    removeHighlights();
    pageSearchInput.focus();
  });

  pageSearchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && currentHighlights.length > 0) {
      event.preventDefault();

      if (currentHighlights[currentMatchIndex]) {
        currentHighlights[currentMatchIndex].style.backgroundColor = '#fef08a';
      }

      currentMatchIndex = (currentMatchIndex + 1) % currentHighlights.length;

      if (currentHighlights[currentMatchIndex]) {
        currentHighlights[currentMatchIndex].style.backgroundColor = '#fbbf24';
        currentHighlights[currentMatchIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      searchCounter.textContent = `${currentMatchIndex + 1} of ${currentHighlights.length}`;
    }
  });
}

function openEditModal({ userId = null, url = null } = {}) {
  const modal = document.getElementById('editUserModal');
  const iframe = document.getElementById('editIframe');

  if (!modal || !iframe) {
    return;
  }

  const src = url || (userId ? `/admin-user-edit/${userId}/` : null);
  if (!src) {
    return;
  }

  iframe.src = src;
  modal.classList.remove('hidden');
}

function closeEditModal() {
  const modal = document.getElementById('editUserModal');
  const iframe = document.getElementById('editIframe');

  if (!modal || !iframe) {
    return;
  }

  modal.classList.add('hidden');
  iframe.src = 'about:blank';
}

function openCreateModal({ url = null } = {}) {
  const modal = document.getElementById('createUserModal');
  const iframe = document.getElementById('createIframe');

  if (!modal || !iframe) {
    return;
  }

  const src = url || '/admin-user-create/';
  iframe.src = src;
  modal.classList.remove('hidden');
}

function closeCreateModal() {
  const modal = document.getElementById('createUserModal');
  const iframe = document.getElementById('createIframe');

  if (!modal || !iframe) {
    return;
  }

  modal.classList.add('hidden');
  iframe.src = 'about:blank';
}

function bindUserModalTriggers() {
  const editButtons = document.querySelectorAll('[data-edit-user]');
  editButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const userId = button.getAttribute('data-edit-user');
      const editUrl = button.getAttribute('data-edit-url');

      const options = {};
      if (editUrl) {
        options.url = editUrl;
      } else if (userId) {
        options.userId = userId;
      }

      if (options.url || options.userId) {
        openEditModal(options);
      }
    });
  });

  const createButtons = document.querySelectorAll('[data-create-user]');
  createButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const createUrl = button.getAttribute('data-create-url');
      const options = createUrl ? { url: createUrl } : {};
      openCreateModal(options);
    });
  });
}

function bindModalDismissHandlers() {
  const editModal = document.getElementById('editUserModal');
  if (editModal) {
    const editCloseButton = editModal.querySelector('[data-close-edit-modal]');
    if (editCloseButton) {
      editCloseButton.addEventListener('click', () => {
        closeEditModal();
      });
    }

    editModal.addEventListener('click', (event) => {
      if (event.target === editModal) {
        closeEditModal();
      }
    });
  }

  const createModal = document.getElementById('createUserModal');
  if (createModal) {
    const createCloseButton = createModal.querySelector('[data-close-create-modal]');
    if (createCloseButton) {
      createCloseButton.addEventListener('click', () => {
        closeCreateModal();
      });
    }

    createModal.addEventListener('click', (event) => {
      if (event.target === createModal) {
        closeCreateModal();
      }
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      const editVisible = editModal && !editModal.classList.contains('hidden');
      const createVisible = createModal && !createModal.classList.contains('hidden');

      if (editVisible) {
        closeEditModal();
      }

      if (createVisible) {
        closeCreateModal();
      }
    }
  });
}

function initializeUserModalInteractions() {
  bindUserModalTriggers();
  bindModalDismissHandlers();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeUserModalInteractions);
} else {
  initializeUserModalInteractions();
}

function handleUserModalMessage(event) {
  if (!event || !event.data) {
    return;
  }

  const { type, message } = event.data;

  if (type === 'userUpdated') {
    closeEditModal();
    showToast(message || 'User has been updated successfully.', 'success');
    if (reloadTimer) {
      window.clearTimeout(reloadTimer);
    }
    reloadTimer = window.setTimeout(() => {
      window.location.reload();
    }, 1600);
  } else if (type === 'userCreated') {
    closeCreateModal();
    showToast(message || 'User has been created successfully.', 'success');
    if (reloadTimer) {
      window.clearTimeout(reloadTimer);
    }
    reloadTimer = window.setTimeout(() => {
      window.location.reload();
    }, 1400);
  } else if (type === 'userUpdateError' || type === 'userCreateError') {
    const variant = type === 'userUpdateError' ? 'error' : 'warning';
    showToast(message || 'An error occurred. Please try again.', variant);
  }
}

window.addEventListener('message', handleUserModalMessage);

window.adminUsersPage = {
  openEditModal,
  closeEditModal,
  openCreateModal,
  closeCreateModal,
};
