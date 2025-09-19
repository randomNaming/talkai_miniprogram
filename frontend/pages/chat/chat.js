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

    // Use proper authenticated chat API
    this.sendAuthenticatedMessage(text);
  },

  /**
   * Send message using authenticated chat API with progressive display (like talkai_py MessageProcessingThread)
   */
  sendAuthenticatedMessage: function(text) {
    console.log('Starting progressive chat like talkai_py MessageProcessingThread...');
    
    // Store original message for subsequent calls
    this.currentUserMessage = text;
    
    // Ensure authentication first
    this.ensureAuth().then(() => {
      // STEP 1: Get immediate AI response (like talkai_py ai_response_ready signal)
      console.log('Step 1: Getting immediate AI response...');
      const requestData = {
        message: text,
        include_history: this.data.settings.includeHistory
      };
      
      return api.chat.sendMessage(requestData);
    }).then(result => {
      console.log('Step 1 completed: AI response received');
      
      // Immediately show AI response
      this.showImmediateAIResponse(result);
      
      // STEP 2: Get grammar check after delay (like talkai_py correction_ready signal)  
      setTimeout(() => {
        this.getGrammarCheckSeparately(text);
      }, 800); // 0.8s delay like talkai_py
      
      // STEP 3: Get vocabulary suggestions after delay (like talkai_py vocabulary_ready signal)
      setTimeout(() => {
        this.getVocabSuggestionsSeparately(text, result.response);
      }, 1600); // 1.6s total delay like talkai_py
      
    }).catch(err => {
      console.error('Chat API failed:', err);
      
      // Fallback to dict AI endpoint for development/testing
      console.log('Falling back to dict AI endpoint...');
      this.sendFallbackMessage(text);
    });
  },

  /**
   * Show immediate AI response (like talkai_py ai_response_ready signal)
   */
  showImmediateAIResponse: function(result) {
    console.log('Showing immediate AI response...');

    const aiMessage = {
      id: Date.now() + 1,
      type: 'ai',
      content: result.response,
      time: this.formatTime(new Date()),
      // Initially no grammar check and vocab suggestions
      grammar_check: null,
      suggested_vocab: []
    };

    this.setData({
      messages: [...this.data.messages, aiMessage],
      isLoading: false
    });
    this.scrollToBottom();
    
    // Store current AI message ID for later updates
    this.currentAIMessageId = aiMessage.id;
  },

  /**
   * Get grammar check separately (like talkai_py correction_ready signal)
   */
  getGrammarCheckSeparately: function(userText) {
    console.log('Step 2: Getting grammar check separately...');
    
    const config = envConfig.getConfig();
    const apiUrl = `${config.API_BASE_URL}/chat/grammar-check`;
    
    wx.request({
      url: apiUrl,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${wx.getStorageSync('talkai_token')}`
      },
      data: {
        text: userText
      },
      success: (res) => {
        console.log('Step 2 completed: Grammar check received', res.statusCode);
        // 根据talkai_py ui.py on_correction_ready逻辑:
        // 只有当has_error=true时才显示语法纠错
        if (res.statusCode === 200 && res.data.has_error) {
          this.updateAIMessageWithGrammarCheck(res.data);
        } else {
          console.log('No grammar errors found, not showing correction');
        }
      },
      fail: (err) => {
        console.error('Grammar check request failed:', err);
      }
    });
  },

  /**
   * Get vocabulary suggestions separately (like talkai_py vocabulary_ready signal)
   */
  getVocabSuggestionsSeparately: function(userText, aiResponse) {
    console.log('Step 3: Getting vocabulary suggestions separately...');
    
    const config = envConfig.getConfig();
    const apiUrl = `${config.API_BASE_URL}/chat/vocabulary-suggestions`;
    
    wx.request({
      url: apiUrl,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${wx.getStorageSync('talkai_token')}`
      },
      data: {
        user_input: userText,
        ai_response: aiResponse
      },
      success: (res) => {
        console.log('Step 3 completed: Vocabulary suggestions received', res.statusCode);
        if (res.statusCode === 200 && res.data.suggested_vocab && res.data.suggested_vocab.length > 0) {
          this.updateAIMessageWithVocabSuggestions(res.data.suggested_vocab);
        }
        
        // Save cached messages after all processing is complete
        this.saveCachedMessages();
      },
      fail: (err) => {
        console.error('Vocabulary suggestions request failed:', err);
      }
    });
  },

  /**
   * Update AI message with grammar check results
   */
  updateAIMessageWithGrammarCheck: function(grammarCheck) {
    console.log('Updating AI message with grammar check...');
    
    const messages = [...this.data.messages];
    const lastMessage = messages.find(msg => msg.id === this.currentAIMessageId);
    
    if (lastMessage) {
      lastMessage.grammar_check = grammarCheck;
      this.enhanceGrammarCorrection(lastMessage);
      
      this.setData({
        messages: messages
      });
      this.scrollToBottom();
    }
  },

  /**
   * Update AI message with vocabulary suggestions
   */
  updateAIMessageWithVocabSuggestions: function(suggestedVocab) {
    console.log('Updating AI message with vocabulary suggestions...');
    
    const messages = [...this.data.messages];
    const lastMessage = messages.find(msg => msg.id === this.currentAIMessageId);
    
    if (lastMessage) {
      lastMessage.suggested_vocab = suggestedVocab;
      
      this.setData({
        messages: messages
      });
      this.scrollToBottom();
    }
  },

  /**
   * Handle API response with progressive display like talkai_py MessageProcessingThread
   */
  handleProgressiveResponse: function(result) {
    // This method is now replaced by the separate methods above
    // Keeping it for fallback compatibility
    console.log('Using fallback progressive response display...');
    this.showImmediateAIResponse(result);
  },

  /**
   * Fallback method using dict AI endpoint (for development/testing)
   */
  sendFallbackMessage: function(text) {
    const config = envConfig.getConfig();
    const apiUrl = `${config.API_BASE_URL}/dict/ai-chat`;
    
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
        console.log('Fallback dict AI response:', res.statusCode, res.data);
        if (res.statusCode === 200) {
          // Use progressive display for fallback too
          this.handleProgressiveResponse(res.data);
        } else {
          this.handleApiError(new Error(res.data?.detail || 'Request failed'));
        }
      },
      fail: (err) => {
        console.error('Fallback request failed:', err);
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
    
    // Process grammar correction with UI enhancements (based on talkai_py ui.py)
    // 根据talkai_py ui.py on_correction_ready逻辑:
    // 只有当has_error=true时才显示语法纠错
    if (result.grammar_check && result.grammar_check.has_error) {
      this.enhanceGrammarCorrection(aiMessage);
    }

    this.setData({
      messages: [...this.data.messages, aiMessage],
      isLoading: false
    });
    
    // 词汇推荐已经包含在aiMessage中，不需要再次添加系统消息

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

    console.log('手动添加词汇到后端:', vocab.corrected);

    // 调用后端API添加词汇
    api.addVocabWordToBackend(vocab.corrected, 'chat_correction')
      .then(result => {
        console.log('词汇添加结果:', result);
        
        // 检查API返回是否成功 - 修复判断逻辑
        if (!result) {
          throw new Error('No response from vocabulary API');
        }
        
        if (result.success === false) {
          throw new Error(result.message || 'Failed to add word to vocabulary');
        }
        
        // 根据操作类型显示不同的提示
        let toastTitle = '已添加到词汇表';
        if (result.action === 'updated' && result.is_level_vocab) {
          toastTitle = '等级词汇已更新';
          
          // 标记需要在词汇页面突出显示这个等级词汇
          app.globalData.highlightedLevelWord = {
            word: result.word,
            timestamp: Date.now(),
            source: result.original_source,
            level: result.original_level
          };
        } else if (result.action === 'updated') {
          toastTitle = '词汇已更新';
        }
        
        wx.showToast({
          title: toastTitle,
          icon: 'success',
          duration: 1500
        });
        
        // 设置需要刷新词汇页面的标记
        app.globalData.needRefreshVocab = true;
        
        // 触发词汇数据同步刷新
        if (app.globalData.vocabSyncManager) {
          setTimeout(() => {
            app.globalData.vocabSyncManager.forceSync();
          }, 500);
        }
      })
      .catch(error => {
        console.error('词汇添加失败:', error);
        
        wx.showToast({
          title: '添加失败，请重试',
          icon: 'none',
          duration: 1500
        });
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
   * Enhance grammar correction with UI patterns from talkai_py
   */
  enhanceGrammarCorrection: function(message) {
    const grammarCheck = message.grammar_check;
    if (!grammarCheck || !grammarCheck.has_error) return;
    
    // Calculate confidence level (based on talkai_py logic)
    const confidenceLevel = this.calculateCorrectionConfidence(grammarCheck.vocab_to_learn);
    message.confidence_level = confidenceLevel;
    message.confidence_indicator = this.getConfidenceIndicator(confidenceLevel);
    
    // Get explanation if available (复制talkai_py add_corrected_input的explanation处理)
    let explanation = '';
    
    // 首先检查主要的explanation字段
    if (grammarCheck.explanation && grammarCheck.explanation.trim()) {
      explanation = grammarCheck.explanation.trim();
    } else if (grammarCheck.vocab_to_learn && grammarCheck.vocab_to_learn.length > 0) {
      // 如果没有主要explanation，从词汇项中收集
      const explanations = grammarCheck.vocab_to_learn
        .filter(item => item.explanation && item.explanation.trim())
        .map(item => item.explanation.trim());
      if (explanations.length > 0) {
        explanation = explanations.join('; ');
      }
    }
    
    if (explanation) {
      message.correction_explanation = explanation;
    }
    
    // Create highlighted correction (simplified for WeChat rich-text)
    message.highlighted_correction = this.createHighlightedCorrection(
      grammarCheck.corrected_input, 
      grammarCheck.vocab_to_learn
    );
  },
  
  /**
   * Calculate correction confidence (from talkai_py ui.py)
   */
  calculateCorrectionConfidence: function(vocabToLearn) {
    if (!vocabToLearn || vocabToLearn.length === 0) {
      return 'high';
    }
    
    const highConfidenceTypes = ['translation', 'vocabulary'];
    const lowConfidenceTypes = ['grammar', 'collocation'];
    
    let highConfidenceCount = 0;
    let lowConfidenceCount = 0;
    
    vocabToLearn.forEach(item => {
      const errorType = item.error_type || 'vocabulary';
      if (highConfidenceTypes.includes(errorType)) {
        highConfidenceCount += 2;
      } else if (lowConfidenceTypes.includes(errorType)) {
        lowConfidenceCount += 1;
      }
    });
    
    return highConfidenceCount >= lowConfidenceCount ? 'high' : 'medium';
  },
  
  /**
   * Get confidence indicator (from talkai_py ui.py)
   */
  getConfidenceIndicator: function(confidenceLevel) {
    switch (confidenceLevel) {
      case 'high':
        return '✓';  // Green checkmark
      case 'medium':
        return '⚠';  // Warning sign
      default:
        return '?';   // Question mark
    }
  },
  
  /**
   * Create highlighted correction text for rich-text display (based on talkai_py add_corrected_input)
   */
  createHighlightedCorrection: function(correctedInput, vocabToLearn) {
    if (!correctedInput) {
      return correctedInput;
    }
    
    // 先为整个文本设置正确部分的颜色（绿色）- 复制talkai_py逻辑
    let highlighted_input = `<span style="color: #27ae60;">${correctedInput}</span>`;
    
    // 如果有值得学习的单词，使用粗体和不同颜色标记它们 - 复制talkai_py逻辑
    if (vocabToLearn && vocabToLearn.length > 0) {
      vocabToLearn.forEach(wordPair => {
        const corrected = wordPair.corrected;
        const original = wordPair.original;
        const errorType = wordPair.error_type || "vocabulary";
        
        if (corrected && (corrected !== original)) {
          // 使用智能匹配查找词汇变形 (复制talkai_py find_word_variants_in_text逻辑)
          const variantWord = this.findWordVariantsInText(corrected, correctedInput);
          if (variantWord) {
            // 根据错误类型使用不同颜色 (复制talkai_py get_error_type_color逻辑)
            const color = this.getErrorTypeColor(errorType);
            const pattern = new RegExp('\\b' + this.escapeRegExp(variantWord) + '\\b', 'gi');
            const replacement = `<b style="color: ${color};">${variantWord}</b>`;
            highlighted_input = highlighted_input.replace(pattern, replacement);
          }
        }
      });
    }
    
    return highlighted_input;
  },
  
  /**
   * 智能查找目标词汇在文本中的变形形式 (复制talkai_py find_word_variants_in_text函数)
   */
  findWordVariantsInText: function(targetWord, text) {
    // 如果目标词是多词短语，不进行变形匹配，避免误匹配
    if (targetWord.split(' ').length > 1) {
      // 对于多词短语，只进行精确匹配
      const exactPattern = new RegExp('\\b' + this.escapeRegExp(targetWord) + '\\b', 'i');
      if (exactPattern.test(text)) {
        return targetWord;
      } else {
        return null;
      }
    }
    
    // 常见的后缀变形
    const commonSuffixes = ['s', 'es', 'ed', 'ing', 'er', 'est', 'ly', 'tion', 'sion', 'ness', 'ment'];
    
    // 1. 精确匹配（优先级最高）
    const exactPattern = new RegExp('\\b' + this.escapeRegExp(targetWord) + '\\b', 'i');
    if (exactPattern.test(text)) {
      return targetWord;
    }
    
    // 2. 查找文本中是否有以目标词汇为词根的变形（仅限单词）
    const wordsInText = text.toLowerCase().match(/\b\w+\b/g) || [];
    const targetLower = targetWord.toLowerCase();
    
    for (let word of wordsInText) {
      // 检查文本中的词是否以目标词开头（目标词是词根）
      if (word.startsWith(targetLower) && word.length > targetLower.length) {
        const suffix = word.slice(targetLower.length);
        // 确保后缀是纯字母，不包含空格或标点
        if (/^[a-z]+$/i.test(suffix) && (commonSuffixes.includes(suffix) || suffix.length <= 3)) {
          return word;
        }
      }
      
      // 检查目标词是否以文本中的词开头（文本中的词是词根）
      if (targetLower.startsWith(word) && targetLower.length > word.length) {
        const suffix = targetLower.slice(word.length);
        // 确保后缀是纯字母，不包含空格或标点
        if (/^[a-z]+$/i.test(suffix) && (commonSuffixes.includes(suffix) || suffix.length <= 3)) {
          return word;
        }
      }
    }
    
    // 3. 包含匹配（最后手段，处理不规则变形，仅限单词）
    for (let word of wordsInText) {
      // 双向包含检查，但要求有足够的重叠
      const minLen = Math.min(word.length, targetLower.length);
      if (minLen >= 3) {  // 至少3个字符才考虑包含匹配
        if ((targetLower.includes(word) && targetLower.length >= minLen * 0.7) ||
           (word.includes(targetLower) && word.length >= minLen * 0.7)) {
          return word;
        }
      }
    }
    
    return null;
  },
  
  /**
   * Get color for different error types (from talkai_py ui.py)
   */
  getErrorTypeColor: function(errorType) {
    const colorMap = {
      'translation': '#e74c3c',   // Red for translations
      'vocabulary': '#f39c12',    // Orange for vocabulary
      'collocation': '#9b59b6',   // Purple for collocations
      'grammar': '#2980b9'        // Blue for grammar
    };
    return colorMap[errorType] || '#e74c3c';
  },
  
  /**
   * Escape special regex characters
   */
  escapeRegExp: function(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  },
  
  /**
   * Add vocabulary suggestion as system message (like talkai_py)
   */
  addVocabSuggestionMessage: function(suggestedVocab) {
    const wordList = suggestedVocab.map(word => `<b>${word}</b>`).join(', ');
    
    const suggestionMessage = {
      id: Date.now() + 2,
      type: 'system',
      content: `推荐词汇练习: ${wordList}`,
      time: this.formatTime(new Date()),
      suggested_vocab: suggestedVocab,
      isVocabSuggestion: true
    };
    
    this.setData({
      messages: [...this.data.messages, suggestionMessage]
    });
  },
  
  /**
   * Handle vocabulary suggestion tap
   */
  onVocabSuggestionTap: function(e) {
    const word = e.currentTarget.dataset.word;
    if (word) {
      // Navigate to dictionary page to look up the word
      wx.navigateTo({
        url: `/pages/dict/dict?word=${encodeURIComponent(word)}`
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