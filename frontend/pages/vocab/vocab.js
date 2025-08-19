// pages/vocab/vocab.js
const app = getApp();
const api = require('../../services/api');

Page({
  data: {
    vocabList: [],
    searchText: '',
    totalWords: 0,
    masteredWords: 0,
    learningWords: 0
  },

  onLoad: function (options) {
    this.loadVocabList();
  },

  onShow: function () {
    this.loadVocabList();
  },

  loadVocabList: function() {
    const cachedVocab = app.globalData.vocabList || [];
    
    this.setData({
      vocabList: cachedVocab,
      totalWords: cachedVocab.length,
      masteredWords: cachedVocab.filter(item => item.is_mastered).length,
      learningWords: cachedVocab.filter(item => !item.is_mastered).length
    });
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