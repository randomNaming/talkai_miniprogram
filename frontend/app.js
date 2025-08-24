// TalkAI Mini Program Entry Point
const api = require('./services/api');
const storage = require('./utils/storage');

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
      lastSyncTime: null
    };
    
    // Check login status
    this.checkLoginStatus();
    
    // Initialize services
    this.initServices();
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