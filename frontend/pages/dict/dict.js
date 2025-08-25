// pages/dict/dict.js
const api = require('../../services/api');

Page({
  data: {
    searchText: '',
    searchResults: [],
    isSearching: false,
    recentSearches: []
  },

  onLoad: function (options) {
    this.loadRecentSearches();
    
    // Handle word parameter from vocabulary suggestions
    if (options.word) {
      const word = decodeURIComponent(options.word);
      this.setData({
        searchText: word
      });
      // Automatically search for the word
      this.searchWord(word);
    }
  },

  loadRecentSearches: function() {
    const recent = wx.getStorageSync('recent_searches') || [];
    this.setData({ recentSearches: recent });
  },

  onSearchInput: function(e) {
    this.setData({ searchText: e.detail.value });
  },

  onSearch: function() {
    const text = this.data.searchText.trim();
    if (!text) return;
    this.searchWord(text);
  },

  searchWord: function(word) {
    if (!word) return;
    
    this.setData({ 
      isSearching: true,
      searchResults: []
    });
    
    api.dict.query(word).then(result => {
      // Handle both single word and multiple results
      let results = [];
      if (result.definition) {
        // Single word result format
        results = [{
          word: word,
          definition: result.definition,
          phonetic: result.phonetic || '',
          translation: result.translation || ''
        }];
      } else if (result.results && Array.isArray(result.results)) {
        // Multiple results format  
        results = result.results;
      }
      
      this.setData({
        searchResults: results,
        isSearching: false
      });
      this.saveRecentSearch(word);
    }).catch(err => {
      console.error('Dictionary search failed:', err);
      this.setData({ 
        isSearching: false,
        searchResults: []
      });
      
      wx.showToast({
        title: '查询失败，请重试',
        icon: 'none',
        duration: 2000
      });
    });
  },

  saveRecentSearch: function(word) {
    let recent = this.data.recentSearches;
    recent = recent.filter(item => item !== word);
    recent.unshift(word);
    recent = recent.slice(0, 10);
    
    this.setData({ recentSearches: recent });
    wx.setStorageSync('recent_searches', recent);
  },

  onRecentSearchTap: function(e) {
    const word = e.currentTarget.dataset.word;
    if (word) {
      this.setData({ searchText: word });
      this.searchWord(word);
    }
  },

  onClearRecentSearches: function() {
    wx.showModal({
      title: '清空记录',
      content: '确定要清空所有搜索记录吗？',
      confirmText: '清空',
      confirmColor: '#DC3545',
      success: (res) => {
        if (res.confirm) {
          this.setData({ recentSearches: [] });
          wx.removeStorageSync('recent_searches');
          wx.showToast({
            title: '记录已清空',
            icon: 'success'
          });
        }
      }
    });
  },

  onAddToVocab: function(e) {
    const word = e.currentTarget.dataset.word;
    if (word) {
      // Add word to vocabulary (implement this based on your vocab management)
      wx.showToast({
        title: '已添加到词汇表',
        icon: 'success',
        duration: 1500
      });
      
      // Navigate to vocab page
      wx.switchTab({
        url: '/pages/vocab/vocab'
      });
    }
  }
});