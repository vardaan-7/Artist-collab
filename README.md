# Artist-Collab Backend Engine 🎨🎵

A high-performance, asynchronous ecosystem designed for independent artists, creators, and session musicians to network, showcase audio portfolios, and discover algorithmic collaborations through acoustic vibe matching.

Built with a modern, high-concurrency stack leveraging **FastAPI**, **PostgreSQL (Supabase)** for relational metadata management, **Redis** for distributed server throttling, **MinIO / S3 Storage** for resilient media ingestion, **Librosa** for digital signal processing, and **Qdrant** for 33-dimensional sonic vector similarity search.

---

## 🚀 Core Technical Stack

* **Framework Engine:** FastAPI (Asynchronous Python 3.11 ASGI Core)
* **Relational Database:** PostgreSQL / Supabase (Structured schema modeling with SQLAlchemy ORM)
* **Audio DSP Engine:** Librosa & SoundFile (33-D acoustic extraction: Tempo, 20 MFCCs, 12 Chroma STFT)
* **Vector Search Database:** Qdrant Cloud (High-dimensional metric space for cosine vibe matching)
* **Distributed Caching & Security:** Redis (In-memory token tracking and rate limiting)
* **Object Storage Engine:** MinIO / Cloud Storage (Containerized media streaming & presigned access)
* **Resilience Layer:** Multi-Cloud synthetic heartbeat pings preventing free-tier dormancy

---

## ✨ System Architecture & Implemented Features

### 🎧 33-Dimensional Acoustic Feature Extraction & Vibe Matching
The platform features an automated audio analysis pipeline (`app/services/audio_processor.py`). Uploaded audio previews are processed with **Librosa** to compile a normalized 33-dimensional feature vector:
* **Rhythm (1 Dim):** Dynamic tempo detection via beat tracking.
* **Timbre (20 Dims):** 20 Mel-Frequency Cepstral Coefficients (MFCCs).
* **Harmony (12 Dims):** 12 Chroma STFT pitch class energy distributions.

These acoustic embeddings are indexed directly into a **Qdrant Vector Database**, allowing creators to discover collaborators via instantaneous cosine similarity ranking ("Vibe Matching").

### 📁 Asynchronous Media Ingestion & Tenant Isolation
The media pipeline (`app/routers/media.py`) manages multipart file uploads, securely routes audio snippets to cloud object storage, and synchronizes persistent media records across PostgreSQL tables with strict user tenant isolation.

### ⏱️ Distributed Sliding-Window Rate Limiting
To defend against server abuse, malicious scraping, and brute-force vector depletion, the engine incorporates a custom asynchronous ASGI middleware layer backing directly into **Redis** (`app/middleware/rate_limiter.py`). Incoming traffic is evaluated across a rolling window to drop abusive requests before reaching API routers.

### 📍 Regional Geospatial Data Seeding
The backend contains an algorithmic provisioning module (`seed-artists.py`) that constructs relational artist networks across realistic regional coordinate boundaries (Noida, Delhi, and Gurugram) using a **Gaussian scatter offset** and regional profiling (`Faker('en_IN')`).

### 💼 Production API Domain Routers
* **`/api/v1/auth`**: Credential management, bcrypt hashing, and stateless JWT token workflows.
* **`/api/v1/marketplace`**: Discovery operations, profile indexing, collaboration broadcasts, and Qdrant similarity searches.
* **`/api/v1/media`**: Audio portfolio uploads, streaming integration, and radar track synchronization.
* **`/api/v1/chat`**: Real-time communication and messaging channels between matched creators.

---

## 🔮 Strategic Engineering Roadmap

* [x] **JWT Auth & Tenant Isolation:** Secure credential management and stateless JWT authentication.
* [x] **DSP Acoustic Extraction:** 33-dimensional audio vector analysis via Librosa.
* [x] **Qdrant Vector Engine Integration:** Cosine similarity searches for sonic vibe matching.
* [x] **Media Portfolio Pipeline:** Multipart file uploads, MinIO/cloud storage streaming, and database synchronization.
* [x] **Multi-Cloud Keep-Alive Architecture:** Zero-downtime synthetic heartbeat monitoring across Render, Supabase, Qdrant, and Redis.
* [ ] **Real-Time Collaboration Spaces:** Live WebRTC/WebSocket audio jam rooms.
* [ ] **Automated Quality Gates:** GitHub Actions CI workflow enforcing linting with Ruff.

---

## 🛠️ Local Development Setup

### 1. Environmental Blueprints
Clone the repository and initialize your environment variables:
```bash
git clone [https://github.com/vardaan-7/Artist-collab.git](https://github.com/vardaan-7/Artist-collab.git)
cd Artist-collab
cp .env.example .env