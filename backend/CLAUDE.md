# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
## 部署请参考 deploy_problem.md 中的 “快速部署指南”
## Project Overview

TalkAI is a WeChat Mini Program for AI-powered English learning, featuring intelligent conversation practice, grammar correction, vocabulary management, and dictionary lookup. It consists of a Python FastAPI backend and WeChat Mini Program frontend.

## Architecture

**Backend (FastAPI):**
- `backend/app/api/v1/` - API endpoints (auth, chat, dict, vocab, user, sync)  
- `backend/app/core/` - Configuration and database setup
- `backend/app/models/` - SQLAlchemy data models (user, chat, vocab)
- `backend/app/services/` - Business logic (AI, dictionary, learning analysis, WeChat)
- `backend/app/utils/` - Utility functions and prompts

**Frontend (WeChat Mini Program):**
- `frontend/pages/` - Mini program pages (chat, vocab, dict, profile, login)
- `frontend/services/api.js` - API communication layer
- `frontend/utils/storage.js` - Local storage utilities

**Data:**
- SQLite primary database at `backend/data/db/talkai.db`
- Dictionary database at `backend/data/db/dictionary400k.db` (400K words)
- Redis cache for performance optimization

## Development Commands

### Backend Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py

# Run with Docker Compose
docker-compose up -d

# Check service health
curl http://localhost:8001/health

# View logs
docker-compose logs -f talkai-backend

# Access Redis
docker exec -it talkai-redis redis-cli

# Database operations
sqlite3 data/db/talkai.db ".tables"
```

### Testing
```bash
# Backend tests (pytest configured in requirements.txt)
cd backend
python -m pytest tests/ -v

# API testing
curl "http://localhost:8001/api/v1/dict/query?word=hello"
```

### Deployment Commands
```bash
# Interactive deployment for existing servers
./deployment/deploy-existing-server.sh --interactive

# Deploy with config file
./deployment/deploy-existing-server.sh --config deployment/quick-deploy-config.sh

# Check deployment status
./deployment/deploy-existing-server.sh --status

# View deployment logs
tail -f /tmp/talkai-deploy.log
```

## Configuration

### Environment Variables (.env)
Key configuration in `backend/.env`:
- `MOONSHOT_API_KEY` or `OPENAI_API_KEY` - AI service (required)
- `WECHAT_APP_ID` & `WECHAT_APP_SECRET` - WeChat Mini Program auth
- `SECRET_KEY` - JWT signing (32+ character secure key)
- `DATABASE_URL` - SQLite database path
- `REDIS_URL` - Redis connection string

### Service Ports
- Backend API: 8001 (external) → 8000 (container)
- Redis Cache: 6380 (external) → 6379 (container)
- Nginx: 80/443 (HTTPS proxy to backend)

### API Configuration
Frontend API base URL in `frontend/services/api.js`:
```javascript
const BASE_URL = 'https://api.jimingge.net/api/v1';
```

## AI Service Integration

The application supports two AI providers:
- **Moonshot AI** (recommended): Better Chinese support, faster response
- **OpenAI**: Alternative provider

Provider is auto-detected based on available API keys. AI services power:
- Conversation practice in `/chat` endpoints
- Grammar correction and learning analysis
- Vocabulary learning suggestions

## WeChat Mini Program Setup

1. Configure server domain in WeChat Public Platform:
   - request合法域名: `https://api.jimingge.net`
2. Update `frontend/services/api.js` with your domain
3. Import `frontend/` directory in WeChat Developer Tools
4. Test, upload, and submit for review

## Database Schema

**Core Tables:**
- `users` - User profiles with WeChat integration
- `chat_sessions` & `chat_messages` - Conversation history
- `vocabulary` - Personal vocabulary management
- `learning_reports` - Generated learning analytics

**Dictionary:**
- External SQLite database with 400K English words
- Accessed via `/dict` API endpoints

## Deployment Architecture

**Production Setup:**
- Docker containers orchestrated by docker-compose
- Nginx reverse proxy with SSL termination
- Data persistence via mounted volumes
- Redis caching for performance
- Health checks and automatic restarts

**Key Files:**
- `backend/docker-compose.yml` - Service orchestration
- `backend/Dockerfile` - Python application container
- `deployment/deploy-existing-server.sh` - Automated deployment script

## Development Notes

- No formal linting/formatting tools configured - follow existing code style
- Tests use pytest framework (in requirements.txt)
- Logging configured with loguru to `backend/logs/app.log`
- CORS configured for WeChat Mini Program origins
- Rate limiting implemented for API protection
- JWT tokens expire after 24 hours (configurable)

## Common Tasks

**Add new API endpoint:** Create in `backend/app/api/v1/`, add business logic to `backend/app/services/`, update router imports in `backend/main.py`

**Modify WeChat Mini Program:** Update pages in `frontend/pages/`, modify API calls in `frontend/services/api.js`, test in WeChat Developer Tools

**Database changes:** Modify models in `backend/app/models/`, use SQLAlchemy migration or direct schema updates for SQLite

**AI functionality:** Update prompts in `backend/app/utils/prompts.py`, modify service logic in `backend/app/services/ai.py`
