// js/auth.js
const currentUserId = localStorage.getItem('userId');

// Kick out if not logged in
if (!currentUserId && !window.location.href.includes('login.html')) {
    window.location.href = 'login.html';
}

// Global fetch that attaches the ID badge
async function secureFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-User-ID': currentUserId,
        ...(options.headers || {})
    };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        localStorage.clear();
        window.location.href = 'login.html';
    }
    return response;
}

// Side-bar personalizer
window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.profile-name').forEach(el => el.textContent = localStorage.getItem('userFullName'));
    document.querySelectorAll('.profile-role').forEach(el => el.textContent = localStorage.getItem('userRole') || 'Manager');
});