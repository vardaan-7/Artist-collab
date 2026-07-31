isLogin = true;
const apiBase = "/api/v1/marketplace"; 
const chatApiBase = "/api/v1/chat"; 
let currentCursor = null;  
let activeChatArtistId = null; 
let chatPollingInterval = null; 

document.getElementById('toggle-form').addEventListener('click', () => {
    isLogin = !isLogin;
    document.getElementById('form-title').innerText = isLogin ? "Welcome back" : "Create your profile";
    document.getElementById('toggle-form').innerText = isLogin ? "New here? Create an account" : "Already have an account? Log in";
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
            alert("Login failed — check your email and password."); 
        }
    } else {
        const payload = {
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            artist_name: document.getElementById('artist_name').value,
            role_type: document.getElementById('role_type').value,
            tenant_id: "tenant_default",
            bio: "Hey there!"
        };
        
        const response = await fetch(`/api/v1/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) { 
            alert("You're in! Log in to get started."); 
            location.reload(); 
        } else { 
            alert("Registration failed. Please try again."); 
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
        
        // Handle Signature Track Visibility and Control Rules dynamically
        const trackContainer = document.getElementById("signature-track-container");
        const uploadFormCard = document.getElementById('audioUploadForm') ? document.getElementById('audioUploadForm').parentElement : null;
        
        if (trackContainer) {
            trackContainer.innerHTML = "";
            
            if (user.signature_track) {
                // If signature track exists, display it and hide the upload interface container
                if (uploadFormCard) uploadFormCard.style.display = "none";
                
                const track = user.signature_track;
                trackContainer.innerHTML = `
                    <div class="track-card">
                        <p class="track-label">🎧 Your track: <span style="color: var(--text);">${track.title}</span></p>
                        <audio controls>
                            <source src="${track.file_url}" type="${track.mime_type || 'audio/mpeg'}">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                `;
            } else {
                // If no signature track exists, show the upload form element interface cleanly
                if (uploadFormCard) uploadFormCard.style.display = "block";
                
                trackContainer.innerHTML = `
                    <div class="track-empty">
                        🎵 No track yet — add a snippet so nearby artists can hear what you sound like.
                    </div>
                `;
            }
        }
        
        document.getElementById('auth-card').classList.add('hidden');
        document.getElementById('main-dashboard').classList.remove('hidden');
        document.getElementById('artist-grid').innerHTML = `<p class="empty-note">Pick a role above to see who's playing nearby.</p>`;
        
        injectChatUIElements();
        fetchIncomingRequests();
        fetchActiveConnections(); 
    } else { logout(); }
}

async function executeAudioUpload(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('portfolioFile');
    const statusDiv = document.getElementById('uploadProgressStatus');
    
    if (!fileInput || !fileInput.files.length) {
        if (statusDiv) statusDiv.innerHTML = '<span class="status-err">Please select an audio file first.</span>';
        return;
    }

    const audioFile = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('title', audioFile.name); 

    if (statusDiv) statusDiv.innerHTML = "Uploading track...";

    try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/v1/media/upload-snippet', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (response.ok) {
            if (statusDiv) statusDiv.innerHTML = '<span class="status-ok">✔ Track added to your profile.</span>';
            fileInput.value = ""; 
            
            // Reload the dashboard metrics immediately to render the native player and hide the form container
            loadDashboard();
        } else {
            const err = await response.json();
            if (statusDiv) statusDiv.innerHTML = `<span class="status-err">Upload failed: ${err.detail || 'Server rejected track'}</span>`;
        }
    } catch (error) {
        console.error("Audio streaming file upload failure:", error);
        if (statusDiv) statusDiv.innerHTML = '<span class="status-err">Network error — check your connection and try again.</span>';
    }
}

async function searchProximity(isNewSearch = true) {
    const token = localStorage.getItem('token');
    const selectedRole = document.getElementById('role-search-input').value;
    const targetRole = selectedRole ? selectedRole.trim() : "";
    const grid = document.getElementById('artist-grid');
    const paginationBar = document.getElementById('pagination-bar');

    if (!targetRole) {
        alert("Pick a role to search for nearby talent.");
        return;
    }

    if (isNewSearch) {
        currentCursor = null;
        grid.innerHTML = '<p class="empty-note">Scanning nearby artists…</p>';
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
            alert("You're searching a bit fast — give it a moment and try again.");
            return;
        }

        if (response.ok) {
            const data = await response.json();
            const artists = data.artists;
            
            currentCursor = data.paging.next_cursor;
            const hasMore = data.paging.has_more;

            if (isNewSearch) grid.innerHTML = '';

            if (artists.length === 0 && isNewSearch) {
                grid.innerHTML = `<p class="empty-note">No "${targetRole}" nearby yet — try a different role or check back later.</p>`;
                paginationBar.classList.add('hidden');
                return;
            }

            artists.forEach(artist => {
                const el = document.createElement('div');
                el.className = 'artist-card';
                el.innerHTML = `
                    <div>
                        <div class="artist-card-top">
                            <span class="artist-name">${artist.artist_name}</span>
                            <span class="chip-distance">📍 ${artist.distance_km} km away</span>
                        </div>
                        <span class="artist-role">${artist.role_type.toUpperCase()}</span>
                        <div class="artist-bio">${artist.bio || 'No bio yet.'}</div>
                    </div>
                    <button class="connect-btn" onclick="sendConnectRequest(${artist.id})">Send connect request</button>
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
            grid.innerHTML = `<p class="error-note">Search failed: ${err.detail || 'Something went wrong. Try again.'}</p>`;
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
            inbox.innerHTML = `<p class="empty-note">No pending requests right now.</p>`;
            return;
        }

        requests.forEach(req => {
            const el = document.createElement('div');
            el.className = 'request-card';
            el.innerHTML = `
                <div>
                    <span class="request-from">Request from artist #${req.sender_id}</span>
                    <div class="request-msg">"${req.message}"</div>
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
    const response = await fetch(`${chatApiBase}/contacts`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        const partners = await response.json();
        const networkBox = document.getElementById('active-connections');
        networkBox.innerHTML = '';

        if (partners.length === 0) {
            networkBox.innerHTML = `<p class="empty-note">No connections yet — accept a request or send one to get started.</p>`;
            return;
        }

        partners.forEach(partner => {
            const el = document.createElement('div');
            el.className = 'artist-card'; 
            el.innerHTML = `
                <div>
                    <span class="artist-name">🤝 ${partner.artist_name}</span><br>
                    <span class="artist-role connected">${partner.role_type.toUpperCase()}</span>
                </div>
                <button class="chat-btn" onclick="openChatWindow(${partner.artist_id}, '${partner.artist_name}')">Chat now</button>
            `;
            networkBox.appendChild(el);
        });
    }
}

function injectChatUIElements() {
    if (document.getElementById('chat-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'chat-modal';
    modal.className = 'chat-modal hidden';

    modal.innerHTML = `
        <div class="chat-header">
            <strong id="chat-title">Chat</strong>
            <button class="chat-close" onclick="closeChatWindow()">✕</button>
        </div>
        <div id="chat-messages" class="chat-messages"></div>

        <form id="chat-submit-form" class="chat-form">
            <input type="text" id="chat-input-text" class="chat-input" placeholder="Type a message…" required autocomplete="off">
            <button type="submit" class="chat-send">Send</button>
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
            fetchChatTimeline(); 
        }
    });
}

function openChatWindow(artistId, artistName) {
    activeChatArtistId = artistId;
    document.getElementById('chat-title').innerText = `Chat with ${artistName}`;
    document.getElementById('chat-modal').classList.remove('hidden');
    
    fetchChatTimeline();
    clearInterval(chatPollingInterval);
    chatPollingInterval = setInterval(fetchChatTimeline, 3000); 
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
            box.innerHTML = `<p class="chat-empty">No messages yet — say hi!</p>`;
            return;
        }

        messages.forEach(msg => {
            const isMe = msg.sender_id !== activeChatArtistId;
            const bubble = document.createElement('div');
            bubble.className = `msg-bubble ${isMe ? 'msg-mine' : 'msg-theirs'}`;
            bubble.innerText = msg.message_text;
            box.appendChild(bubble);
        });
        box.scrollTop = box.scrollHeight; 
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

    if (response.ok) { alert("Connect request sent!"); } 
    else { alert(`Failed to connect: ${(await response.json()).detail || 'Unknown error'}`); }
}

async function handleRequestAction(requestId, actionType) {
    const token = localStorage.getItem('token');
    const response = await fetch(`${apiBase}/requests/${requestId}/status?action=${actionType}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        alert(`Request ${actionType}.`);
        fetchIncomingRequests(); 
        fetchActiveConnections();
    } else { alert(`Failed to update request: ${(await response.json()).detail || 'Unknown error'}`); }
}

function logout() {
    localStorage.removeItem('token');
    location.reload();
}

// Event delegation configuration to capture audio upload form submission
document.addEventListener('submit', (e) => {
    if (e.target && e.target.id === 'audioUploadForm') {
        executeAudioUpload(e);
    }
});

async function syncArtistLocation() {
    const statusDiv = document.getElementById('syncStatus');
    
    if (!navigator.geolocation) {
        statusDiv.innerHTML = '<span class="status-err">Your browser does not support location sharing.</span>';
        return;
    }

    statusDiv.innerHTML = "Requesting device permission...";

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            statusDiv.innerHTML = `Got your coordinates (${lat.toFixed(4)}, ${lon.toFixed(4)}). Syncing…`;

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
                    statusDiv.innerHTML = '<span class="status-ok">✔ Location synced.</span>';
                    loadDashboard();
                } else {
                    const err = await response.json();
                    statusDiv.innerHTML = `<span class="status-err">Sync failed: ${err.detail || 'Server error'}</span>`;
                }
            } catch (error) {
                console.error("Location sync error:", error);
                statusDiv.innerHTML = '<span class="status-err">Network error — check your connection and try again.</span>';
            }
        },
        (error) => {
            console.error("Geolocation error callback:", error);
            statusDiv.innerHTML = '<span class="status-err">Permission denied, or the request timed out.</span>';
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'syncLocationBtn') {
        syncArtistLocation();
    }
});

if(localStorage.getItem('token')) { loadDashboard(); }