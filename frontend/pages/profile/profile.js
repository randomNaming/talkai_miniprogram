// pages/profile/profile.js
const app = getApp();
const api = require('../../services/api');

Page({
  data: {
    userInfo: {},
    stats: {
      total_usage_time: 0,
      chat_history_count: 0,
      vocab_count: 0,
      days_since_registration: 0
    }
  },

  onLoad: function (options) {
    if (!app.globalData.isLoggedIn) {
      wx.reLaunch({
        url: '/pages/login/login'
      });
      return;
    }
    
    this.loadUserData();
  },

  onShow: function () {
    this.loadUserData();
  },

  loadUserData: function() {
    this.setData({
      userInfo: app.globalData.userInfo || {}
    });

    // Get user statistics
    api.user.getStats().then(stats => {
      this.setData({ stats });
    }).catch(err => {
      console.error('Failed to load stats:', err);
    });
  },

  onSync: function() {
    wx.showLoading({ title: '同步中...' });
    
    app.syncData().then(() => {
      wx.hideLoading();
      wx.showToast({
        title: '同步成功',
        icon: 'success'
      });
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({
        title: '同步失败',
        icon: 'none'
      });
    });
  },

  onLogout: function() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmColor: '#DC3545',
      success: (res) => {
        if (res.confirm) {
          app.logout();
        }
      }
    });
  }
});