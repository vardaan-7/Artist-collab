isLogin = true;
const apiBase = "/api/v1/marketplace"; 
const chatApiBase = "/api/v1/chat"; // 🟢 Connected to your new chat router prefix
let currentCursor = null;  
let activeChatArtistId = null; // 🟢 Globally tracks who you are messaging
let chatPollingInterval = null; // 🟢 Controls short polling loops

document.getElementById('toggle-form').addEventListener('click', () => {
    isLogin = !isLogin;
    document.getElementById('form-title').innerText = isLogin ? "Artist Login" : "Register Account";
    document.getElementById('toggle-form').innerText = isLogin ? "Create an account instead" : "Already have an account? Login";
    document.getElementById('email').value = "";
    document.getElementById('password').value = "";
    if(document.getElementById('artist_name')) document.getElementById('artist_name').value = "";
    document.querySelectorAll('.reg-field').forEach(el => el.classList.toggle('hidden', isLogin));
});

document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (isLogin) {
        const formData = new URLSearchParams();
        formData.append('username', document.getElementById('email').value);
        formData.append('password', document.getElementById('password').value);

        const response = await fetch(`/api/v1/auth/login`, { method: 'POST', body: formData });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            
            document.getElementById('email').value = "";
            document.getElementById('password').value = "";
            
            loadDashboard();
        } else { 
            alert("Login failed. Check credentials."); 
        }
    } else {
        const payload = {
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            artist_name: document.getElementById('artist_name').value,
            role_type: document.getElementById('role_type').value,
            tenant_id: document.getElementById('tenant_id').value || "tenant_default",
            bio: "Hey there! Ready to jump onto some massive collaborative project tracks."
        };
        
        // Changed to a relative path here as well
        const response = await fetch(`/api/v1/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) { 
            alert("Registration complete! Go ahead and log in."); 
            location.reload(); 
        } else { 
            alert("Registration failed."); 
        }
    }
});

async function loadDashboard() {
    const token = localStorage.getItem('token');
    if (!token) return;

    const response = await fetch(`/api/v1/auth/me`,{
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const user = await response.json();
        document.getElementById('user-display-name').innerText = user.artist_name;
        document.getElementById('user-bio').innerText = user.bio || 'No bio added yet.';
        document.getElementById('user-role').innerText = user.role_type;
        document.getElementById('user-tenant').innerText = user.tenant_id;
        
        const trackContainer = document.getElementById("signature-track-container");
        if (trackContainer) {
            if (user.signature_track) {
                const track = user.signature_track;
                trackContainer.innerHTML = `
                    <div style="background: #202024; padding: 1rem; border: 1px solid #323238; border-radius: 4px; text-align: left;">
                        <p style="margin: 0 0 0.5rem 0; font-size: 0.85rem; color: #04d361; font-weight: bold;">
                            📻 Your Signature Track: <span style="color: #ffffff;">${track.title}</span>
                        </p>
                        <audio controls style="width: 100%; height: 32px; outline: none; margin-top: 0.25rem;">
                            <source src="${track.file_url}" type="${track.mime_type}">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                `;
            } else {
                trackContainer.innerHTML = `
                    <div style="background: #121214; padding: 1rem; border: 1px dashed #323238; border-radius: 4px; font-size: 0.8rem; color: #a8a8b3; text-align: center;">
                        🎵 No signature track uploaded. Drop a snippet to unlock vector matchmaking profile radar!
                    </div>
                `;
            }
        }
        
        document.getElementById('auth-card').classList.add('hidden');
        document.getElementById('main-dashboard').classList.remove('hidden');
        
        document.getElementById('artist-grid').innerHTML = `<p style="color: #a8a8b3;">Type an artist role above to map local talent by proximity radar.</p>`;
        
        // Inject structural Chat HTML Container dynamically at the base of the page layout
        injectChatUIElements();

        fetchIncomingRequests();
        fetchActiveConnections(); 
    } else { logout(); }
}

async function searchProximity(isNewSearch = true) {
    const token = localStorage.getItem('token');
    const targetRole = document.getElementById('role-search-input').value.trim();
    const grid = document.getElementById('artist-grid');
    const paginationBar = document.getElementById('pagination-bar');

    if (!targetRole) {
        alert("Please specify a role type to look up nearby talent!");
        return;
    }

    if (isNewSearch) {
        currentCursor = null;
        grid.innerHTML = '<p style="color: #a8a8b3;">Scanning local workspace radar coordinates...</p>';
    }

    let url = `${apiBase}/discover?role_type=${encodeURIComponent(targetRole)}&limit=10`;
    
    if (!isNewSearch && currentCursor) {
        url += `&cursor=${encodeURIComponent(currentCursor)}`;
    }

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.status === 429) {
            alert("⚠️ Rate limit reached! Slow down your talent search!");
            return;
        }

        if (response.ok) {
            const data = await response.json();
            const artists = data.artists;
            
            currentCursor = data.paging.next_cursor;
            const hasMore = data.paging.has_more;

            if (isNewSearch) grid.innerHTML = '';

            if (artists.length === 0 && isNewSearch) {
                grid.innerHTML = `<p style="color: #a8a8b3;">No creators matching "${targetRole}" located inside this cluster layer.</p>`;
                paginationBar.classList.add('hidden');
                return;
            }

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
    
    // 🔍 Fetching from our newly deduplicated distinct contacts path
    const response = await fetch(`${chatApiBase}/contacts`, {
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
                </div>
                <button class="connect-btn" style="background:#0070f3; border: none; color:#ffffff;" onclick="openChatWindow(${partner.artist_id}, '${partner.artist_name}')">Chat Now</button>
            `;
            networkBox.appendChild(el);
        });
    }
}

// 🟢 CHAT INTERACTION OVERLAY LOGIC
function injectChatUIElements() {
    if (document.getElementById('chat-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'chat-modal';
    modal.className = 'hidden';
    modal.style = "position:fixed; bottom:20px; right:20px; width:360px; height:450px; background:#121214; border:1px solid #29292e; border-radius:8px; box-shadow:0 10px 25px rgba(0,0,0,0.5); display:flex; flex-direction:column; z-index:9999; color:white; font-family:sans-serif;";
    
    modal.innerHTML = `
        <div style="padding:12px; background:#202024; border-bottom:1px solid #29292e; display:flex; justify-content:space-between; align-items:center; border-top-left-radius:8px; border-top-right-radius:8px;">
            <div>
                <strong id="chat-title" style="color:#04d361;">Chat Pane</strong>
            </div>
            <button onclick="closeChatWindow()" style="background:transparent; border:none; color:#a8a8b3; cursor:pointer; font-size:16px;">✕</button>
        </div>
        <div id="chat-messages" style="flex:1; padding:15px; overflow-y:auto; display:flex; flex-direction:column; gap:10px; background:#121214;"></div>
        
        <form id="chat-submit-form" style="padding:10px; border-top:1px solid #29292e; display:flex !important; flex-direction:row !important; align-items:center !important; gap:8px !important; background:#202024; border-bottom-left-radius:8px; border-bottom-right-radius:8px; width:100% !important; box-sizing:border-box !important;">
            
            <input type="text" id="chat-input-text" placeholder="Type text..." required autocomplete="off" 
                style="flex: 1 !important; display: block !important; width: 100% !important; min-width: 0 !important; height: 38px !important; padding: 0 12px !important; background:#121214 !important; border:1px solid #29292e !important; color:white !important; border-radius:4px !important; outline:none !important; box-sizing:border-box !important;">
            
            <button type="submit" 
                style="flex-shrink: 0 !important; width: auto !important; height: 38px !important; background:#0070f3 !important; color:white !important; border:none !important; padding:0 20px !important; border-radius:4px !important; cursor:pointer !important; font-weight:bold !important; white-space:nowrap !important; box-sizing:border-box !important;">
                Send
            </button>
        </form>
    `;
    document.body.appendChild(modal);

    document.getElementById('chat-submit-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('chat-input-text');
        const text = input.value.trim();
        if (!text || !activeChatArtistId) return;

        const token = localStorage.getItem('token');
        const response = await fetch(`${chatApiBase}/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ receiver_id: activeChatArtistId, message_text: text })
        });

        if (response.ok) {
            input.value = "";
            fetchChatTimeline(); // Reload view immediately
        }
    });
}

function openChatWindow(artistId, artistName) {
    activeChatArtistId = artistId;
    document.getElementById('chat-title').innerText = `Chat with ${artistName}`;
    document.getElementById('chat-modal').classList.remove('hidden');
    
    fetchChatTimeline();
    clearInterval(chatPollingInterval);
    chatPollingInterval = setInterval(fetchChatTimeline, 3000); // 🕒 Poll every 3 seconds
}

function closeChatWindow() {
    document.getElementById('chat-modal').classList.add('hidden');
    activeChatArtistId = null;
    clearInterval(chatPollingInterval);
}

async function fetchChatTimeline() {
    if (!activeChatArtistId) return;
    const token = localStorage.getItem('token');
    
    const response = await fetch(`${chatApiBase}/history/${activeChatArtistId}`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const messages = await response.json();
        const box = document.getElementById('chat-messages');
        box.innerHTML = '';

        if (messages.length === 0) {
            box.innerHTML = `<p style="color:#555; text-align:center; font-size:12px; margin-top:20px;">No messages. Send a message to start!</p>`;
            return;
        }

        messages.forEach(msg => {
            const isMe = msg.sender_id !== activeChatArtistId;
            const bubble = document.createElement('div');
            bubble.style = `
                padding: 8px 12px; 
                border-radius: 8px; 
                max-width: 75%; 
                font-size: 13px; 
                word-break: break-word;
                align-self: ${isMe ? 'flex-end' : 'flex-start'}; 
                background: ${isMe ? '#0070f3' : '#29292e'};
                color: white;
            `;
            bubble.innerText = msg.message_text;
            box.appendChild(bubble);
        });
        box.scrollTop = box.scrollHeight; // Auto-scroll down
    }
}

async function sendConnectRequest(receiverId) {
    const token = localStorage.getItem('token');
    const userMsg = prompt("Enter a brief connection handshake introduction message:", "Hey, let's collaborate!");
    if (userMsg === null) return;

    const response = await fetch(`${apiBase}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ receiver_id: receiverId, message: userMsg })
    });

    if (response.ok) { alert("Collaboration connection request dispatched successfully!"); } 
    else { alert(`Failed to connect: ${(await response.json()).detail || 'Unknown error'}`); }
}

async function handleRequestAction(requestId, actionType) {
    const token = localStorage.getItem('token');
    const response = await fetch(`${apiBase}/requests/${requestId}/status?action=${actionType}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        alert(`Request ${actionType} successfully!`);
        fetchIncomingRequests(); 
        fetchActiveConnections();
    } else { alert(`Failed to update request: ${(await response.json()).detail || 'Unknown error'}`); }
}

function logout() {
    localStorage.removeItem('token');
    location.reload();
}

if(localStorage.getItem('token')) { loadDashboard(); }
async function syncArtistLocation() {
    const statusDiv = document.getElementById('syncStatus');
    
    if (!navigator.geolocation) {
        statusDiv.innerHTML = '<span style="color: red;">Your browser does not support geolocation metrics.</span>';
        return;
    }

    statusDiv.innerHTML = "Requesting device permission...";

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            statusDiv.innerHTML = `Coordinates captured (${lat.toFixed(4)}, ${lon.toFixed(4)}). Syncing cloud profile...`;

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/v1/auth/update-location', {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ latitude: lat, longitude: lon })
                });

                if (response.ok) {
                    statusDiv.innerHTML = '<span style="color: green;">✔ Profile location synced successfully!</span>';
                    if (typeof loadMarketplace === 'function') loadMarketplace();
                } else {
                    const err = await response.json();
                    statusDiv.innerHTML = `<span style="color: red;">Sync failed: ${err.detail || 'Server error'}</span>`;
                }
            } catch (error) {
                console.error("Location sync error:", error);
                statusDiv.innerHTML = '<span style="color: red;">Network failure connecting to profile router.</span>';
            }
        },
        (error) => {
            console.error("Geolocation error callback:", error);
            statusDiv.innerHTML = '<span style="color: red;">Permission denied or location retrieval timed out.</span>';
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'syncLocationBtn') {
        syncArtistLocation();
    }
});