// pages/login/login.js
const app = getApp();
const api = require('../../services/api');

Page({
  data: {
    isLogging: false
  },

  onLoad: function (options) {
    console.log('Login page loaded');
    
    // Check if already logged in
    if (app.globalData.isLoggedIn) {
      this.redirectToMain();
      return;
    }
    
    // Start automatic login process
    this.startAutoLogin();
  },

  onShow: function () {
    // Reset logging state
    this.setData({
      isLogging: false
    });
  },

  /**
   * Start automatic login process
   */
  startAutoLogin: function() {
    console.log('Starting automatic login...');
    this.setData({ isLogging: true });

    // First try to login with existing token
    const token = wx.getStorageSync('talkai_token');
    if (token) {
      this.tryTokenLogin();
    } else {
      // No existing token, start fresh login
      this.performFreshLogin();
    }
  },

  /**
   * Try login with existing token
   */
  tryTokenLogin: function() {
    console.log('Trying login with existing token...');

    // Verify existing token
    api.auth.verifyToken().then(result => {
      console.log('Token verification successful');
      
      // Get user profile
      return api.user.getProfile();
    }).then(userInfo => {
      // Login successful
      app.login(userInfo);
      this.redirectToMain();
    }).catch(err => {
      console.log('Token login failed:', err);
      // Clear invalid token and try fresh login
      wx.removeStorageSync('talkai_token');
      this.performFreshLogin();
    });
  },

  /**
   * Perform fresh login without user interaction
   */
  performFreshLogin: function() {
    console.log('Performing fresh automatic login...');

    // Get WeChat login code
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          // Login without user profile (anonymous login)
          this.performLogin(loginRes.code, null);
        } else {
          console.error('Failed to get WeChat login code');
          this.showLoginError('获取微信登录信息失败');
        }
      },
      fail: (err) => {
        console.error('WeChat login failed:', err);
        this.showLoginError('微信登录失败');
      }
    });
  },


  /**
   * Perform login with backend
   */
  performLogin: function(jsCode, userInfo) {
    console.log('Performing login with backend...');
    
    // Create login data with optional userInfo
    const loginData = {
      js_code: jsCode
    };
    
    // Add user info if available
    if (userInfo) {
      loginData.nickname = userInfo.nickName;
      loginData.avatar_url = userInfo.avatarUrl;
    }
    
    api.auth.wechatLogin(loginData).then(result => {
      console.log('Backend login successful:', result);
      
      // Get complete user profile
      return api.user.getProfile();
    }).then(completeUserInfo => {
      console.log('Got user profile:', completeUserInfo);
      
      // Save login state
      app.login(completeUserInfo);
      
      // Show success message
      wx.showToast({
        title: '登录成功',
        icon: 'success',
        duration: 1500
      });
      
      // Sync data after login
      this.syncDataAfterLogin();
      
      // Navigate to main page
      setTimeout(() => {
        this.redirectToMain();
      }, 1500);
      
    }).catch(err => {
      console.error('Login failed:', err);
      this.showLoginError('登录失败，请重试');
    });
  },

  /**
   * Sync data after successful login
   */
  syncDataAfterLogin: function() {
    console.log('Syncing data after login...');
    
    app.syncData().then(result => {
      console.log('Data sync completed:', result);
    }).catch(err => {
      console.warn('Data sync failed:', err);
      // Don't block login for sync failures
    });
  },

  /**
   * Show login error message
   */
  showLoginError: function(message) {
    this.setData({ isLogging: false });
    
    wx.showModal({
      title: '登录失败',
      content: message,
      showCancel: false,
      confirmText: '确定',
      confirmColor: '#2C5AA0'
    });
  },

  /**
   * Redirect to main page
   */
  redirectToMain: function() {
    wx.switchTab({
      url: '/pages/chat/chat'
    });
  },

  /**
   * Handle privacy policy tap
   */
  onPrivacyPolicyTap: function() {
    wx.showModal({
      title: '隐私政策',
      content: '我们重视您的隐私，仅收集必要的用户信息用于提供服务。您的学习数据将安全存储并仅用于改善学习体验。',
      showCancel: false,
      confirmText: '我知道了',
      confirmColor: '#2C5AA0'
    });
  },

  /**
   * Handle user agreement tap
   */
  onUserAgreementTap: function() {
    wx.showModal({
      title: '用户协议',
      content: '欢迎使用TalkAI英语学习小程序。请遵守使用规范，合理使用AI对话功能。我们致力于为您提供优质的英语学习服务。',
      showCancel: false,
      confirmText: '我同意',
      confirmColor: '#2C5AA0'
    });
  }
});