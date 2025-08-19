// Local Storage Utility Functions
const STORAGE_KEYS = {
  TOKEN: 'talkai_token',
  USER_INFO: 'talkai_user_info',
  VOCAB_LIST: 'talkai_vocab_list',
  CONVERSATION_HISTORY: 'talkai_conversation',
  LAST_SYNC_TIME: 'talkai_last_sync',
  APP_SETTINGS: 'talkai_settings'
};

/**
 * Get token from storage
 */
function getToken() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.TOKEN);
  } catch (e) {
    console.error('Failed to get token:', e);
    return null;
  }
}

/**
 * Set token to storage
 */
function setToken(token) {
  try {
    wx.setStorageSync(STORAGE_KEYS.TOKEN, token);
    return true;
  } catch (e) {
    console.error('Failed to set token:', e);
    return false;
  }
}

/**
 * Get user info from storage
 */
function getUserInfo() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.USER_INFO);
  } catch (e) {
    console.error('Failed to get user info:', e);
    return null;
  }
}

/**
 * Set user info to storage
 */
function setUserInfo(userInfo) {
  try {
    wx.setStorageSync(STORAGE_KEYS.USER_INFO, userInfo);
    return true;
  } catch (e) {
    console.error('Failed to set user info:', e);
    return false;
  }
}

/**
 * Get vocabulary list from storage
 */
function getVocabList() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.VOCAB_LIST) || [];
  } catch (e) {
    console.error('Failed to get vocab list:', e);
    return [];
  }
}

/**
 * Set vocabulary list to storage
 */
function setVocabList(vocabList) {
  try {
    wx.setStorageSync(STORAGE_KEYS.VOCAB_LIST, vocabList || []);
    return true;
  } catch (e) {
    console.error('Failed to set vocab list:', e);
    return false;
  }
}

/**
 * Get conversation history from storage
 */
function getConversationHistory() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.CONVERSATION_HISTORY) || [];
  } catch (e) {
    console.error('Failed to get conversation history:', e);
    return [];
  }
}

/**
 * Set conversation history to storage
 */
function setConversationHistory(history) {
  try {
    // Limit history to last 100 messages to save storage
    const limitedHistory = (history || []).slice(-100);
    wx.setStorageSync(STORAGE_KEYS.CONVERSATION_HISTORY, limitedHistory);
    return true;
  } catch (e) {
    console.error('Failed to set conversation history:', e);
    return false;
  }
}

/**
 * Add message to conversation history
 */
function addMessageToHistory(message) {
  try {
    const history = getConversationHistory();
    history.push({
      ...message,
      timestamp: new Date().toISOString()
    });
    return setConversationHistory(history);
  } catch (e) {
    console.error('Failed to add message to history:', e);
    return false;
  }
}

/**
 * Get last sync time
 */
function getLastSyncTime() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.LAST_SYNC_TIME);
  } catch (e) {
    console.error('Failed to get last sync time:', e);
    return null;
  }
}

/**
 * Set last sync time
 */
function setLastSyncTime(timestamp) {
  try {
    wx.setStorageSync(STORAGE_KEYS.LAST_SYNC_TIME, timestamp);
    return true;
  } catch (e) {
    console.error('Failed to set last sync time:', e);
    return false;
  }
}

/**
 * Get app settings
 */
function getAppSettings() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.APP_SETTINGS) || {
      autoSync: true,
      syncInterval: 24,
      showGrammarCorrection: true,
      enableVoice: false,
      theme: 'light'
    };
  } catch (e) {
    console.error('Failed to get app settings:', e);
    return {};
  }
}

/**
 * Set app settings
 */
function setAppSettings(settings) {
  try {
    const currentSettings = getAppSettings();
    const newSettings = { ...currentSettings, ...settings };
    wx.setStorageSync(STORAGE_KEYS.APP_SETTINGS, newSettings);
    return true;
  } catch (e) {
    console.error('Failed to set app settings:', e);
    return false;
  }
}

/**
 * Clear all storage data
 */
function clearAll() {
  try {
    Object.values(STORAGE_KEYS).forEach(key => {
      wx.removeStorageSync(key);
    });
    return true;
  } catch (e) {
    console.error('Failed to clear storage:', e);
    return false;
  }
}

/**
 * Get storage info
 */
function getStorageInfo() {
  try {
    return wx.getStorageInfoSync();
  } catch (e) {
    console.error('Failed to get storage info:', e);
    return null;
  }
}

module.exports = {
  getToken,
  setToken,
  getUserInfo,
  setUserInfo,
  getVocabList,
  setVocabList,
  getConversationHistory,
  setConversationHistory,
  addMessageToHistory,
  getLastSyncTime,
  setLastSyncTime,
  getAppSettings,
  setAppSettings,
  clearAll,
  getStorageInfo,
  STORAGE_KEYS
};