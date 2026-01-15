// 1. src/services/personas/personaService.js
// Mevcut PersonaAPI'yi genişleterek yeni servis katmanı

import axios from 'axios';

class PersonaService {
  /**
   * Tüm personaları getir
   * @returns {Promise} Persona listesi
   */
  async getPersonas() {
    try {
      const response = await axios.get('/api/personas');
      return response;
    } catch (error) {
      console.error('Personalar alınırken hata:', error);
      throw error;
    }
  }
  
  /**
   * Belirli bir personayı getir
   * @param {string} personaId - Persona ID
   * @returns {Promise} Persona detayları
   */
  async getPersona(personaId) {
    try {
      const response = await axios.get(`/api/personas/${personaId}`);
      return response;
    } catch (error) {
      console.error(`Persona alınırken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Yeni persona oluştur
   * @param {Object} personaData - Persona verileri
   * @returns {Promise} Oluşturma sonucu
   */
  async createPersona(personaData) {
    try {
      const response = await axios.post('/api/personas', personaData);
      return response;
    } catch (error) {
      console.error('Persona oluşturulurken hata:', error);
      throw error;
    }
  }
  
  /**
   * Persona sil
   * @param {string} personaId - Persona ID
   * @returns {Promise} Silme sonucu
   */
  async deletePersona(personaId) {
    try {
      const response = await axios.delete(`/api/personas/${personaId}`);
      return response;
    } catch (error) {
      console.error(`Persona silinirken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Persona durumunu getir
   * @param {string} personaId - Persona ID
   * @returns {Promise} Durum bilgisi
   */
  async getPersonaStatus(personaId) {
    try {
      const response = await axios.get(`/api/personas/${personaId}/status`);
      return response;
    } catch (error) {
      console.error(`Persona durumu alınırken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Personayı başlat
   * @param {string} personaId - Persona ID
   * @returns {Promise} Başlatma sonucu
   */
  async startPersona(personaId) {
    try {
      const response = await axios.post(`/api/personas/${personaId}/start`);
      return response;
    } catch (error) {
      console.error(`Persona başlatılırken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Personayı durdur
   * @param {string} personaId - Persona ID
   * @returns {Promise} Durdurma sonucu
   */
  async stopPersona(personaId) {
    try {
      const response = await axios.post(`/api/personas/${personaId}/stop`);
      return response;
    } catch (error) {
      console.error(`Persona durdurulurken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Persona verilerini getir
   * @param {string} personaId - Persona ID
   * @returns {Promise} Persona verileri
   */
  async getPersonaData(personaId) {
    try {
      const response = await axios.get(`/api/personas/${personaId}/data`);
      return response;
    } catch (error) {
      console.error(`Persona verileri alınırken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Persona verilerini güncelle
   * @param {string} personaId - Persona ID
   * @param {Object} data - Güncellenecek veriler
   * @returns {Promise} Güncelleme sonucu
   */
  async updatePersonaData(personaId, data) {
    try {
      const response = await axios.post(`/api/personas/${personaId}/data`, { data });
      return response;
    } catch (error) {
      console.error(`Persona verileri güncellenirken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * Görevi çalıştır
   * @param {string} personaId - Persona ID
   * @param {Object} task - Görev bilgileri
   * @returns {Promise} Görev sonucu
   */
  async executeTask(personaId, task) {
    try {
      const response = await axios.post(`/api/personas/${personaId}/execute-task`, { task });
      return response;
    } catch (error) {
      console.error(`Görev çalıştırılırken hata: ${personaId}`, error);
      throw error;
    }
  }
  
  /**
   * A2A protokolü ile görev çalıştır
   * @param {Object} task - Görev bilgileri
   * @param {Object} context - Bağlam bilgileri
   * @param {string} targetPersona - Hedef persona ID
   * @returns {Promise} Görev sonucu
   */
  async executeTaskWithPersona(task, context = {}, targetPersona) {
    try {
      const response = await axios.post(`/api/a2a/task`, {
        task,
        context,
        target_persona: targetPersona
      });
      return response;
    } catch (error) {
      console.error(`A2A görev çalıştırılırken hata:`, error);
      throw error;
    }
  }
  
  /**
   * Tüm pluginleri getir
   * @returns {Promise} Plugin listesi
   */
  async getAllPlugins() {
    try {
      const response = await axios.get('/api/plugins');
      return response;
    } catch (error) {
      console.error('Plugin listesi alınırken hata:', error);
      throw error;
    }
  }
  
  /**
   * Belirli bir plugini getir
   * @param {string} pluginId - Plugin ID
   * @returns {Promise} Plugin detayları
   */
  async getPlugin(pluginId) {
    try {
      const response = await axios.get(`/api/plugins/${pluginId}`);
      return response;
    } catch (error) {
      console.error(`Plugin detayları alınırken hata: ${pluginId}`, error);
      throw error;
    }
  }
  
  /**
   * Plugin durumunu güncelle
   * @param {string} pluginId - Plugin ID
   * @param {boolean} enabled - Etkinleştirme durumu
   * @returns {Promise} Güncelleme sonucu
   */
  async updatePluginStatus(pluginId, enabled) {
    try {
      const response = await axios.patch(`/api/plugins/${pluginId}/status`, { enabled });
      return response;
    } catch (error) {
      console.error(`Plugin durumu güncellenirken hata: ${pluginId}`, error);
      throw error;
    }
  }
}

// Singleton instance
export const personaService = new PersonaService();
export default personaService;