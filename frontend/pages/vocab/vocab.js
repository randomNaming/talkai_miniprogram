// pages/vocab/vocab.js
const app = getApp();
const api = require('../../services/api');

Page({
  data: {
    vocabList: [],
    searchText: '',
    totalWords: 0,
    masteredWords: 0,
    learningWords: 0,
    progressPercentage: 0,
    // 学习进度统计
    weeklyProgress: [],
    monthlyStats: {
      newWords: 0,
      reviewWords: 0,
      masteredWords: 0
    }
  },

  onLoad: function (options) {
    this.loadVocabList();
    // 加载学习进度数据
    this.loadLearningProgress();
  },

  onShow: function () {
    this.loadVocabList();
    // 每次显示时刷新学习进度
    this.loadLearningProgress();
  },

  loadVocabList: function() {
    // 优先使用实时同步数据，回退到缓存数据
    const cachedVocab = app.globalData.vocabList || [];
    const vocabStats = app.globalData.vocabStats;
    
    const totalWords = vocabStats ? vocabStats.total_vocab_count : cachedVocab.length;
    const masteredWords = vocabStats ? vocabStats.mastered_vocab_count : cachedVocab.filter(item => item.isMastered).length;
    const learningWords = vocabStats ? vocabStats.unmastered_vocab_count : cachedVocab.filter(item => !item.isMastered).length;
    
    // 计算学习进度百分比
    const progressPercentage = totalWords > 0 ? Math.round((masteredWords / totalWords) * 100) : 0;
    
    // 设置词汇列表和进度数据
    this.setData({
      vocabList: cachedVocab,
      totalWords: totalWords,
      masteredWords: masteredWords,
      learningWords: learningWords,
      progressPercentage: progressPercentage
    });
    
    // 如果没有统计数据或数据过期，触发同步
    if (!vocabStats || this.shouldRefreshData()) {
      this.refreshVocabData();
    }
  },

  // 检查是否需要刷新数据
  shouldRefreshData: function() {
    const lastSyncTime = app.globalData.lastSyncTime;
    if (!lastSyncTime) return true;
    
    // 如果超过5分钟没有同步，强制刷新
    const fiveMinutes = 5 * 60 * 1000;
    return (Date.now() - lastSyncTime) > fiveMinutes;
  },

  // 获取详细学习进度数据
  loadLearningProgress: async function() {
    try {
      const response = await api.getLearningProgress();
      if (response.success) {
        this.setData({
          weeklyProgress: response.weekly_progress || [],
          monthlyStats: response.monthly_stats || {
            newWords: 0,
            reviewWords: 0,
            masteredWords: 0
          }
        });
      }
    } catch (error) {
      console.error('获取学习进度失败:', error);
    }
  },

  // 跳转到详细进度页面
  goToProgressView: function() {
    wx.navigateTo({
      url: '/pages/vocab/progress-view'
    });
  },

  // 刷新词汇数据
  refreshVocabData: function() {
    const vocabSyncManager = app.globalData.vocabSyncManager;
    if (vocabSyncManager) {
      console.log('[VocabPage] 触发词汇数据同步');
      vocabSyncManager.syncVocabulary('manual').then(success => {
        if (success) {
          // 同步成功，重新加载数据
          this.loadVocabList();
        }
      }).catch(error => {
        console.error('[VocabPage] 数据同步失败:', error);
      });
    }
  },

  // 手动强制刷新（下拉刷新）
  onPullDownRefresh: function() {
    console.log('[VocabPage] 用户下拉刷新');
    
    this.refreshVocabData();
    
    // 延迟停止下拉刷新动画
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  },

  onSearchInput: function(e) {
    this.setData({
      searchText: e.detail.value
    });
  },

  onSearch: function() {
    // Implement search functionality
  },

  onVocabTap: function(e) {
    const vocab = e.currentTarget.dataset.vocab;
    // Navigate to vocab detail page
  },

  onAddVocab: function() {
    wx.showModal({
      title: '添加词汇',
      content: '请在对话中练习英语，遇到生词时系统会自动添加到词汇表',
      showCancel: false
    });
  }
});