// pages/chat/chat.js
const app = getApp();
const api = require('../../services/api');
const storage = require('../../utils/storage');
const envConfig = require('../../config/env');

Page({
  data: {
    messages: [],
    inputText: '',
    isLoading: false,
    isOnline: true,
    scrollTop: 0,
    scrollToView: '',
    welcomeMessage: 'Hello! I\'m your English learning assistant. Let\'s have a conversation in English! What would you like to talk about today?',
    welcomeTime: '',
    userAvatar: '',
    showSettings: false,
    showQuickActions: true,
    settings: {
      showGrammarCorrection: true,
      includeHistory: true,
      showQuickActions: true
    }
  },

  onLoad: function (options) {
    console.log('Chat page loaded');
    
    // Initialize page directly
    this.initializePage();
    
    // Start background token setup (non-blocking)
    this.setupBackgroundAuth();
  },

  onShow: function () {
    // Update online status
    this.checkOnlineStatus();
    
    // Load messages from cache
    this.loadCachedMessages();
  },

  onHide: function () {
    // Save messages to cache
    this.saveCachedMessages();
  },

  /**
   * Initialize page data and settings
   */
  initializePage: function() {
    const userInfo = app.globalData.userInfo;
    const settings = storage.getAppSettings();
    
    this.setData({
      userAvatar: userInfo?.avatar_url || '/images/default_avatar.png',
      welcomeTime: this.formatTime(new Date()),
      settings: {
        ...this.data.settings,
        ...settings
      },
      showQuickActions: settings.showQuickActions !== false
    });

    // Get initial greeting from server
    this.getInitialGreeting();
  },

  /**
   * Setup background authentication (non-blocking)
   */
  setupBackgroundAuth: function() {
    console.log('Setting up background auth...');
    
    // Check for existing token
    const token = wx.getStorageSync('talkai_token');
    if (token) {
      // Try to verify existing token quietly
      api.auth.verifyToken().then(result => {
        console.log('Token verified successfully');
        if (!app.globalData.isLoggedIn) {
          // Get user profile and login
          return api.user.getProfile();
        }
      }).then(userInfo => {
        if (userInfo) {
          app.login(userInfo);
          console.log('Background auth completed');
        }
      }).catch(err => {
        console.log('Token verification failed, will create new session on first API call');
        wx.removeStorageSync('talkai_token');
      });
    } else {
      console.log('No existing token, will create session on first API call');
    }
  },

  /**
   * Check if running in development environment
   */
  isDevelopment: function() {
    try {
      // Check if running in WeChat Developer Tools
      const accountInfo = wx.getAccountInfoSync();
      const envVersion = accountInfo.miniProgram.envVersion;
      
      console.log('Current environment version:', envVersion);
      
      // Use development mode only for WeChat Developer Tools simulator
      // Real device preview should use production flow
      return envVersion === 'develop' && this.isSimulator();
    } catch (error) {
      console.warn('Failed to get account info, assuming production:', error);
      return false; // Default to production if detection fails
    }
  },

  /**
   * Check if running in simulator vs real device
   */
  isSimulator: function() {
    try {
      const systemInfo = wx.getSystemInfoSync();
      // Check if running in simulator (WeChat Developer Tools)
      return systemInfo.platform === 'devtools';
    } catch (error) {
      return false;
    }
  },

  /**
   * Perform login with js_code and optional user info
   */
  performLogin: function(jsCode, userInfo, resolve, reject) {
    const loginData = { 
      js_code: jsCode,
      nickname: userInfo?.nickName,
      avatar_url: userInfo?.avatarUrl
    };
    
    console.log('Calling backend login API...');
    api.auth.wechatLogin(loginData).then(result => {
      console.log('Backend login successful, token received:', !!result.access_token);
      
      // Create user info from login result
      const completeUserInfo = {
        id: result.user_id,
        nickname: loginData.nickname || 'User',
        avatar_url: loginData.avatar_url || '/images/default_avatar.png',
        is_new_user: result.is_new_user
      };
      
      console.log('User logged in:', completeUserInfo.nickname || completeUserInfo.id);
      
      // Save login state
      app.login(completeUserInfo);
      console.log('Authentication completed successfully');
      resolve();
    }).catch(err => {
      console.error('Authentication failed:', err.message || err);
      reject(err);
    });
  },

  /**
   * Ensure authentication before API calls
   */
  ensureAuth: function() {
    return new Promise((resolve, reject) => {
      console.log('ensureAuth called, isLoggedIn:', app.globalData.isLoggedIn);
      
      // If already logged in, resolve immediately
      if (app.globalData.isLoggedIn && storage.getToken()) {
        console.log('Already authenticated, proceeding...');
        resolve();
        return;
      }
      
      console.log('Need to authenticate, starting WeChat login...');
      
      // Always try real WeChat login
      wx.login({
        success: (loginRes) => {
          console.log('wx.login success, code:', loginRes.code ? 'received' : 'missing');
          
          if (loginRes.code) {
            // Try to get user profile info (optional)
            wx.getUserProfile({
              desc: '用于完善个人资料',
              success: (profileRes) => {
                this.performLogin(loginRes.code, profileRes.userInfo, resolve, reject);
              },
              fail: () => {
                // If getUserProfile fails, login without user info
                this.performLogin(loginRes.code, null, resolve, reject);
              }
            });
          } else {
            console.error('wx.login failed: no code received');
            reject(new Error('Failed to get WeChat code'));
          }
        },
        fail: (err) => {
          console.error('wx.login API failed:', err);
          reject(new Error('WeChat login API failed: ' + (err.errMsg || 'unknown')));
        }
      });
    });
  },

  /**
   * Development login - create mock session without WeChat API
   */
  mockLogin: function() {
    return new Promise((resolve, reject) => {
      console.log('Development mode: creating mock authentication session');
      
      // Create mock user session directly
      const mockUser = {
        id: 'dev_user_' + Date.now(),
        nickname: 'Dev User',
        avatar_url: '/images/default_avatar.png',
        is_new_user: false
      };
      
      // Create mock token
      const mockToken = 'dev_token_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      
      // Save mock token
      storage.setToken(mockToken);
      
      // Save login state
      app.login(mockUser);
      
      console.log('Development authentication completed with mock session');
      resolve();
    });
  },

  /**
   * Get mock AI response for development
   */
  getMockResponse: function(userMessage) {
    return new Promise((resolve) => {
      console.log('Generating mock response for:', userMessage);
      
      // Simulate network delay
      setTimeout(() => {
        const mockResponses = [
          "That's a great question! In development mode, I'm providing mock responses to help you test the interface.",
          "I understand what you're saying. This is a simulated response since we're in development environment.",
          "Great! Your message has been received. This mock response shows that the chat interface is working properly.",
          "Thanks for testing! In the actual app, I would provide personalized English learning assistance.",
          "Perfect! The chat functionality is working. This response is generated locally for development testing."
        ];
        
        const randomResponse = mockResponses[Math.floor(Math.random() * mockResponses.length)];
        
        const mockResult = {
          response: randomResponse,
          grammar_check: userMessage.length > 10 ? {
            has_errors: false,
            corrected_text: userMessage,
            suggestions: []
          } : null,
          suggested_vocab: []
        };
        
        resolve(mockResult);
      }, 800); // Simulate API delay
    });
  },

  /**
   * Get initial greeting from server
   */
  getInitialGreeting: function() {
    api.chat.getGreeting().then(result => {
      if (result.message) {
        this.setData({
          welcomeMessage: result.message,
          welcomeTime: this.formatTime(new Date(result.timestamp))
        });
      }
    }).catch(err => {
      console.warn('Failed to get greeting:', err);
    });
  },

  /**
   * Check online status
   */
  checkOnlineStatus: function() {
    wx.getNetworkType({
      success: (res) => {
        this.setData({
          isOnline: res.networkType !== 'none'
        });
      }
    });
  },

  /**
   * Load cached messages
   */
  loadCachedMessages: function() {
    const cachedMessages = storage.getConversationHistory();
    if (cachedMessages && cachedMessages.length > 0) {
      this.setData({
        messages: cachedMessages
      });
      this.scrollToBottom();
    }
  },

  /**
   * Save messages to cache
   */
  saveCachedMessages: function() {
    storage.setConversationHistory(this.data.messages);
  },

  /**
   * Handle input change
   */
  onInputChange: function(e) {
    this.setData({
      inputText: e.detail.value
    });
  },

  /**
   * Send message
   */
  onSendMessage: function() {
    const text = this.data.inputText.trim();
    
    if (!text || this.data.isLoading) {
      return;
    }

    if (!this.data.isOnline) {
      wx.showToast({
        title: '请检查网络连接',
        icon: 'none'
      });
      return;
    }

    // Add user message to UI
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: text,
      time: this.formatTime(new Date())
    };

    this.setData({
      messages: [...this.data.messages, userMessage],
      inputText: '',
      isLoading: true
    });

    this.scrollToBottom();

    // Send message using dict AI chat endpoint (no authentication required)
    console.log('Sending chat message via dict AI endpoint...');
    
    // Get current environment config for API URL
    const config = envConfig.getConfig();
    const apiUrl = `${config.API_BASE_URL}/dict/ai-chat`;
    console.log('Using API URL:', apiUrl);
    
    // Use the dict AI chat endpoint that works like /dict/query
    wx.request({
      url: apiUrl,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        message: text
      },
      success: (res) => {
        console.log('Dict AI chat response:', res.statusCode, res.data);
        if (res.statusCode === 200) {
          this.handleApiResponse(res.data);
        } else {
          this.handleApiError(new Error(res.data?.detail || 'Request failed'));
        }
      },
      fail: (err) => {
        console.error('Dict AI chat failed:', err);
        this.handleApiError(new Error('Network request failed'));
      }
    });
  },

  /**
   * Handle successful API response
   */
  handleApiResponse: function(result) {
    console.log('Chat response received:', result);

    // Add AI response
    const aiMessage = {
      id: Date.now() + 1,
      type: 'ai',
      content: result.response,
      time: this.formatTime(new Date()),
      grammar_check: result.grammar_check,
      suggested_vocab: result.suggested_vocab || []
    };

    this.setData({
      messages: [...this.data.messages, aiMessage],
      isLoading: false
    });

    this.scrollToBottom();
    this.saveCachedMessages();
  },

  /**
   * Handle API error
   */
  handleApiError: function(err) {
    console.error('Chat request failed:', err);
    
    this.setData({
      isLoading: false
    });

    let errorContent = 'Sorry, I encountered an error. Please try again.';
    
    // Provide specific error messages
    if (err.message.includes('Not authenticated')) {
      errorContent = 'Authentication failed. Please check your network connection and try again.';
    } else if (err.message.includes('Network request failed')) {
      errorContent = 'Network error. Please check your internet connection.';
    } else if (err.message.includes('timeout')) {
      errorContent = 'Request timeout. Please try again.';
    }

    // Show error message
    const errorMessage = {
      id: Date.now() + 1,
      type: 'ai',
      content: errorContent,
      time: this.formatTime(new Date()),
      isError: true
    };

    this.setData({
      messages: [...this.data.messages, errorMessage]
    });

    this.scrollToBottom();
  },

  /**
   * Handle quick action buttons
   */
  onQuickAction: function(e) {
    const action = e.currentTarget.dataset.action;
    let message = '';

    switch (action) {
      case 'greeting':
        message = 'Hello! How are you doing today?';
        break;
      case 'introduce':
        message = 'Let me introduce myself.';
        break;
      case 'help':
        message = 'Can you help me practice English conversation?';
        break;
      case 'topic':
        message = 'Can we talk about something else?';
        break;
      default:
        return;
    }

    this.setData({
      inputText: message
    });
  },

  /**
   * Add vocabulary word
   */
  onAddVocab: function(e) {
    const vocab = e.currentTarget.dataset.vocab;
    
    if (!vocab) return;

    // Add to app global vocab list
    const vocabItem = {
      word: vocab.corrected,
      definition: vocab.explanation || '',
      source: 'chat_correction'
    };

    app.addVocabWord(vocabItem);

    wx.showToast({
      title: '已添加到词汇表',
      icon: 'success',
      duration: 1500
    });
  },

  /**
   * Copy message content
   */
  onCopyMessage: function(e) {
    const content = e.currentTarget.dataset.content;
    
    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({
          title: '已复制',
          icon: 'success',
          duration: 1000
        });
      }
    });
  },

  /**
   * Translate message (placeholder)
   */
  onTranslateMessage: function(e) {
    wx.showToast({
      title: '翻译功能开发中',
      icon: 'none',
      duration: 1500
    });
  },

  /**
   * Clear chat history
   */
  onClearChat: function() {
    wx.showModal({
      title: '清空对话',
      content: '确定要清空所有对话记录吗？',
      confirmText: '清空',
      confirmColor: '#DC3545',
      success: (res) => {
        if (res.confirm) {
          this.setData({
            messages: []
          });
          storage.setConversationHistory([]);
          wx.showToast({
            title: '对话已清空',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * Show settings modal
   */
  onShowSettings: function() {
    this.setData({
      showSettings: true
    });
  },

  /**
   * Hide settings modal
   */
  onHideSettings: function() {
    this.setData({
      showSettings: false
    });
  },

  /**
   * Handle setting change
   */
  onSettingChange: function(e) {
    const key = e.currentTarget.dataset.key;
    const value = e.detail.value;
    
    const newSettings = {
      ...this.data.settings,
      [key]: value
    };

    this.setData({
      settings: newSettings,
      showQuickActions: newSettings.showQuickActions
    });

    // Save settings
    storage.setAppSettings(newSettings);
  },

  /**
   * Scroll to bottom
   */
  scrollToBottom: function() {
    if (this.data.messages.length > 0) {
      const lastMessageId = `msg-${this.data.messages[this.data.messages.length - 1].id}`;
      this.setData({
        scrollToView: lastMessageId
      });
    }
  },

  /**
   * Format time
   */
  formatTime: function(date) {
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) { // Less than 1 minute
      return '刚刚';
    } else if (diff < 3600000) { // Less than 1 hour
      return `${Math.floor(diff / 60000)}分钟前`;
    } else if (now.toDateString() === date.toDateString()) { // Same day
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else {
      return date.toLocaleDateString('zh-CN', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
  },

  /**
   * Handle page share
   */
  onShareAppMessage: function() {
    return {
      title: 'TalkAI英语学习 - AI智能对话练习',
      path: '/pages/chat/chat',
      imageUrl: '/images/share_chat.png'
    };
  }
});