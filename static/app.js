let isLogin = true;
const apiBase = "http://127.0.0.1:8000/api/v1/marketplace"; // Optimized to point directly to your router prefix
let currentCursor = null;  // 🟢 Global state variable tracking the Base64 composite pagination token

document.getElementById('toggle-form').addEventListener('click', () => {
    isLogin = !isLogin;
    document.getElementById('form-title').innerText = isLogin ? "Artist Login" : "Register Account";
    document.getElementById('toggle-form').innerText = isLogin ? "Create an account instead" : "Already have an account? Login";
    document.querySelectorAll('.reg-field').forEach(el => el.classList.toggle('hidden', isLogin));
});

document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (isLogin) {
        const formData = new URLSearchParams();
        // Since your backend expects an OAuth2 Form login, let's keep hitting the proper auth path
        formData.append('username', document.getElementById('email').value);
        formData.append('password', document.getElementById('password').value);

        const response = await fetch(`http://127.0.0.1:8000/api/v1/auth/login`, { method: 'POST', body: formData });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            loadDashboard();
        } else { alert("Login failed. Check credentials."); }
    } else {
        const payload = {
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            artist_name: document.getElementById('artist_name').value,
            role_type: document.getElementById('role_type').value,
            tenant_id: document.getElementById('tenant_id').value || "tenant_default",
            bio: "Hey there! Ready to jump onto some massive collaborative project tracks."
        };
        const response = await fetch(`http://127.0.0.1:8000/api/v1/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) { alert("Registration complete! Go ahead and log in."); location.reload(); } 
        else { alert("Registration failed."); }
    }
});

async function loadDashboard() {
    const token = localStorage.getItem('token');
    if (!token) return;

    const response = await fetch(`http://127.0.0.1:8000/api/v1/auth/me`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const user = await response.json();
        document.getElementById('user-display-name').innerText = user.artist_name;
        document.getElementById('user-bio').innerText = user.bio || 'No bio added yet.';
        document.getElementById('user-role').innerText = user.role_type;
        document.getElementById('user-tenant').innerText = user.tenant_id;
        
        document.getElementById('auth-card').classList.add('hidden');
        document.getElementById('main-dashboard').classList.remove('hidden');
        
        // 🟢 Sets the initial placeholder for the search field and fires concurrent side panels
        document.getElementById('artist-grid').innerHTML = `<p style="color: #a8a8b3;">Type an artist role above to map local talent by proximity radar.</p>`;
        fetchIncomingRequests();
        fetchActiveConnections(); 
    } else { logout(); }
}

// 🟢 UPGRADED DISCOVERY PIECE: Handles geospatial queries and cursor-based offsets
async function searchProximity(isNewSearch = true) {
    const token = localStorage.getItem('token');
    const targetRole = document.getElementById('role-search-input').value.trim();
    const grid = document.getElementById('artist-grid');
    const paginationBar = document.getElementById('pagination-bar');

    if (!targetRole) {
        alert("Please specify a role type to look up nearby talent!");
        return;
    }

    // Reset global pagination parameters if starting a clean query criteria execution
    if (isNewSearch) {
        currentCursor = null;
        grid.innerHTML = '<p style="color: #a8a8b3;">Scanning local workspace radar coordinates...</p>';
    }

    // Pointing directly to our advanced cursor routing engine path
    let url = `${apiBase}/discover?role_type=${encodeURIComponent(targetRole)}&limit=10`;
    
    // Inject the pagination state token if executing a progressive page advancement sequence
    if (!isNewSearch && currentCursor) {
        url += `&cursor=${encodeURIComponent(currentCursor)}`;
    }

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            const artists = data.artists;
            
            // Advance state references
            currentCursor = data.paging.next_cursor;
            const hasMore = data.paging.has_more;

            if (isNewSearch) grid.innerHTML = '';

            if (artists.length === 0 && isNewSearch) {
                grid.innerHTML = `<p style="color: #a8a8b3;">No creators matching "${targetRole}" located inside this cluster layer.</p>`;
                paginationBar.classList.add('hidden');
                return;
            }

            // Loop and append elements dynamically
            artists.forEach(artist => {
                const el = document.createElement('div');
                el.className = 'artist-card';
                el.innerHTML = `
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <strong style="font-size: 1.1rem; color: #fff;">${artist.artist_name}</strong>
                            <span style="font-size: 0.8rem; color: #04d361; font-weight: bold; background: #121214; padding: 0.2rem 0.5rem; border-radius: 4px;">
                                📍 ${artist.distance_km} km away
                            </span>
                        </div>
                        <span class="artist-role">${artist.role_type.toUpperCase()}</span>
                        <div class="artist-bio">${artist.bio || 'No bio cataloged.'}</div>
                    </div>
                    <button class="connect-btn" onclick="sendConnectRequest(${artist.id})">Connect Handshake</button>
                `;
                grid.appendChild(el);
            });

            // Toggle visual display state of the pagination controls container boundary
            if (hasMore && currentCursor) {
                paginationBar.classList.remove('hidden');
            } else {
                paginationBar.classList.add('hidden');
            }

        } else {
            const err = await response.json();
            grid.innerHTML = `<p style="color: #f75a68;">Spatial Scan Fault: ${err.detail || 'Failed search synchronization execution.'}</p>`;
        }
    } catch (error) {
        console.error("Discovery engine routing failure:", error);
    }
}

async function fetchIncomingRequests() {
    const token = localStorage.getItem('token');
    const response = await fetch(`${apiBase}/requests/incoming`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const requests = await response.json();
        const inbox = document.getElementById('requests-inbox');
        inbox.innerHTML = '';

        if (requests.length === 0) {
            inbox.innerHTML = `<p style="color: #a8a8b3;">Your inbox is empty. No pending handshakes.</p>`;
            return;
        }

        requests.forEach(req => {
            const el = document.createElement('div');
            el.className = 'request-card';
            el.innerHTML = `
                <div>
                    <strong style="color: #8257e5;">Request from User ID: ${req.sender_id}</strong>
                    <div class="request-msg" style="background: #202024; padding: 0.6rem; border-radius: 4px; margin-top: 0.5rem; font-style: italic;">
                        "${req.message}"
                    </div>
                </div>
                <div class="btn-group">
                    <button class="accept-btn" onclick="handleRequestAction(${req.id}, 'accepted')">Accept</button>
                    <button class="decline-btn" onclick="handleRequestAction(${req.id}, 'declined')">Decline</button>
                </div>
            `;
            inbox.appendChild(el);
        });
    }
}

async function fetchActiveConnections() {
    const token = localStorage.getItem('token');
    const response = await fetch(`${apiBase}/connections`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const partners = await response.json();
        const networkBox = document.getElementById('active-connections');
        networkBox.innerHTML = '';

        if (partners.length === 0) {
            networkBox.innerHTML = `<p style="color: #a8a8b3;">No active connections verified yet.</p>`;
            return;
        }

        partners.forEach(partner => {
            const el = document.createElement('div');
            el.className = 'artist-card'; 
            el.innerHTML = `
                <div>
                    <strong style="font-size: 1.1rem; color: #04d361;">🤝 ${partner.artist_name}</strong><br>
                    <span class="artist-role" style="background: #04d361; color: black; font-weight: bold;">${partner.role_type.toUpperCase()}</span>
                    <div class="artist-bio">${partner.bio || 'Connected collaborator profile workspace.'}</div>
                </div>
                <button class="connect-btn" style="background:#202024; border: 1px solid #323238; color:#a8a8b3;" onclick="alert('Shared workspace coming soon!')">Open Project</button>
            `;
            networkBox.appendChild(el);
        });
    }
}

async function sendConnectRequest(receiverId) {
    const token = localStorage.getItem('token');
    const userMsg = prompt("Enter a brief connection handshake introduction message:", "Hey, let's collaborate!");
    if (userMsg === null) return;

    const response = await fetch(`${apiBase}/connect`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ receiver_id: receiverId, message: userMsg })
    });

    if (response.ok) {
        alert("Collaboration connection request dispatched successfully!");
    } else {
        const errData = await response.json();
        alert(`Failed to connect: ${errData.detail || 'Unknown error'}`);
    }
}

async function handleRequestAction(requestId, actionType) {
    const token = localStorage.getItem('token');
    
    const response = await fetch(`${apiBase}/requests/${requestId}/status?action=${actionType}`, {
        method: 'PATCH',
        headers: { 
            'Authorization': `Bearer ${token}`
        }
    });

    if (response.ok) {
        alert(`Request ${actionType} successfully!`);
        fetchIncomingRequests(); 
        fetchActiveConnections();
    } else {
        const errData = await response.json();
        alert(`Failed to update request: ${errData.detail || 'Unknown error'}`);
    }
}

function logout() {
    localStorage.removeItem('token');
    location.reload();
}

if(localStorage.getItem('token')) { loadDashboard(); }