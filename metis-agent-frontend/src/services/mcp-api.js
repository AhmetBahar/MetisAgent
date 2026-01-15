// src/services/mcp-api.js
// MCP mimarisine uygun API servisleri

import axios from 'axios';

// Temel API URL
const BASE_URL = 'http://localhost:6001/api';

// API çağrısı timeout değeri (ms)
const API_TIMEOUT = 30000;

// API client oluştur
const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Yanıt işleme interceptor'u
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Hatası:', error);
    return Promise.reject(error);
  }
);

// MCP API Servis Sınıfı
class MCPApiService {
  constructor(toolName) {
    this.toolName = toolName;
  }

  // GET isteği
  async get(handlerName, params = {}) {
    try {
      return await apiClient.get(`/${this.toolName}/${handlerName}`, { params });
    } catch (error) {
      return this._handleError(error, `${this.toolName}.${handlerName} GET`);
    }
  }

  // POST isteği
  async post(handlerName, data = {}) {
    try {
      return await apiClient.post(`/${this.toolName}/${handlerName}`, data);
    } catch (error) {
      return this._handleError(error, `${this.toolName}.${handlerName} POST`);
    }
  }

  // Hata işleme
  _handleError(error, context) {
    // API yanıtlarından hata mesajını çıkar
    const errorMessage = error.response?.data?.error || error.message || 'Bilinmeyen bir hata oluştu';
    
    // Error objesi oluştur
    const formattedError = new Error(`${context} hatası: ${errorMessage}`);
    formattedError.originalError = error;
    formattedError.context = context;
    formattedError.details = error.response?.data;
    
    throw formattedError;
  }
}

// MCP API servisleri - MCP Tool adlarıyla eşleştirin 
export const MCPLlmAPI = new MCPApiService('llm_tool');
export const MCPCommandExecutorAPI = new MCPApiService('command_executor');
export const MCPEditorAPI = new MCPApiService('editor_tool');
export const MCPFileManagerAPI = new MCPApiService('file_manager');
export const MCPSystemInfoAPI = new MCPApiService('system_info');
export const MCPUserManagerAPI = new MCPApiService('user_manager');
export const MCPNetworkManagerAPI = new MCPApiService('network_manager');
export const MCPSchedulerAPI = new MCPApiService('scheduler');
export const MCPArchiveManagerAPI = new MCPApiService('archive_manager');

// MCP yardımcı fonksiyonları
export const MCPApiUtils = {
  // Sistemdeki tüm araçları listele
  async getTools() {
    try {
      return await apiClient.get('/tools');
    } catch (error) {
      console.error('Araç listesi alınamadı:', error);
      return { tools: [] };
    }
  },
  
  // API durumunu kontrol et
  async checkStatus() {
    try {
      return await apiClient.get('/status');
    } catch (error) {
      console.error('API durum kontrolü başarısız:', error);
      return { status: 'offline', message: error.message };
    }
  }
};

export default {
  MCPLlmAPI,
  MCPCommandExecutorAPI,
  MCPEditorAPI,
  MCPFileManagerAPI,
  MCPSystemInfoAPI,
  MCPUserManagerAPI,
  MCPNetworkManagerAPI,
  MCPSchedulerAPI,
  MCPArchiveManagerAPI,
  MCPApiUtils
};