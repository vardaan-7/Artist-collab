let isLogin = true;
const apiBase = "http://127.0.0.1:8000/api/v1";

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
        formData.append('username', document.getElementById('email').value);
        formData.append('password', document.getElementById('password').value);

        const response = await fetch(`${apiBase}/auth/login`, { method: 'POST', body: formData });
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
        const response = await fetch(`${apiBase}/auth/register`, {
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

    const response = await fetch(`${apiBase}/auth/me`, {
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
        
        fetchMarketplace();
        fetchIncomingRequests();
    } else { logout(); }
}

async function fetchMarketplace() {
    const token = localStorage.getItem('token');
    const selectedRole = document.getElementById('role-filter').value;
    
    let url = `${apiBase}/marketplace/artists`;
    if (selectedRole) { url += `?role_type=${selectedRole}`; }

    const response = await fetch(url, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const artists = await response.json();
        const grid = document.getElementById('artist-grid');
        grid.innerHTML = '';
        
        if (artists.length === 0) {
            grid.innerHTML = `<p style="color: #a8a8b3;">No other artists found in your workspace tier.</p>`;
            return;
        }

        artists.forEach(artist => {
            const el = document.createElement('div');
            el.className = 'artist-card';
            el.innerHTML = `
                <div>
                    <strong style="font-size: 1.1rem; color: #fff;">${artist.artist_name}</strong><br>
                    <span class="artist-role">${artist.role_type.toUpperCase()}</span>
                    <div class="artist-bio">${artist.bio || 'No bio set.'}</div>
                </div>
                <button class="connect-btn" onclick="sendConnectRequest(${artist.id})">Connect Handshake</button>
            `;
            grid.appendChild(el);
        });
    }
}

async function fetchIncomingRequests() {
    const token = localStorage.getItem('token');
    const response = await fetch(`${apiBase}/marketplace/requests/incoming`, {
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
                    <button class="accept-btn" onclick="alert('Accept logic coming soon!')">Accept</button>
                    <button class="decline-btn" onclick="alert('Decline logic coming soon!')">Decline</button>
                </div>
            `;
            inbox.appendChild(el);
        });
    }
}

async function sendConnectRequest(receiverId) {
    const token = localStorage.getItem('token');
    const userMsg = prompt("Enter a brief connection handshake introduction message:", "Hey, let's collaborate!");
    if (userMsg === null) return;

    const response = await fetch(`${apiBase}/marketplace/connect`, {
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

function logout() {
    localStorage.removeItem('token');
    location.reload();
}

if(localStorage.getItem('token')) { loadDashboard(); }