// 测试前端到后端连接的临时页面
const api = require('../../services/api');

Page({
  data: {
    testResults: [],
    isLoading: false
  },

  onLoad: function (options) {
    console.log('Test connection page loaded');
  },

  // 测试基础连接
  testBasicConnection: function() {
    this.setData({ isLoading: true });
    this.addResult('开始测试基础连接...');
    
    wx.request({
      url: 'http://localhost:8000/health',
      method: 'GET',
      success: (res) => {
        this.addResult(`✅ 基础连接成功: ${res.statusCode}`);
        this.addResult(`响应数据: ${JSON.stringify(res.data)}`);
      },
      fail: (err) => {
        this.addResult(`❌ 基础连接失败: ${JSON.stringify(err)}`);
      },
      complete: () => {
        this.setData({ isLoading: false });
      }
    });
  },

  // 测试API封装
  testAPIWrapper: function() {
    this.setData({ isLoading: true });
    this.addResult('开始测试API封装...');
    
    // 测试无需认证的端点
    api.user.getAvailableGrades().then(result => {
      this.addResult(`✅ API封装成功: ${JSON.stringify(result)}`);
    }).catch(err => {
      this.addResult(`❌ API封装失败: ${JSON.stringify(err)}`);
    }).finally(() => {
      this.setData({ isLoading: false });
    });
  },

  // 测试认证
  testAuthentication: function() {
    this.setData({ isLoading: true });
    this.addResult('开始测试认证...');
    
    const token = wx.getStorageSync('talkai_token');
    if (!token) {
      this.addResult('❌ 未找到token，请先登录');
      this.setData({ isLoading: false });
      return;
    }
    
    this.addResult(`Token存在: ${token.substring(0, 20)}...`);
    
    // 尝试获取个人资料
    api.user.getProfile().then(result => {
      this.addResult(`✅ 认证成功，个人资料: ${JSON.stringify(result)}`);
    }).catch(err => {
      this.addResult(`❌ 认证失败: ${JSON.stringify(err)}`);
    }).finally(() => {
      this.setData({ isLoading: false });
    });
  },

  // 测试个人资料更新
  testProfileUpdate: function() {
    this.setData({ isLoading: true });
    this.addResult('开始测试个人资料更新...');
    
    const updateData = {
      nickname: `测试昵称_${Date.now()}`,
      age: 25,
      gender: 'Male',
      grade: 'CET4'
    };
    
    this.addResult(`更新数据: ${JSON.stringify(updateData)}`);
    
    api.user.updateProfile(updateData).then(result => {
      this.addResult(`✅ 个人资料更新成功: ${JSON.stringify(result)}`);
    }).catch(err => {
      this.addResult(`❌ 个人资料更新失败: ${JSON.stringify(err)}`);
    }).finally(() => {
      this.setData({ isLoading: false });
    });
  },

  // 清空测试结果
  clearResults: function() {
    this.setData({ testResults: [] });
  },

  // 添加测试结果
  addResult: function(message) {
    const results = this.data.testResults;
    results.push({
      message: message,
      timestamp: new Date().toLocaleTimeString()
    });
    this.setData({ testResults: results });
    console.log(message);
  }
});