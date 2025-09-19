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
    console.log('[VocabPage] onLoad 被调用');
    
    // 只加载最近词汇，避免其他可能引起循环的操作
    this.loadRecentVocabulary();
  },

  onShow: function () {
    console.log('[VocabPage] onShow 被调用');
    
    // 检查是否需要刷新词汇
    if (app.globalData.needRefreshVocab) {
      console.log('[VocabPage] 检测到词汇更新标记，强制刷新');
      app.globalData.needRefreshVocab = false;
      this.loadRecentVocabulary();
      return;
    }
    
    // 添加防抖，避免频繁切换页面时重复调用
    if (this.lastShowTime && (Date.now() - this.lastShowTime) < 2000) {
      console.log('[VocabPage] 页面切换过于频繁，跳过重复加载');
      return;
    }
    this.lastShowTime = Date.now();
    
    // 只刷新最近词汇，不触发同步
    this.loadRecentVocabulary();
  },

  loadVocabList: function() {
    console.log('[VocabPage] loadVocabList 被调用，但已完全禁用避免循环调用');
    
    // 完全禁用所有数据加载，使用静态数据避免接口调用
    this.setData({
      totalWords: 0,
      masteredWords: 0,
      learningWords: 0,
      progressPercentage: 0,
      vocabList: [] // 空数组，不调用任何接口
    });
    
    console.log('[VocabPage] 已禁用数据加载，使用静态数据');
  },

  // 加载最近添加的词汇（AI改错、词典查词和最近更新的等级词汇）
  loadRecentVocabulary: function() {
    console.log('[VocabPage] 加载最近词汇（包括更新的等级词汇）');
    
    // 简化版本：直接加载最近更新的所有词汇
    api.learningVocab.getList({
      include_recent_level: true,
      limit: 50  // 增加limit来显示更多词汇
    }).then(recentVocab => {
      console.log('[VocabPage] 成功获取词汇数据:', recentVocab.length, recentVocab);
      
      const processedVocab = recentVocab.map(item => {
        // 检查是否是被突出显示的等级词汇
        const highlightedWord = app.globalData.highlightedLevelWord;
        const isHighlighted = highlightedWord && 
                             highlightedWord.word === item.word &&
                             (Date.now() - highlightedWord.timestamp) < 30000; // 30秒内高亮
        
        return {
          word: item.word,
          source: item.source,
          level: item.level,
          added_date: item.added_date,
          isMastered: item.is_mastered,
          right_use_count: item.right_use_count,
          wrong_use_count: item.wrong_use_count,
          last_used: item.last_used,
          isHighlighted: isHighlighted,
          isRecentLevelVocab: item.source === 'level_vocab'
        };
      });
      
      // 如果有高亮词汇，将其排在最前面
      const highlightedItems = processedVocab.filter(item => item.isHighlighted);
      const normalItems = processedVocab.filter(item => !item.isHighlighted);
      const sortedVocab = [...highlightedItems, ...normalItems];
      
      // 也更新基本统计数据
      const totalWords = recentVocab.length;
      const masteredWords = processedVocab.filter(item => item.isMastered).length;
      
      this.setData({
        vocabList: sortedVocab,
        totalWords: totalWords,
        masteredWords: masteredWords,
        learningWords: totalWords - masteredWords,
        progressPercentage: totalWords > 0 ? Math.round((masteredWords / totalWords) * 100) : 0
      });
      
      // 清除高亮标记（30秒后自动清除）
      if (app.globalData.highlightedLevelWord) {
        setTimeout(() => {
          app.globalData.highlightedLevelWord = null;
          this.loadRecentVocabulary(); // 重新加载去除高亮
        }, 30000);
      }
      
    }).catch(error => {
      console.error('[VocabPage] 加载最近词汇失败:', error);
      this.setData({ 
        vocabList: [],
        totalWords: 0,
        masteredWords: 0,
        learningWords: 0,
        progressPercentage: 0
      });
    });
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
    // 暂时禁用词汇同步，避免循环调用
    console.log('[VocabPage] refreshVocabData 被调用，但已禁用同步');
    return;
    
    // const vocabSyncManager = app.globalData.vocabSyncManager;
    // if (vocabSyncManager) {
    //   console.log('[VocabPage] 触发词汇数据同步');
    //   vocabSyncManager.syncVocabulary('manual').then(success => {
    //     if (success) {
    //       // 同步成功，重新加载数据
    //       this.loadVocabList();
    //     }
    //   }).catch(error => {
    //     console.error('[VocabPage] 数据同步失败:', error);
    //   });
    // }
  },

  // 手动强制刷新（下拉刷新）
  onPullDownRefresh: function() {
    console.log('[VocabPage] 用户下拉刷新');
    
    // 重新加载最近词汇
    this.loadRecentVocabulary();
    
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