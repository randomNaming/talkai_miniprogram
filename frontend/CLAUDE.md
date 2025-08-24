# CLAUDE.md

## 开发环境设置

### 当前开发模式：本地前端 + 本地后端开发
- **环境自动检测**：前端会自动检测运行环境并切换API地址
- **本地开发**：微信开发者工具中运行 → 使用 `http://localhost:8000/api/v1`
- **生产环境**：真实微信环境中运行 → 使用 `https://api.jimingge.net/api/v1`

### 本地开发启动流程
1. **启动本地后端**：
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动前端开发**：
   - 打开微信开发者工具
   - 导入 `frontend/` 目录
   - 前端会自动使用本地API：`http://localhost:8000/api/v1`

### 环境配置文件
- `config/env.js`：自动环境检测和API地址切换
- 开发环境：自动检测微信开发者工具环境
- 生产环境：自动检测真实微信环境

## Project Overview

This is the WeChat Mini Program frontend for TalkAI, an English learning app that features AI-powered conversation practice, vocabulary management, and dictionary lookup functionality.

## Architecture

### Main Components
- **App Entry** (`app.js`): Global app state, user session management, data synchronization
- **API Service** (`services/api.js`): Centralized HTTP client with authentication and error handling
- **Storage Utility** (`utils/storage.js`): Local storage management for tokens, user data, and offline capability
- **Pages**: Core user interface components (chat, vocab, dict, profile, login)

### Page Structure
- **Chat** (`pages/chat/`): Main conversation interface with AI assistant
- **Vocabulary** (`pages/vocab/`): Personal vocabulary management and learning progress
- **Dictionary** (`pages/dict/`): Word lookup and definitions
- **Profile** (`pages/profile/`): User settings and statistics
- **Login** (`pages/login/`): WeChat authentication

## Development Commands

### WeChat Mini Program Development
```bash
# Open WeChat Developer Tools and import the frontend/ directory
# No traditional build process - WeChat handles compilation

# Test in simulator or preview on device through WeChat Developer Tools
```

### Configuration Updates
```bash
# Update API endpoint in services/api.js
const BASE_URL = 'https://api.jimingge.net/api/v1'; # Current production endpoint

# Update WeChat Mini Program ID in project.config.json
"appid": "wxb45f0d5fa6530db4"
```

## Key Configuration Files

### WeChat Mini Program Config (`app.json`)
- Defines page routing, navigation bar, tab bar configuration
- Sets network timeout, permissions, and performance optimizations
- Main navigation: Chat, Vocabulary, Dictionary, Profile

### Project Config (`project.config.json`)
- WeChat Developer Tools settings and Mini Program app ID
- Compilation settings (ES6 transpilation, minification)
- Editor preferences (4-space indentation)

### API Configuration (`services/api.js`)
- Centralized HTTP client with Bearer token authentication
- Automatic token refresh and login redirect on 401 errors
- Organized API endpoints: auth, user, chat, vocab, dict, sync
- 30-second request timeout with comprehensive error handling

## Local Storage Strategy

### Data Persistence
- **Authentication**: JWT tokens and user profile data
- **Offline Support**: Vocabulary list, conversation history cached locally
- **Settings**: User preferences for grammar correction, sync intervals
- **Sync**: Last sync timestamp for delta updates with backend

### Storage Keys
```javascript
STORAGE_KEYS = {
  TOKEN: 'talkai_token',
  USER_INFO: 'talkai_user_info', 
  VOCAB_LIST: 'talkai_vocab_list',
  CONVERSATION_HISTORY: 'talkai_conversation',
  LAST_SYNC_TIME: 'talkai_last_sync',
  APP_SETTINGS: 'talkai_settings'
}
```

## WeChat Mini Program Deployment

### Domain Whitelist Configuration
Must configure in WeChat Public Platform → Development Settings:
- Request domains: `https://api.jimingge.net`
- Upload/Download domains: `https://api.jimingge.net` (if file operations needed)

### Development vs Production
- **Development**: Enable "Do not verify request domains" in WeChat Developer Tools
- **Production**: Must disable domain verification bypass for app store submission
- **Testing**: Use WeChat Developer Tools simulator or scan QR code for device testing

## Authentication Flow

### App Startup Flow (Instant Chat)
1. App launches directly into chat interface (no login page)
2. Chat interface is immediately functional - users can send messages right away
3. Authentication happens automatically on first API call:
   - Background token verification if exists
   - Seamless WeChat login when needed (transparent to user)
   - No blocking or waiting states
4. All features work immediately without user intervention

**User Experience Features**:
- **Zero Friction**: No login screens, buttons, or waiting
- **Instant Functionality**: Send messages immediately upon opening app
- **Transparent Auth**: Authentication handled behind the scenes
- **Progressive Enhancement**: Features work immediately, sync in background
- **Seamless Experience**: Users never see authentication process

### Session Management
- Tokens stored persistently in WeChat storage
- App checks login status on launch
- Usage time tracking for analytics
- Automatic logout and cleanup on token expiry

## Data Synchronization

### Offline-First Design
- All vocabulary and chat data cached locally
- Background sync when app gains network connectivity
- Conflict resolution: server data takes precedence
- Incremental sync using last sync timestamps

### Sync Points
- App launch/resume (if logged in)
- Manual refresh in vocab/profile pages  
- Before app backgrounding (usage time updates)
- After adding new vocabulary words

## Development Notes

### Code Style
- Follow existing WeChat Mini Program patterns
- Use `require()` for module imports
- Console.log for debugging (automatically stripped in production)
- Error handling with try-catch and API response validation

### API Integration
- All API calls go through `services/api.js` wrapper
- Use convenience functions: `sendChatMessage()`, `addVocabWord()`, etc.
- Handle network errors gracefully with user feedback
- Respect 30-second timeout for long-running requests

### WeChat-Specific Considerations
- Use `wx.*` APIs for platform features (storage, navigation, user info)
- Handle WeChat app lifecycle (onShow/onHide events)
- Follow WeChat UI/UX guidelines for consistency
- Test on real devices for performance and compatibility

## Testing

### Development Environment Handling
The app automatically detects the environment and provides appropriate functionality:

**Development Mode** (WeChat Developer Tools):
- Uses mock authentication to bypass WeChat login issues
- Provides simulated AI responses for testing chat interface
- No backend API calls required for basic functionality testing
- Automatic fallback when real authentication fails

**Production Mode** (Real WeChat environment):
- Uses real WeChat login and backend API integration
- Full functionality with AI responses from backend service

### Manual Testing Workflow
1. **WeChat Developer Tools**: Automatic mock mode for immediate testing
2. **Device testing**: Use QR code preview for real environment testing  
3. **Offline scenarios**: Test by disabling network connectivity
4. **Backend integration**: Verify API calls work in production environment
5. **Authentication flow**: Test real WeChat login on actual devices

### Key Test Scenarios  
- **Development**: Mock responses and simulated authentication
- **Production**: Real authentication and AI chat responses
- **Network resilience**: Graceful handling of connection issues
- **Cross-environment**: Seamless switching between dev and production modes
- **Error handling**: Fallback mechanisms when services unavailable