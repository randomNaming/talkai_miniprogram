// TalkAI Mini Program Entry Point
const api = require('./services/api');
const storage = require('./utils/storage');
const { vocabSyncManager } = require('./services/vocab-sync');

App({
  onLaunch: function () {
    console.log('TalkAI Mini Program Launched');
    
    // Handle unhandled promise rejections
    this.setupErrorHandlers();
    
    // Initialize app data
    this.globalData = {
      userInfo: null,
      token: null,
      baseUrl: 'https://api.jimingge.net/api/v1',
      isLoggedIn: false,
      currentConversation: [],
      vocabList: [],
      vocabStats: null,
      lastSyncTime: null,
      vocabSyncManager: vocabSyncManager,
      needRefreshVocab: false
    };
    
    // Check login status
    this.checkLoginStatus();
    
    // Initialize services
    this.initServices();
    
    // 暂时完全禁用词汇同步初始化，避免循环调用问题
    console.log('[App] 暂时禁用词汇同步初始化');
    
    // Skip sync initialization in development
    // const isDevelopment = wx.getSystemInfoSync && wx.getSystemInfoSync().platform === 'devtools';
    // if (!isDevelopment) {
    //   this.checkAuthAndInitSync();
    // } else {
    //   console.log('[App] 开发环境：跳过词汇同步初始化');
    // }
  },

  setupErrorHandlers: function() {
    // Handle file system errors (like ad file reading errors)
    wx.onError && wx.onError(function(err) {
      // Ignore ad-related file errors
      if (err && err.indexOf && err.indexOf('interstitialAdExtInfo.txt') !== -1) {
        console.warn('Ignoring ad file error:', err);
        return;
      }
      console.error('Global error:', err);
    });
  },

  onShow: function () {
    // App is brought to foreground
    console.log('App shown');
    
    // 完全禁用应用恢复时的词汇同步，避免循环调用
    // if (this.globalData.vocabSyncManager) {
    //   this.globalData.vocabSyncManager.syncOnAppResume();
    // }
  },

  onHide: function () {
    // App is sent to background
    console.log('App hidden');
    
    // Update usage time when app goes to background
    this.updateUsageTime();
  },

  // Check if user is logged in
  checkLoginStatus: function() {
    const token = storage.getToken();
    const userInfo = storage.getUserInfo();
    
    if (token && userInfo) {
      this.globalData.token = token;
      this.globalData.userInfo = userInfo;
      this.globalData.isLoggedIn = true;
    }
  },

  // Initialize app services
  initServices: function() {
    // Load cached vocabulary
    this.loadCachedVocab();
    
    // Load conversation history
    this.loadConversationHistory();
  },

  // Check authentication and initialize sync
  checkAuthAndInitSync: function() {
    const storage = require('./utils/storage');
    const api = require('./services/api');
    
    const token = storage.getToken();
    
    if (!token) {
      console.log('[App] No token found, performing login first');
      this.performAutoLogin().then(() => {
        this.initVocabSync();
      }).catch(err => {
        console.error('[App] Auto login failed, skipping sync init:', err);
      });
    } else {
      // Verify token validity
      console.log('[App] Verifying existing token');
      api.auth.verifyToken().then(() => {
        console.log('[App] Token valid, initializing sync');
        this.initVocabSync();
      }).catch(err => {
        console.log('[App] Token invalid, performing re-login');
        storage.setToken(''); // Clear invalid token
        this.performAutoLogin().then(() => {
          this.initVocabSync();
        }).catch(loginErr => {
          console.error('[App] Re-login failed, skipping sync init:', loginErr);
        });
      });
    }
  },

  // Perform automatic login
  performAutoLogin: function() {
    const api = require('./services/api');
    
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (loginRes.code) {
            api.auth.wechatLogin({
              js_code: loginRes.code
            }).then(result => {
              return api.user.getProfile();
            }).then(userInfo => {
              this.login(userInfo);
              resolve();
            }).catch(reject);
          } else {
            reject(new Error('Failed to get WeChat login code'));
          }
        },
        fail: reject
      });
    });
  },

  // Initialize vocabulary sync manager
  initVocabSync: function() {
    try {
      console.log('Initializing vocabulary sync manager');
      
      // Initialize the sync manager
      this.globalData.vocabSyncManager.init();
      
      // Set up event listeners for vocab sync
      this.setupVocabSyncEventListeners();
      
    } catch (error) {
      console.error('Failed to initialize vocabulary sync:', error);
    }
  },

  // Set up event listeners for vocabulary sync
  setupVocabSyncEventListeners: function() {
    // Store reference to app instance
    const app = this;
    
    // Custom event emitter for vocab sync events
    this.emitVocabSyncEvent = function(eventData) {
      console.log('VocabSync Event:', eventData);
      
      // Handle different sync events
      switch (eventData.type) {
        case 'sync_success':
          if (eventData.data && eventData.data.vocabulary) {
            // Update pages that are currently showing vocab data
            app.refreshVocabPages(eventData.data);
          }
          break;
          
        case 'sync_error':
          console.error('Vocabulary sync error:', eventData.error);
          break;
      }
    };
  },

  // Refresh pages that display vocabulary data (完全禁用避免循环调用)
  refreshVocabPages: function(vocabData) {
    console.log('[App] refreshVocabPages 已禁用，避免循环调用');
    return;
    
    // try {
    //   // Get current pages stack
    //   const pages = getCurrentPages();
    //   const currentPage = pages[pages.length - 1];
    //   
    //   // Refresh vocab page if it's currently active
    //   if (currentPage && currentPage.route === 'pages/vocab/vocab') {
    //     if (typeof currentPage.loadVocabList === 'function') {
    //       currentPage.loadVocabList();
    //     }
    //   }
    //   
    //   console.log('Vocabulary pages refreshed with new data');
    // } catch (error) {
    //   console.error('Failed to refresh vocabulary pages:', error);
    // }
  },

  // Load cached vocabulary from local storage
  loadCachedVocab: function() {
    const cachedVocab = storage.getVocabList();
    if (cachedVocab) {
      this.globalData.vocabList = cachedVocab;
    }
  },

  // Load conversation history from local storage
  loadConversationHistory: function() {
    const history = storage.getConversationHistory();
    if (history) {
      this.globalData.currentConversation = history;
    }
  },

  // Update user usage time
  updateUsageTime: function() {
    if (!this.globalData.isLoggedIn) return;
    
    const sessionStart = this.globalData.sessionStart || Date.now();
    const sessionDuration = Math.floor((Date.now() - sessionStart) / 1000); // seconds
    
    if (sessionDuration > 10) { // Only update if session is longer than 10 seconds
      api.updateUsageTime({
        session_duration: sessionDuration
      }).catch(err => {
        console.warn('Failed to update usage time:', err);
      });
    }
    
    // Reset session start time
    this.globalData.sessionStart = Date.now();
  },

  // Login function
  login: function(userInfo) {
    this.globalData.userInfo = userInfo;
    this.globalData.isLoggedIn = true;
    this.globalData.sessionStart = Date.now();
    
    // Save to local storage
    storage.setUserInfo(userInfo);
    
    console.log('User logged in:', userInfo);
  },

  // Logout function
  logout: function() {
    // Update usage time before logout
    this.updateUsageTime();
    
    // Clear global data
    this.globalData.userInfo = null;
    this.globalData.token = null;
    this.globalData.isLoggedIn = false;
    this.globalData.currentConversation = [];
    this.globalData.vocabList = [];
    
    // Clear local storage
    storage.clearAll();
    
    // Navigate to login page
    wx.reLaunch({
      url: '/pages/login/login'
    });
    
    console.log('User logged out');
  },

  // Add vocabulary word
  addVocabWord: function(word) {
    if (!word || !word.word) return;
    
    // Check if word already exists
    const existingIndex = this.globalData.vocabList.findIndex(item => 
      item.word.toLowerCase() === word.word.toLowerCase()
    );
    
    if (existingIndex >= 0) {
      // Update existing word
      this.globalData.vocabList[existingIndex] = {
        ...this.globalData.vocabList[existingIndex],
        ...word,
        updated_at: new Date().toISOString()
      };
    } else {
      // Add new word
      this.globalData.vocabList.unshift({
        ...word,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        encounter_count: 1,
        correct_count: 0,
        familiarity: 0.0,
        mastery_score: 0.0,
        is_mastered: false
      });
    }
    
    // Save to local storage
    storage.setVocabList(this.globalData.vocabList);
    
    console.log('Vocab word added/updated:', word.word);
    
    // 通知词汇页面有新词汇添加
    this.notifyVocabPageUpdate();
  },

  // 通知词汇页面更新（不触发同步，只刷新显示）
  notifyVocabPageUpdate: function() {
    try {
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      
      // 如果当前就在词汇页面，立即刷新
      if (currentPage && currentPage.route === 'pages/vocab/vocab') {
        if (typeof currentPage.loadRecentVocabulary === 'function') {
          console.log('[App] 当前在词汇页面，立即刷新词汇列表');
          currentPage.loadRecentVocabulary();
        }
      } else {
        // 如果不在词汇页面，设置标记，当切换到词汇页面时刷新
        this.globalData.needRefreshVocab = true;
        console.log('[App] 设置词汇页面刷新标记');
      }
    } catch (error) {
      console.error('Failed to notify vocab page update:', error);
    }
  },

  // Helper method to trigger vocabulary sync after operations
  triggerVocabSync: function(operation = 'unknown') {
    if (this.globalData.vocabSyncManager) {
      this.globalData.vocabSyncManager.refreshAfterVocabOperation(operation);
    }
  },

  // Force vocabulary synchronization
  forceVocabSync: function() {
    if (this.globalData.vocabSyncManager) {
      return this.globalData.vocabSyncManager.forceSync();
    }
    return Promise.resolve(false);
  },

  // Get vocabulary sync status
  getVocabSyncStatus: function() {
    if (this.globalData.vocabSyncManager) {
      return this.globalData.vocabSyncManager.getSyncStatus();
    }
    return null;
  },

  // Sync data with server
  syncData: function() {
    if (!this.globalData.isLoggedIn) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      console.log('Starting data sync...');
      
      // Sync vocabulary
      const lastSyncTime = storage.getLastSyncTime();
      
      api.syncVocabulary({
        vocabulary: this.globalData.vocabList,
        last_sync_time: lastSyncTime
      }).then(result => {
        console.log('Vocabulary sync completed:', result);
        
        // Update local vocabulary with server data
        if (result.vocabulary && result.vocabulary.length > 0) {
          this.globalData.vocabList = result.vocabulary;
          storage.setVocabList(result.vocabulary);
        }
        
        // Update sync time
        storage.setLastSyncTime(result.server_time);
        this.globalData.lastSyncTime = result.server_time;
        
        resolve(result);
      }).catch(err => {
        console.error('Data sync failed:', err);
        reject(err);
      });
    });
  },

  globalData: {} // Will be initialized in onLaunch
});