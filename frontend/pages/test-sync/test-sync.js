// 词汇同步测试页面
const app = getApp();
const api = require('../../services/api');

Page({
  data: {
    syncStatus: {},
    testResults: [],
    isTestRunning: false
  },

  onLoad: function() {
    this.updateSyncStatus();
  },

  // 更新同步状态显示
  updateSyncStatus: function() {
    const status = app.getVocabSyncStatus();
    this.setData({
      syncStatus: status || {}
    });
  },

  // 测试API连接
  testAPIConnection: async function() {
    this.addTestResult('开始测试API连接...');
    
    try {
      const result = await api.getVocabStatus();
      this.addTestResult(`✅ API连接成功: ${result.total_vocab_count}个词汇`);
    } catch (error) {
      this.addTestResult(`❌ API连接失败: ${error.message}`);
    }
  },

  // 测试词汇列表获取
  testVocabListAPI: async function() {
    this.addTestResult('开始测试词汇列表获取...');
    
    try {
      const result = await api.getVocabList();
      this.addTestResult(`✅ 词汇列表获取成功: ${result.total_count}个词汇`);
      this.addTestResult(`   - 来源分布: ${this.analyzeSources(result.vocabulary)}`);
    } catch (error) {
      this.addTestResult(`❌ 词汇列表获取失败: ${error.message}`);
    }
  },

  // 测试强制同步
  testForceSync: async function() {
    this.addTestResult('开始测试强制同步...');
    
    try {
      const success = await app.forceVocabSync();
      if (success) {
        this.addTestResult('✅ 强制同步成功');
        this.updateSyncStatus();
      } else {
        this.addTestResult('❌ 强制同步失败');
      }
    } catch (error) {
      this.addTestResult(`❌ 强制同步异常: ${error.message}`);
    }
  },

  // 测试定期同步状态
  testPeriodicSync: function() {
    const status = app.getVocabSyncStatus();
    
    if (status && status.isInitialized) {
      this.addTestResult('✅ 定期同步已初始化');
      this.addTestResult(`   - 同步间隔: ${status.config.VOCAB_SYNC_INTERVAL / 1000}秒`);
      this.addTestResult(`   - 上次同步: ${status.lastSyncTime ? new Date(status.lastSyncTime).toLocaleTimeString() : '未同步'}`);
      
      if (status.nextSyncTime) {
        const nextSync = new Date(status.nextSyncTime);
        this.addTestResult(`   - 下次同步: ${nextSync.toLocaleTimeString()}`);
      }
    } else {
      this.addTestResult('❌ 定期同步未初始化');
    }
  },

  // 模拟词汇操作
  testVocabOperation: function() {
    this.addTestResult('模拟词汇操作触发同步...');
    
    // 模拟添加词汇
    app.addVocabWord({
      word: 'test-sync-' + Date.now(),
      definition: '测试同步功能',
      source: 'manual'
    });
    
    this.addTestResult('✅ 已添加测试词汇，应该触发自动同步');
  },

  // 运行完整测试套件
  runFullTest: async function() {
    if (this.data.isTestRunning) {
      return;
    }

    this.setData({
      isTestRunning: true,
      testResults: []
    });

    this.addTestResult('🚀 开始运行完整测试套件...');
    this.addTestResult('');

    // 测试1: API连接
    this.addTestResult('=== 测试1: API连接 ===');
    await this.testAPIConnection();
    await this.sleep(1000);

    // 测试2: 词汇列表API
    this.addTestResult('');
    this.addTestResult('=== 测试2: 词汇列表API ===');
    await this.testVocabListAPI();
    await this.sleep(1000);

    // 测试3: 定期同步状态
    this.addTestResult('');
    this.addTestResult('=== 测试3: 定期同步状态 ===');
    this.testPeriodicSync();
    await this.sleep(1000);

    // 测试4: 强制同步
    this.addTestResult('');
    this.addTestResult('=== 测试4: 强制同步 ===');
    await this.testForceSync();
    await this.sleep(1000);

    // 测试5: 词汇操作触发同步
    this.addTestResult('');
    this.addTestResult('=== 测试5: 词汇操作触发 ===');
    this.testVocabOperation();

    this.addTestResult('');
    this.addTestResult('🎉 测试套件运行完成！');

    this.setData({
      isTestRunning: false
    });
  },

  // 清空测试结果
  clearResults: function() {
    this.setData({
      testResults: []
    });
  },

  // 辅助方法：添加测试结果
  addTestResult: function(message) {
    const results = this.data.testResults;
    results.push({
      message: message,
      timestamp: new Date().toLocaleTimeString()
    });
    
    this.setData({
      testResults: results
    });

    console.log(`[TestSync] ${message}`);
  },

  // 辅助方法：分析词汇来源
  analyzeSources: function(vocabulary) {
    if (!vocabulary || vocabulary.length === 0) return '无数据';
    
    const sources = {};
    vocabulary.forEach(item => {
      const source = item.source || 'unknown';
      sources[source] = (sources[source] || 0) + 1;
    });
    
    return Object.entries(sources)
      .map(([source, count]) => `${source}: ${count}`)
      .join(', ');
  },

  // 辅助方法：延迟
  sleep: function(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
});