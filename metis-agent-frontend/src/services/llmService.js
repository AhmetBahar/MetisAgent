// services/llmService.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:6001/api';

class LLMService {
  constructor() {
    this.wsConnection = null;
    this.currentProvider = 'openai';
  }

  async getProviders() {
    try {
      const response = await axios.get(`${API_BASE_URL}/llm_tool/get_providers`);
      return response.data.providers || [];
    } catch (error) {
      console.error('Error fetching LLM providers:', error);
      return [];
    }
  }

  async getModels(provider = 'openai') {
    try {
      const response = await axios.get(`${API_BASE_URL}/llm_tool/get_models`, {
        params: { provider }
      });
      return response.data.models || [];
    } catch (error) {
      console.error(`Error fetching models for ${provider}:`, error);
      return [];
    }
  }

  async checkProviderStatus(provider = 'openai') {
    try {
      const response = await axios.get(`${API_BASE_URL}/llm_tool/check_status`, {
        params: { provider }
      });
      return response.data;
    } catch (error) {
      console.error(`Error checking status for ${provider}:`, error);
      return { status: 'error', message: 'API error', provider_status: 'error' };
    }
  }

  async setupProvider(providerData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/llm_tool/setup_provider`, providerData);
      return response.data;
    } catch (error) {
      console.error('Error setting up provider:', error);
      throw error;
    }
  }

  async generateText(params) {
    try {
      const response = await axios.post(`${API_BASE_URL}/llm_tool/generate_text`, params);
      return response.data.text || '';
    } catch (error) {
      console.error('Error generating text:', error);
      throw error;
    }
  }

  async generateTasks(prompt, provider = 'openai', model = '', temperature = 0.7) {
    try {
      const response = await axios.post(`${API_BASE_URL}/llm_tool/generate_tasks`, {
        prompt,
        provider,
        model,
        temperature
      });
      return response.data;
    } catch (error) {
      console.error('Error generating tasks:', error);
      throw error;
    }
  }

  // WebSocket streaming
  async startStreaming(params, callbacks = {}) {
    try {
      // Önceki bağlantıyı kapat
      this.stopStreaming();

      // Stream başlat ve WebSocket ID al
      const response = await axios.post(`${API_BASE_URL}/llm_tool/stream_start`, params);
      
      if (response.data.status !== 'success') {
        throw new Error(response.data.message || 'Stream başlatılamadı');
      }

      const wsId = response.data.ws_id;
      
      // WebSocket bağlantısı oluştur
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      //const wsUrl = `${protocol}//${window.location.host}${API_BASE_URL}/llm/stream/${wsId}`;
      const wsUrl = `${protocol}//localhost:6001/api/llm/stream/${wsId}`;

      this.wsConnection = new WebSocket(wsUrl);
      
      // Bağlantı açıldığında
      this.wsConnection.onopen = () => {
        console.log('WebSocket bağlantısı açıldı');
        
        // İlk mesajı gönder (konfigürasyon)
        this.wsConnection.send(JSON.stringify({
          provider_type: params.provider,
          model: params.model,
          prompt: params.prompt,
          temperature: params.temperature || 0.7,
          system_prompt: params.system_prompt || ''
        }));
        
        if (callbacks.onOpen) callbacks.onOpen();
      };
      
      // Mesaj alındığında
      this.wsConnection.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'content') {
            // İçerik geldi
            if (callbacks.onContent) callbacks.onContent(data.content);
          } else if (data.type === 'done') {
            // Tamamlandı
            if (callbacks.onDone) callbacks.onDone(data.content);
          } else if (data.type === 'error') {
            // Hata
            if (callbacks.onError) callbacks.onError(data.content);
          }
        } catch (e) {
          console.error('WebSocket mesajı ayrıştırma hatası:', e);
          if (callbacks.onError) callbacks.onError('Mesaj ayrıştırma hatası');
        }
      };
      
      // Bağlantı kapandığında
      this.wsConnection.onclose = () => {
        console.log('WebSocket bağlantısı kapandı');
        if (callbacks.onClose) callbacks.onClose();
        this.wsConnection = null;
      };
      
      // Hata durumunda
      this.wsConnection.onerror = (error) => {
        console.error('WebSocket hatası:', error);
        if (callbacks.onError) callbacks.onError('WebSocket bağlantı hatası');
      };
      
      return wsId;
    } catch (error) {
      console.error('Streaming başlatma hatası:', error);
      if (callbacks.onError) callbacks.onError(error.message || 'Stream başlatılamadı');
      throw error;
    }
  }

  stopStreaming() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }
}

export default new LLMService();