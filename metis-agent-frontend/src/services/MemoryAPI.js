// src/services/MemoryAPI.js
import axios from 'axios';

const BASE_URL = '/api/memory';

class MemoryAPI {
  static async storeMemory(content, category = 'general', tags = []) {
    return axios.post(`${BASE_URL}/store`, { content, category, tags });
  }
  
  static async retrieveMemories(query = null, category = null, tags = [], limit = 10) {
    let url = `${BASE_URL}/retrieve?limit=${limit}`;
    
    if (query) url += `&query=${encodeURIComponent(query)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (tags && tags.length > 0) url += `&tags=${tags.join(',')}`;
    
    return axios.get(url);
  }
  
  static async updateMemory(memoryId, content, category, tags) {
    return axios.put(`${BASE_URL}/update/${memoryId}`, { content, category, tags });
  }
  
  static async deleteMemory(memoryId) {
    return axios.delete(`${BASE_URL}/delete/${memoryId}`);
  }
  
  static async clearAllMemories() {
    return axios.post(`${BASE_URL}/clear`);
  }
  
  static async searchBySimilarity(query, limit = 5) {
    return axios.get(`${BASE_URL}/search?query=${encodeURIComponent(query)}&limit=${limit}`);
  }
  
  static async setUser(username) {
    return axios.post(`${BASE_URL}/user/${username}`);
  }
}

export default MemoryAPI;