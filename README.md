# Artist-Collab Backend Engine 🎨🎵

A high-performance, asynchronous ecosystem designed for independent artists, creators, and session musicians to network, showcase portfolios, and discover local collaborations. This backend architecture delivers decentralized discovery, secure media ingestion pipelines, and algorithmic resource protection.

Built with a modern, high-concurrency stack leveraging **FastAPI**, **PostgreSQL** for relational metadata management, **Redis** for distributed server throttling, **MinIO** for resilient cloud object storage, and **Qdrant** for high-dimensional semantic vector search.

---

## 🚀 Core Technical Stack

* **Framework Engine:** FastAPI (Asynchronous Python 3.11 ASGI Core)
* **Relational Database:** PostgreSQL (Structured schema modeling with SQLAlchemy ORM)
* **Distributed Caching & Security:** Redis (In-memory token tracking and rate limiting)
* **Object Storage Engine:** MinIO (S3-Compatible containerized cluster for media streaming)
* **Vector Search Database:** Qdrant (High-dimensional embedding space for AI matching metrics)
* **Infrastructure Containerization:** Docker Compose (Multi-container microservice isolation)

---

## ✨ System Architecture & Implemented Features

### ⏱️ Distributed sliding-window Rate Limiting
To defend against server abuse, malicious scripting, and brute-force vector depletion, the engine incorporates a custom asynchronous ASGI middleware layer backing directly into **Redis**. Every incoming request is intercepted at the ASGI `dispatch` layer, evaluating client identifier frequencies against a rolling window to drop abusive traffic before it hits application routers.

### 📍 Regional Geospatial Data Seeding
The backend contains a sophisticated algorithmic provisioning platform (`seed-artists.py`) that constructs relational artist networks across realistic regional coordinate boundaries. Centered around primary technology and creative hubs (Noida, Delhi, and Gurugram), the script implements a **Gaussian scatter offset** to generate natural, location-aware clusters using specific regional target audiences (`Faker('en_IN')`).

### 💼 Live Architectural Domain Routers
The application layer isolates business logic into dedicated API routers (`app/routers/`):
* **`/api/v1/auth`**: Implements secure credential management, password hashing via `bcrypt`, and stateless session identification using JWT tokens (`python-jose`).
* **`/api/v1/marketplace`**: Handles discovery operations, allowing users to securely build talent profiles, broadcast active collaboration requests, and filter local creators.

---

## 🔮 Strategic Engineering Roadmap

This system is built with an evolutionary architecture. Upcoming integrations currently in the development pipeline include:

* [ ] **Asynchronous Multi-Part Media Pipeline:** Hooking up the `app/services/storage.py` layer with `boto3` to stream and buffer 10-second audio previews directly to the **MinIO Object Container**, generating highly secure presigned storage URLs.
* [ ] **AI Vector Matching Engine:** Utilizing **Qdrant Vector Database** to index high-dimensional profile embeddings, allowing artists to compute semantic similarity scores for hyper-accurate, algorithm-driven collaboration matches.
* [ ] **Automated Quality Gates:** Injecting a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) to automatically enforce syntactic integrity via the **Ruff Analyzer** on every code push.

---

## 🛠️ Local Development Setup

### 1. Environmental Blueprints
Clone the repository and initialize your environmental files:
```bash
git clone [https://github.com/vardaan-7/Artist-collab.git](https://github.com/vardaan-7/Artist-collab.git)
cd Artist-collab
cp .env.example .env