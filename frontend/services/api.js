// API Service for TalkAI Mini Program
const storage = require('../utils/storage');

// Configuration
const BASE_URL = 'https://api.jimingge.net/api/v1';
const REQUEST_TIMEOUT = 30000;

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
    
    // Make request
    wx.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header: headers,
      timeout: options.timeout || REQUEST_TIMEOUT,
      success: (res) => {
        console.log(`API ${options.method || 'GET'} ${options.url}:`, res.statusCode);
        
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          // Unauthorized - clear token and redirect to login
          storage.setToken('');
          wx.reLaunch({
            url: '/pages/login/login'
          });
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(res.data?.detail || `Request failed with status ${res.statusCode}`));
        }
      },
      fail: (err) => {
        console.error(`API ${options.method || 'GET'} ${options.url} failed:`, err);
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
  }
};

// Chat APIs
const chat = {
  /**
   * Send message and get AI response
   */
  sendMessage(messageData, options = {}) {
    return request({
      url: '/chat/send',
      method: 'POST',
      data: messageData,
      skipAuth: options.skipAuth || false
    });
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