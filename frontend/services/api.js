// API Service for TalkAI Mini Program
const storage = require('../utils/storage');
const envConfig = require('../config/env');

// Get environment-based configuration
const config = envConfig.getConfig();
const BASE_URL = config.API_BASE_URL;
const REQUEST_TIMEOUT = 30000;

console.log(`[API] Using base URL: ${BASE_URL} (env: ${config.ENVIRONMENT})`);

/**
 * Get mock response for development mode
 */
function getMockResponseForEndpoint(url, method) {
  console.log(`Generating mock response for ${method} ${url}`);
  
  if (url.includes('/chat/send') || url.includes('/chat/message')) {
    return {
      response: "Hello! This is a mock response for development. Your chat interface is working correctly! You can now test all the other features of the app.",
      grammar_check: null,
      suggested_vocab: [],
      timestamp: new Date().toISOString()
    };
  }
  
  if (url.includes('/user/profile')) {
    return {
      id: 'dev_user_123',
      nickname: 'Development User',
      avatar_url: '/images/default_avatar.png',
      grade: 'Primary School',
      total_usage_time: 0,
      chat_history_count: 0
    };
  }
  
  return null;
}

/**
 * Make authenticated HTTP request
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const token = storage.getToken();
    
    // Prepare headers
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    // Add authorization header if token exists
    if (token && !options.skipAuth) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const requestUrl = `${BASE_URL}${options.url}`;
    const requestMethod = options.method || 'GET';
    
    console.log(`Making ${requestMethod} request to:`, requestUrl);
    console.log('Request headers:', headers);
    console.log('Request data:', options.data);
    
    // Make request
    wx.request({
      url: requestUrl,
      method: requestMethod,
      data: options.data,
      header: headers,
      timeout: options.timeout || REQUEST_TIMEOUT,
      success: (res) => {
        console.log(`API ${requestMethod} ${options.url} response:`, res.statusCode);
        console.log('Response headers:', res.header);
        console.log('Response data:', res.data);
        
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (res.statusCode === 401 || res.statusCode === 403) {
          console.log('Authentication error detected, checking token type');
          
          const token = storage.getToken();
          // Check if it's a development token
          if (token && token.startsWith('dev_token_')) {
            console.log('Development token detected, using mock response for protected endpoints');
            
            // Handle specific endpoints that need mock responses
            if (options.url.includes('/chat/') || options.url.includes('/user/')) {
              const mockResponse = getMockResponseForEndpoint(options.url, options.method);
              if (mockResponse) {
                resolve(mockResponse);
                return;
              }
            }
          }
          
          // Clear token and reject with auth error
          storage.setToken('');
          reject(new Error('Not authenticated'));
        } else {
          const errorMsg = res.data?.detail || `Request failed with status ${res.statusCode}`;
          console.error('API error:', errorMsg);
          reject(new Error(errorMsg));
        }
      },
      fail: (err) => {
        console.error(`API ${requestMethod} ${options.url} network failure:`, err);
        reject(new Error(err.errMsg || 'Network request failed'));
      }
    });
  });
}

// Authentication APIs
const auth = {
  /**
   * WeChat login
   */
  wechatLogin(loginData) {
    return request({
      url: '/auth/wechat/login',
      method: 'POST',
      data: loginData,
      skipAuth: true
    }).then(result => {
      if (result.access_token) {
        storage.setToken(result.access_token);
      }
      return result;
    });
  },

  /**
   * Logout
   */
  logout() {
    return request({
      url: '/auth/logout',
      method: 'POST'
    }).then(result => {
      storage.setToken('');
      return result;
    });
  },

  /**
   * Verify token
   */
  verifyToken() {
    return request({
      url: '/auth/verify',
      method: 'GET'
    });
  }
};

// User APIs
const user = {
  /**
   * Get user profile
   */
  getProfile() {
    return request({
      url: '/user/profile',
      method: 'GET'
    });
  },

  /**
   * Update user profile
   */
  updateProfile(profileData) {
    return request({
      url: '/user/profile',
      method: 'PUT',
      data: profileData
    });
  },

  /**
   * Update usage time
   */
  updateUsageTime(usageData) {
    return request({
      url: '/user/usage-time',
      method: 'POST',
      data: usageData
    });
  },

  /**
   * Get user statistics
   */
  getStats() {
    return request({
      url: '/user/stats',
      method: 'GET'
    });
  },
  
  /**
   * Get available learning grades
   */
  getAvailableGrades() {
    return request({
      url: '/user/profile/grades',
      method: 'GET',
      skipAuth: true  // This endpoint doesn't require authentication
    });
  },
  
  /**
   * Load vocabulary for current grade
   */
  loadVocab() {
    return request({
      url: '/user/profile/load-vocab',
      method: 'POST',
      data: {}
    });
  },
  
  /**
   * Get vocabulary status
   */
  getVocabStatus() {
    return request({
      url: '/user/profile/vocab-status',
      method: 'GET'
    });
  }
};

// Chat APIs
const chat = {
  /**
   * Send message and get AI response
   */
  sendMessage(messageData, options = {}) {
    if (options.skipAuth) {
      // Use POST /chat/greeting for anonymous chat
      return request({
        url: '/chat/greeting',
        method: 'POST',
        data: { message: messageData.message },
        skipAuth: true
      });
    } else {
      // Use authenticated endpoint
      return request({
        url: '/chat/send',
        method: 'POST',
        data: messageData,
        skipAuth: false
      });
    }
  },

  /**
   * Get conversation history
   */
  getHistory(limit = 20) {
    return request({
      url: `/chat/history?limit=${limit}`,
      method: 'GET'
    });
  },

  /**
   * Check grammar only
   */
  checkGrammar(text) {
    return request({
      url: '/chat/grammar-check',
      method: 'POST',
      data: { text }
    });
  },

  /**
   * Get initial greeting
   */
  getGreeting() {
    return request({
      url: '/chat/greeting',
      method: 'GET'
    });
  }
};

// Vocabulary APIs
const vocab = {
  /**
   * Get vocabulary list
   */
  getList(params = {}) {
    const queryString = Object.keys(params)
      .map(key => `${key}=${encodeURIComponent(params[key])}`)
      .join('&');
    
    return request({
      url: `/vocab/${queryString ? '?' + queryString : ''}`,
      method: 'GET'
    });
  },

  /**
   * Create vocabulary item
   */
  create(vocabData) {
    return request({
      url: '/vocab/',
      method: 'POST',
      data: vocabData
    });
  },

  /**
   * Update vocabulary item
   */
  update(vocabId, vocabData) {
    return request({
      url: `/vocab/${vocabId}`,
      method: 'PUT',
      data: vocabData
    });
  },

  /**
   * Delete vocabulary item
   */
  delete(vocabId) {
    return request({
      url: `/vocab/${vocabId}`,
      method: 'DELETE'
    });
  },

  /**
   * Bulk create vocabulary items
   */
  bulkCreate(wordsData) {
    return request({
      url: '/vocab/bulk',
      method: 'POST',
      data: wordsData
    });
  },

  /**
   * Get vocabulary statistics
   */
  getStats() {
    return request({
      url: '/vocab/stats',
      method: 'GET'
    });
  }
};

// Dictionary APIs
const dict = {
  /**
   * Query single word
   */
  query(word, fuzzy = false) {
    return request({
      url: `/dict/query?word=${encodeURIComponent(word)}&fuzzy=${fuzzy}`,
      method: 'GET'
    });
  },

  /**
   * Search words
   */
  search(query, limit = 10) {
    return request({
      url: `/dict/search?q=${encodeURIComponent(query)}&limit=${limit}`,
      method: 'GET'
    });
  },

  /**
   * Batch query words
   */
  batchQuery(words) {
    return request({
      url: `/dict/batch?words=${words.join(',')}`,
      method: 'GET'
    });
  }
};

// Sync APIs
const sync = {
  /**
   * Sync vocabulary data
   */
  vocabulary(syncData) {
    return request({
      url: '/sync/vocab',
      method: 'POST',
      data: syncData
    });
  },

  /**
   * Get sync status
   */
  getStatus() {
    return request({
      url: '/sync/status',
      method: 'GET'
    });
  },

  /**
   * Force download all data
   */
  forceDownload() {
    return request({
      url: '/sync/force-download',
      method: 'POST'
    });
  }
};

// Convenience functions
function login(jsCode, userInfo) {
  return auth.wechatLogin({
    js_code: jsCode,
    nickname: userInfo?.nickName,
    avatar_url: userInfo?.avatarUrl
  });
}

function sendChatMessage(message, includeHistory = true, options = {}) {
  return chat.sendMessage({
    message,
    include_history: includeHistory
  }, options);
}

function addVocabWord(word, autoLookup = true) {
  return vocab.create({
    word,
    auto_lookup: autoLookup
  });
}

function searchDict(query, limit = 10) {
  return dict.search(query, limit);
}

function syncVocabulary(vocabData) {
  return sync.vocabulary(vocabData);
}

function updateUsageTime(sessionData) {
  return user.updateUsageTime(sessionData);
}

// Export all APIs
module.exports = {
  // Core request function
  request,
  
  // API groups
  auth,
  user,
  chat,
  vocab,
  dict,
  sync,
  
  // Convenience functions
  login,
  sendChatMessage,
  addVocabWord,
  searchDict,
  syncVocabulary,
  updateUsageTime,
  
  // Config
  BASE_URL
};