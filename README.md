<div align="center">
  
# 🏬 Store Intelligence
### *From Raw CCTV Footage to Live Store Analytics*

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://ultralytics.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## 🚀 Quick Start (5 Commands)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/store-intelligence.git
cd store-intelligence

# 2. Start API + Database
docker compose up -d

# 3. Run detection pipeline
python pipeline/detect.py --clips-dir data/clips --layout data/store_layout.json --output data/events.jsonl

# 4. Feed events into API
python pipeline/feed.py --events data/events.jsonl --api-url http://localhost:8000

# 5. Open dashboard
open http://localhost:8000/dashboard/
