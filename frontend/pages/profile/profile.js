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
      days_since_registration: 0,
      usage_hours: 0
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
    
    // 检查是否需要刷新词汇状态数据
    const needsRefresh = wx.getStorageSync('vocab_status_needs_refresh');
    if (needsRefresh) {
      console.log('Vocabulary status refresh triggered from other pages');
      wx.removeStorageSync('vocab_status_needs_refresh');
      
      // 重新加载词汇状态数据
      this.loadVocabStatus();
    }
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
        
        // 如果是stats数据，计算小时数
        if (key === 'stats' && data && data.total_usage_time) {
          updateData[key].usage_hours = Math.floor(data.total_usage_time / 3600);
        }
        
        // 如果是vocabStatus数据，计算掌握率百分比
        if (key === 'vocabStatus' && data && data.mastery_percentage !== undefined) {
          updateData[key].mastery_percentage_display = Math.floor(data.mastery_percentage);
        }
        
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
    this.loadWithRetry('vocabStatus', () => {
      return api.user.getVocabStatus().then(data => {
        console.log('[Profile] 词汇状态API返回:', data);
        console.log('[Profile] added_vocab_levels:', data.added_vocab_levels);
        console.log('[Profile] level_vocab_counts:', data.level_vocab_counts);
        return data;
      });
    });
  },
  
  /**
   * Load available grades
   */
  loadAvailableGrades: function() {
    console.log('开始加载可用年级...');
    api.user.getAvailableGrades().then(data => {
      console.log('可用年级API返回:', data);
      const grades = data.grades || data || []; // 兼容不同的返回格式
      console.log('解析后的年级数据:', grades);
      this.setData({ 
        availableGrades: grades
      });
    }).catch(err => {
      console.error('Failed to load available grades:', err);
      // 使用默认的年级选项
      const defaultGrades = [
        {grade: "Primary School", description: "Primary School"},
        {grade: "Middle School", description: "Middle School"},
        {grade: "High School", description: "High School"},
        {grade: "CET4", description: "CET4"},
        {grade: "CET6", description: "CET6"}
      ];
      this.setData({ availableGrades: defaultGrades });
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
    
    // 优先使用已经存在的editProfile，如果没有则从 userInfo 初始化
    let editProfile = this.data.editProfile;
    if (!editProfile || Object.keys(editProfile).length === 0) {
      editProfile = {
        nickname: userInfo.nickname || '',
        age: userInfo.age || '',
        gender: userInfo.gender || 'Unspecified',
        grade: userInfo.grade || 'Primary School'
      };
      console.log('初始化编辑表单数据:', editProfile);
    } else {
      console.log('使用已存在的编辑数据:', editProfile);
    }
    
    console.log('开始编辑个人资料');
    console.log('当前用户信息:', userInfo);
    console.log('编辑表单数据:', editProfile);
    console.log('可用年级数据:', this.data.availableGrades);
    
    // 检查可用年级是否加载成功
    if (!this.data.availableGrades || this.data.availableGrades.length === 0) {
      console.warn('可用年级未加载，重新加载...');
      this.loadAvailableGrades();
      wx.showToast({
        title: '正在加载数据，请稍后重试',
        icon: 'none'
      });
      return;
    }
    
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
    
    console.log('性别索引:', currentGenderIndex);
    console.log('年级索引:', currentGradeIndex);
    
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
    // 检查是否有未保存的修改
    const editProfile = this.data.editProfile;
    const userInfo = this.data.userInfo;
    
    let hasChanges = false;
    if (editProfile && userInfo) {
      hasChanges = editProfile.nickname !== (userInfo.nickname || '') ||
                   editProfile.age !== (userInfo.age || '') ||
                   editProfile.gender !== (userInfo.gender || 'Unspecified') ||
                   editProfile.grade !== (userInfo.grade || 'Primary School');
    }
    
    if (hasChanges) {
      wx.showModal({
        title: '放弃修改',
        content: '您有未保存的修改，确定要放弃吗？',
        success: (res) => {
          if (res.confirm) {
            this.setData({
              showEditModal: false,
              editProfile: {} // 放弃修改时清空
            });
          }
        }
      });
    } else {
      this.setData({
        showEditModal: false
      });
    }
  },

  /**
   * Handle modal overlay tap (close modal only when clicking on overlay, not content)
   */
  onModalOverlayTap: function(e) {
    // 只有点击背景区域才关闭模态框
    if (e.target === e.currentTarget) {
      this.onCloseEditModal();
    }
  },

  /**
   * Stop event propagation
   */
  stopPropagation: function() {
    // 空函数，用于阻止事件冒泡
  },
  
  /**
   * Handle edit form input
   */
  onEditInputChange: function(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    const editProfile = this.data.editProfile;
    
    console.log(`输入字段变化: ${field} = ${value}`);
    
    editProfile[field] = value;
    this.setData({ 
      editProfile,
      showEditModal: true  // 确保模态框保持打开状态
    });
    
    console.log('更新后的editProfile:', this.data.editProfile);
  },
  
  /**
   * Handle picker change (for gender and grade)
   */
  onPickerChange: function(e) {
    const field = e.currentTarget.dataset.field;
    const value = parseInt(e.detail.value);
    const editProfile = this.data.editProfile;
    
    console.log(`Picker变化: ${field}, 索引: ${value}`);
    
    if (field === 'gender') {
      const genders = ['Male', 'Female', 'Unspecified'];
      editProfile.gender = genders[value];
      console.log(`性别更新为: ${editProfile.gender}`);
      this.setData({ 
        editProfile: editProfile,
        currentGenderIndex: value,
        showEditModal: true  // 确保模态框保持打开状态
      });
    } else if (field === 'grade') {
      if (this.data.availableGrades && this.data.availableGrades[value]) {
        editProfile.grade = this.data.availableGrades[value].grade;
        console.log(`年级更新为: ${editProfile.grade}`);
        this.setData({ 
          editProfile: editProfile,
          currentGradeIndex: value,
          showEditModal: true  // 确保模态框保持打开状态
        });
      } else {
        console.error('可用年级数据不存在或索引超出范围');
        console.error('当前可用年级:', this.data.availableGrades);
        console.error('请求的索引:', value);
      }
    }
    
    console.log('更新后的editProfile:', this.data.editProfile);
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
    
    console.log('开始保存个人资料...');
    console.log('要保存的数据:', editProfile);
    
    // 检查是否有数据可保存
    if (!editProfile) {
      console.error('编辑数据为空');
      wx.showToast({
        title: '数据错误，请重新编辑',
        icon: 'none'
      });
      return;
    }
    
    // Validate input
    if (editProfile.age && (isNaN(editProfile.age) || editProfile.age < 1 || editProfile.age > 120)) {
      console.log('年龄验证失败:', editProfile.age);
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
    
    console.log('开始更新个人资料:', updateData);
    console.log('当前用户认证状态:', app.globalData.isLoggedIn);
    console.log('当前存储的token:', wx.getStorageSync('talkai_token') ? '已存在' : '不存在');
    
    api.user.updateProfile(updateData).then(updatedProfile => {
      wx.hideLoading();
      
      // Update global user info
      app.globalData.userInfo = {
        ...app.globalData.userInfo,
        ...updatedProfile
      };
      
      // Update local data and clear edit profile after successful save
      this.setData({
        userInfo: app.globalData.userInfo,
        showEditModal: false,
        editProfile: {} // 保存成功后清空编辑数据
      });
      
      wx.showToast({
        title: '个人资料已更新',
        icon: 'success'
      });
      
      // Reload data to get updated vocab status
      this.loadUserData();
      
      // 词汇状态会在loadUserData中自动加载，暂时禁用额外的延迟刷新
      // setTimeout(() => {
      //   this.loadVocabStatus();
      // }, 1000);
      
    }).catch(err => {
      wx.hideLoading();
      console.error('Failed to update profile:', err);
      
      // 详细错误信息输出
      console.error('错误类型:', typeof err);
      console.error('错误内容:', err);
      if (err && err.response) {
        console.error('响应状态码:', err.response.status);
        console.error('响应数据:', err.response.data);
      }
      
      // 更详细的错误提示
      let errorMessage = '更新失败';
      if (err && err.detail) {
        errorMessage = err.detail;
      } else if (err && typeof err === 'string') {
        errorMessage = err;
      } else if (err && err.message) {
        errorMessage = err.message;
      }
      
      wx.showToast({
        title: errorMessage,
        icon: 'none',
        duration: 3000
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

  /**
   * Navigate to connection test page
   */
  onTestConnection: function() {
    wx.navigateTo({
      url: '/pages/profile/test-connection'
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