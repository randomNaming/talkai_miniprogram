# CLAUDE.md

## 本地开发
请激活虚拟开发环境
  source /Users/pean/aiproject/talkai_mini/talkai_py/bookvidenv_new/bin/activate
  cd /Users/pean/aiproject/talkai_mini/backend
  uvicorn main:app --reload --host 0.0.0.0 --port 8000

## 线上部署：用 Docker 


## The following content provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
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

** talkai_py/ **
- `talkai_py/` - local Python code version for the application. The Wechat Mini Program(backend +frontend) is constructed based on talkai_py/ using claude code. 

