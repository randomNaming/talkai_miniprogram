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
    },
    vocabStatus: {},
    availableGrades: [],
    showEditModal: false,
    editProfile: {},
    currentGenderIndex: 2, // Default to 'Unspecified'
    currentGradeIndex: 0
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
    // Check authentication before loading data
    this.checkAuthAndLoadData();
  },

  checkAuthAndLoadData: function() {
    if (!app.globalData.isLoggedIn) {
      // Try to re-authenticate
      this.ensureAuthenticated().then(() => {
        this.loadUserData();
      }).catch(err => {
        console.error('Authentication failed:', err);
        // Redirect to login if authentication fails
        wx.reLaunch({
          url: '/pages/login/login'
        });
      });
    } else {
      this.loadUserData();
    }
  },

  ensureAuthenticated: function() {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('talkai_token');
      if (token) {
        // Verify token
        api.auth.verifyToken().then(result => {
          return api.user.getProfile();
        }).then(userInfo => {
          app.login(userInfo);
          resolve();
        }).catch(err => {
          console.error('Token verification failed:', err);
          // Clear invalid token and start fresh login
          wx.removeStorageSync('talkai_token');
          this.performFreshLogin().then(resolve).catch(reject);
        });
      } else {
        this.performFreshLogin().then(resolve).catch(reject);
      }
    });
  },

  performFreshLogin: function() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (loginRes.code) {
            api.auth.wechatLogin({
              js_code: loginRes.code
            }).then(result => {
              return api.user.getProfile();
            }).then(userInfo => {
              app.login(userInfo);
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

  loadUserData: function() {
    this.setData({
      userInfo: app.globalData.userInfo || {}
    });

    // Get user statistics with retry logic
    this.loadWithRetry('stats', () => api.user.getStats());
    
    // Get vocabulary status
    this.loadVocabStatus();
    
    // Get available grades for profile editing
    this.loadAvailableGrades();
  },

  loadWithRetry: function(key, apiCall, maxRetries = 2) {
    let retries = 0;
    const attemptLoad = () => {
      apiCall().then(data => {
        const updateData = {};
        updateData[key] = data;
        this.setData(updateData);
      }).catch(err => {
        console.error(`Failed to load ${key}:`, err);
        if (err.message === 'Not authenticated' && retries < maxRetries) {
          retries++;
          console.log(`Retrying ${key} load (attempt ${retries})`);
          // Wait a bit and retry
          setTimeout(() => {
            this.ensureAuthenticated().then(() => {
              attemptLoad();
            }).catch(authErr => {
              console.error('Re-authentication failed:', authErr);
            });
          }, 1000);
        }
      });
    };
    attemptLoad();
  },
  
  /**
   * Load vocabulary status
   */
  loadVocabStatus: function() {
    this.loadWithRetry('vocabStatus', () => api.user.getVocabStatus());
  },
  
  /**
   * Load available grades
   */
  loadAvailableGrades: function() {
    api.user.getAvailableGrades().then(data => {
      this.setData({ 
        availableGrades: data.grades || [] 
      });
    }).catch(err => {
      console.error('Failed to load available grades:', err);
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

  /**
   * Edit Profile - Following talkai_py UI pattern
   */
  onEditProfile: function() {
    const userInfo = this.data.userInfo;
    const editProfile = {
      nickname: userInfo.nickname || '',
      age: userInfo.age || '',
      gender: userInfo.gender || 'Unspecified',
      grade: userInfo.grade || 'Primary School'
    };
    
    // Calculate picker indices
    const genders = ['Male', 'Female', 'Unspecified'];
    const currentGenderIndex = genders.indexOf(editProfile.gender);
    
    let currentGradeIndex = 0;
    const availableGrades = this.data.availableGrades;
    for (let i = 0; i < availableGrades.length; i++) {
      if (availableGrades[i].grade === editProfile.grade) {
        currentGradeIndex = i;
        break;
      }
    }
    
    this.setData({
      showEditModal: true,
      editProfile: editProfile,
      currentGenderIndex: currentGenderIndex >= 0 ? currentGenderIndex : 2, // Default to 'Unspecified'
      currentGradeIndex: currentGradeIndex
    });
  },
  
  /**
   * Close edit modal
   */
  onCloseEditModal: function() {
    this.setData({
      showEditModal: false,
      editProfile: {}
    });
  },
  
  /**
   * Handle edit form input
   */
  onEditInputChange: function(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    const editProfile = this.data.editProfile;
    
    editProfile[field] = value;
    this.setData({ editProfile });
  },
  
  /**
   * Handle picker change (for gender and grade)
   */
  onPickerChange: function(e) {
    const field = e.currentTarget.dataset.field;
    const value = parseInt(e.detail.value);
    const editProfile = this.data.editProfile;
    
    if (field === 'gender') {
      const genders = ['Male', 'Female', 'Unspecified'];
      editProfile.gender = genders[value];
      this.setData({ 
        editProfile: editProfile,
        currentGenderIndex: value
      });
    } else if (field === 'grade') {
      editProfile.grade = this.data.availableGrades[value].grade;
      this.setData({ 
        editProfile: editProfile,
        currentGradeIndex: value
      });
    }
  },
  
  /**
   * Get current gender index for picker
   */
  getCurrentGenderIndex: function() {
    const genders = ['Male', 'Female', 'Unspecified'];
    const currentGender = this.data.editProfile.gender || 'Unspecified';
    return genders.indexOf(currentGender);
  },
  
  /**
   * Get current grade index for picker
   */
  getCurrentGradeIndex: function() {
    const currentGrade = this.data.editProfile.grade;
    const availableGrades = this.data.availableGrades;
    
    for (let i = 0; i < availableGrades.length; i++) {
      if (availableGrades[i].grade === currentGrade) {
        return i;
      }
    }
    return 0; // Default to first grade if not found
  },
  
  /**
   * Save profile changes
   */
  onSaveProfile: function() {
    const editProfile = this.data.editProfile;
    
    // Validate input
    if (editProfile.age && (isNaN(editProfile.age) || editProfile.age < 1 || editProfile.age > 120)) {
      wx.showToast({
        title: '请输入有效年龄',
        icon: 'none'
      });
      return;
    }
    
    wx.showLoading({ title: '保存中...' });
    
    const updateData = {
      nickname: editProfile.nickname || null,
      age: editProfile.age ? parseInt(editProfile.age) : null,
      gender: editProfile.gender,
      grade: editProfile.grade
    };
    
    api.user.updateProfile(updateData).then(updatedProfile => {
      wx.hideLoading();
      
      // Update global user info
      app.globalData.userInfo = {
        ...app.globalData.userInfo,
        ...updatedProfile
      };
      
      // Update local data
      this.setData({
        userInfo: app.globalData.userInfo,
        showEditModal: false
      });
      
      wx.showToast({
        title: '个人资料已更新',
        icon: 'success'
      });
      
      // Reload data to get updated vocab status
      this.loadUserData();
      
    }).catch(err => {
      wx.hideLoading();
      console.error('Failed to update profile:', err);
      wx.showToast({
        title: '更新失败',
        icon: 'none'
      });
    });
  },
  
  /**
   * Load vocabulary for current grade
   */
  onLoadVocab: function() {
    wx.showLoading({ title: '加载词汇中...' });
    
    api.user.loadVocab().then(result => {
      wx.hideLoading();
      
      if (result.success) {
        wx.showToast({
          title: result.message,
          icon: 'success',
          duration: 2000
        });
        // Reload vocabulary status
        this.loadVocabStatus();
      } else {
        wx.showToast({
          title: result.message,
          icon: 'none',
          duration: 2000
        });
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('Failed to load vocab:', err);
      wx.showToast({
        title: '加载词汇失败',
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