// Config
const API_URL = 'http://localhost:8000';

// State
let currentSessionId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Auth Functions
function checkAuth() {
    // Try to access /auth/me to check if session is valid
    fetch(`${API_URL}/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(res => {
        if (res.ok) {
            showMainView();
            loadDocuments();
        } else {
            showAuthView();
        }
    })
    .catch(() => showAuthView());
}

function setupEventListeners() {
    // Login form
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        try {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            if (res.ok) {
                showMainView();
                loadDocuments();
            } else {
                const data = await res.json();
                document.getElementById('login-error').textContent = data.detail || 'Error al iniciar sesión';
            }
        } catch (err) {
            document.getElementById('login-error').textContent = 'Error de conexión';
        }
    });

    // Register form
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        
        try {
            const res = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            
            if (res.ok) {
                // Auto login after register
                const loginRes = await fetch(`${API_URL}/auth/login`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                if (loginRes.ok) {
                    showMainView();
                    loadDocuments();
                }
            } else {
                const data = await res.json();
                document.getElementById('register-error').textContent = data.detail || 'Error al registrarse';
            }
        } catch (err) {
            document.getElementById('register-error').textContent = 'Error de conexión';
        }
    });

    // Upload form
    document.getElementById('upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('pdf-file');
        const file = fileInput.files[0];
        
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        const statusDiv = document.getElementById('upload-status');
        statusDiv.innerHTML = '<span class="status-loading">📤 Subiendo...</span>';
        
        try {
            const res = await fetch(`${API_URL}/documents/ingest`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            
            if (res.ok) {
                const data = await res.json();
                statusDiv.innerHTML = `<span class="status-success">✅ ${data.filename} indexado (${data.chunks_indexed} chunks)</span>`;
                fileInput.value = '';
                loadDocuments();
            } else {
                const data = await res.json();
                statusDiv.innerHTML = `<span class="status-error">❌ ${data.detail || 'Error al subir'}</span>`;
            }
        } catch (err) {
            statusDiv.innerHTML = '<span class="status-error">❌ Error de conexión</span>';
        }
    });

    // Chat form
    document.getElementById('chat-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message
        addMessage(message, 'user');
        input.value = '';
        
        // Show typing indicator
        showTyping();
        
        try {
            const body = { content: message };
            if (currentSessionId) {
                body.session_id = currentSessionId;
            }
            
            const res = await fetch(`${API_URL}/chat/ask`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            hideTyping();
            
            if (res.ok) {
                const data = await res.json();
                if (!currentSessionId && data.session_id) {
                    currentSessionId = data.session_id;
                }
                addMessage(data.content, 'bot');
            } else {
                const err = await res.json();
                addMessage(`Error: ${err.detail || 'No se pudo obtener respuesta'}`, 'error');
            }
        } catch (err) {
            hideTyping();
            addMessage('Error de conexión con el servidor', 'error');
        }
    });
}

// View Management
function showAuthView() {
    document.getElementById('auth-view').classList.remove('hidden');
    document.getElementById('main-view').classList.add('hidden');
}

function showMainView() {
    document.getElementById('auth-view').classList.add('hidden');
    document.getElementById('main-view').classList.remove('hidden');
}

function showTab(tab) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const tabs = document.querySelectorAll('.tab-btn');
    
    tabs.forEach(t => t.classList.remove('active'));
    
    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabs[0].classList.add('active');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabs[1].classList.add('active');
    }
    
    // Clear errors
    document.getElementById('login-error').textContent = '';
    document.getElementById('register-error').textContent = '';
}

// Chat Functions
function addMessage(content, type) {
    const container = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const timestamp = new Date().toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    messageDiv.innerHTML = `
        ${escapeHtml(content)}
        <div class="timestamp">${timestamp}</div>
    `;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function showTyping() {
    const container = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <span style="opacity: 0.6; font-style: italic;">pensando...</span>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
}

function newChat() {
    currentSessionId = null;
    document.getElementById('chat-messages').innerHTML = `
        <div class="welcome-message">
            <h4>👋 ¡Hola! Soy tu asistente</h4>
            <p>Puedo responder tus preguntas basándome en los documentos que subas.</p>
            <p class="note">Soy conversacional y amigable, pero siempre me baso en la información de tus documentos.</p>
        </div>
    `;
}

// Document Functions
async function loadDocuments() {
    const listDiv = document.getElementById('documents-list');
    listDiv.innerHTML = '<p class="empty">Cargando...</p>';
    
    try {
        const res = await fetch(`${API_URL}/documents/list`, {
            credentials: 'include'
        });
        
        if (res.ok) {
            const data = await res.json();
            renderDocuments(data.sources);
        } else {
            listDiv.innerHTML = '<p class="empty">Error al cargar documentos</p>';
        }
    } catch (err) {
        listDiv.innerHTML = '<p class="empty">Error de conexión</p>';
    }
}

function renderDocuments(sources) {
    const listDiv = document.getElementById('documents-list');
    
    if (!sources || Object.keys(sources).length === 0) {
        listDiv.innerHTML = '<p class="empty">No hay documentos</p>';
        return;
    }
    
    listDiv.innerHTML = Object.entries(sources).map(([name, info]) => `
        <div class="document-item">
            <div class="info">
                <div class="name" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
                <div class="chunks">${info.count} chunks</div>
            </div>
            <button class="delete-btn" onclick="deleteDocument('${escapeHtml(name)}')">🗑️</button>
        </div>
    `).join('');
}

async function deleteDocument(source) {
    if (!confirm(`¿Eliminar "${source}"?`)) return;
    
    try {
        const res = await fetch(`${API_URL}/documents/${encodeURIComponent(source)}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (res.ok) {
            loadDocuments();
        } else {
            alert('Error al eliminar documento');
        }
    } catch (err) {
        alert('Error de conexión');
    }
}

// Logout
async function logout() {
    try {
        await fetch(`${API_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (err) {
        // Ignore error
    }
    showAuthView();
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}