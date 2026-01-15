// src/components/Persona/registry.js
// Persona plugin kayıt ve yönetim sistemi - Sadece mevcut klasörler için

import { lazy } from 'react';
import { personaService } from '../../services/personaService';

/**
 * Persona plugin kayıt ve yönetim sistemi
 */
class PersonaRegistry {
  constructor() {
    this.plugins = new Map();
    this.loading = new Map();
    this.defaultPlugins = ['social-media'];
    
    // Başlangıçta plugin discovery başlat
    this.initPluginDiscovery();
  }
  
  /**
   * Plugin kaydetme
   * @param {Object} plugin - Plugin bilgileri
   */
  register(plugin) {
    if (!plugin || !plugin.id) {
      console.error('Invalid plugin format', plugin);
      return false;
    }
    
    try {
      this.plugins.set(plugin.id, plugin);
      console.log(`Persona plugin kaydedildi: ${plugin.name || plugin.id}`);
      return true;
    } catch (error) {
      console.error(`Plugin kayıt hatası (${plugin.id}):`, error);
      return false;
    }
  }
  
  /**
   * Plugin getirme
   * @param {string} id - Plugin ID
   * @returns {Object|null} Plugin objesi veya null
   */
  getPlugin(id) {
    return this.plugins.get(id) || null;
  }
  
  /**
   * Tüm pluginleri getirme
   * @returns {Array} Plugin listesi
   */
  getAllPlugins() {
    return Array.from(this.plugins.values());
  }
  
  /**
   * Plugin varlığını kontrol et
   * @param {string} id - Plugin ID
   * @returns {boolean} Plugin varsa true, yoksa false
   */
  hasPlugin(id) {
    return this.plugins.has(id);
  }
  
  /**
   * Plugin discovery mekanizması başlatma
   */
  async initPluginDiscovery() {
    console.log("Plugin discovery başlatılıyor...");
    
    // Önce backend'den plugin listesini al
    try {
      const plugins = await this.discoverFromBackend();
      
      // Backend plugin'leri ve varsayılan plugin'lerin birleşimi
      const allPluginIds = [...new Set([
        ...this.defaultPlugins,
        ...plugins.map(p => p.id)
      ])];
      
      console.log(`Bulunan plugin'ler: ${allPluginIds.join(', ')}`);
      
      // Pluginleri kaydet (component yüklenmeden)
      for (const plugin of plugins) {
        if (!this.plugins.has(plugin.id)) {
          this.register({
            ...plugin,
            component: null // Component lazy olarak yüklenecek
          });
        }
      }
      
      // Varsayılan pluginleri yükle
      await this.loadDefaultPlugins();
      
    } catch (error) {
      console.error("Plugin discovery hatası:", error);
      // Hata olsa bile varsayılan pluginleri yüklemeyi dene
      await this.loadDefaultPlugins();
    }
  }
  
  /**
   * Backend'den plugin keşfi
   * @returns {Promise<Array>} Plugin listesi
   */
  async discoverFromBackend() {
    try {
      const response = await personaService.getPersonas();
      if (response.data?.status === 'success') {
        return response.data.personas || [];
      }
      return [];
    } catch (error) {
      console.error("Backend plugin keşfi hatası:", error);
      return [];
    }
  }
  
  /**
   * Varsayılan pluginleri yükle
   */
  async loadDefaultPlugins() {
    for (const pluginId of this.defaultPlugins) {
      if (!this.plugins.has(pluginId) || !this.plugins.get(pluginId).component) {
        try {
          await this.loadPlugin(pluginId);
        } catch (error) {
          console.error(`Varsayılan plugin yüklenemedi: ${pluginId}`, error);
        }
      }
    }
  }
  
  /**
   * Dinamik import ile plugin yükleme
   * @param {string} id - Plugin ID
   * @returns {Promise<boolean>} Başarı durumu
   */
  async loadPlugin(id) {
    // Eğer plugin zaten tam olarak yüklendiyse, hemen başarı döndür
    if (this.plugins.has(id) && this.plugins.get(id).component) {
      return true;
    }
    
    // Yükleme işlemi zaten başladıysa bekle
    if (this.loading.has(id)) {
      return this.loading.get(id);
    }
    
    // Yeni yükleme işlemi başlat
    const loadingPromise = new Promise(async (resolve) => {
      try {
        console.log(`Plugin dinamik yükleniyor: ${id}`);
        
        // Önce plugin metadata'sını almayı dene
        let pluginMeta;
        if (this.plugins.has(id)) {
          // Zaten kaydedilmiş ama component'i eksik
          pluginMeta = this.plugins.get(id);
        } else {
          // Metadata'yı API'den veya varsayılanlardan al
          pluginMeta = await this.fetchPluginMetadata(id);
        }
        
        // Komponentin kendisini dinamik import et
        try {
          // Her bir persona için dinamik import fonksiyonu
          const importFn = this.getPluginImporter(id);
          
          if (importFn) {
            try {
              // Önce modülü getir
              const module = await importFn();
              
              let component;
              // Eğer import sonucu bir nesne ise ve component özelliği varsa
              if (module.default && typeof module.default === 'object' && module.default.component) {
                console.log(`${id} için plugin objesi formatı tespit edildi, component çıkarılıyor`);
                // component değeri bizim React bileşenimiz, onu lazily wrap edelim
                component = lazy(() => Promise.resolve({
                  default: module.default.component
                }));
                
                // Ayrıca meta bilgilerini de alalım
                const meta = { ...module.default };
                delete meta.component; // component'i çıkar
                
                // Plugin metadata bilgilerini güncelle
                pluginMeta = {
                  ...pluginMeta,
                  ...meta
                };
              } else {
                // Normal React bileşeni (doğrudan fonksiyon/sınıf)
                component = lazy(() => Promise.resolve(module));
              }
              
              // Plugin'i güncelle veya kaydet
              if (this.plugins.has(id)) {
                // Mevcut plugin'i güncelle
                const updatedPlugin = {
                  ...this.plugins.get(id),
                  ...pluginMeta,
                  component: component
                };
                this.plugins.set(id, updatedPlugin);
              } else {
                // Yeni plugin kaydet
                this.register({
                  ...pluginMeta,
                  component: component
                });
              }
              
              console.log(`Plugin başarıyla yüklendi: ${id}`);
              resolve(true);
              return;
            } catch (asyncError) {
              console.error(`Plugin async import hatası: ${id}`, asyncError);
            }
          }
          
          console.warn(`${id} için import fonksiyonu bulunamadı veya başarısız oldu, varsayılan görünüm kullanılacak`);
          
          // Varsayılan görünümü yükle
          const DefaultView = lazy(() => import('./base/DefaultPersonaView'));
          this.register({
            ...pluginMeta,
            component: DefaultView
          });
          
          resolve(true);
          
        } catch (importError) {
          console.error(`Plugin dinamik import hatası: ${id}`, importError);
          
          // Hata olsa bile varsayılan görünümle devam et
          try {
            const DefaultView = lazy(() => import('./base/DefaultPersonaView'));
            this.register({
              ...pluginMeta,
              component: DefaultView
            });
            
            resolve(true); // Varsayılan görünümle devam ettiğimiz için true dönüyoruz
          } catch (defaultViewError) {
            console.error("Varsayılan görünüm yüklenemedi:", defaultViewError);
            resolve(false);
          }
        }
      } catch (error) {
        console.error(`Plugin yüklenemedi: ${id}`, error);
        resolve(false);
      } finally {
        this.loading.delete(id);
      }
    });
    
    // Yükleme işlemini önbelleğe al
    this.loading.set(id, loadingPromise);
    return loadingPromise;
  }
  
  /**
   * Plugin importer fonksiyonu - SADECE MEVCUT KLASÖRLERİ İÇERİR
   * @param {string} id - Plugin ID
   * @returns {Function} Import fonksiyonu
   */
  getPluginImporter(id) {
    // Webpack için sadece var olan klasörlere import yapın
    switch(id) {
      case 'social-media':
        return () => import('./plugins/social-media')
          .catch(error => {
            console.warn('Social media plugin yüklenemedi:', error);
            return import('./base/DefaultPersonaView')
              .then(module => ({ 
                default: module.default
              }));
          });
      
      // Diğer tüm plugin'ler için varsayılan görünüm kullan
      default:
        return () => import('./base/DefaultPersonaView')
          .then(module => ({ 
            default: module.default
          }));
    }
  }
  
  /**
   * Plugin metadata'sını getir
   * @param {string} id - Plugin ID
   * @returns {Promise<Object>} Plugin metadata
   */
  async fetchPluginMetadata(id) {
    try {
      // Önce backend'den almayı dene
      const response = await personaService.getPersona(id);
      if (response.data?.status === 'success' && response.data.persona) {
        const persona = response.data.persona;
        return {
          id: persona.id,
          name: persona.name,
          description: persona.description,
          icon: persona.icon || 'User',
          capabilities: persona.capabilities || []
        };
      }
    } catch (error) {
      console.warn(`Plugin metadata'sı backend'den alınamadı: ${id}`, error);
    }
    
    // Backend'den alınamazsa varsayılan metadata oluştur
    return {
      id,
      name: this.getDefaultPluginName(id),
      description: this.getDefaultPluginDescription(id),
      icon: this.getDefaultPluginIcon(id),
      capabilities: []
    };
  }
  
  /**
   * Varsayılan plugin adını getir
   * @param {string} id - Plugin ID
   * @returns {string} Plugin adı
   */
  getDefaultPluginName(id) {
    switch(id) {
      case 'social-media': return 'Sosyal Medya';
      case 'developer': return 'Geliştirici';
      case 'task-executor': return 'Görev Yürütücü';
      case 'assistant': return 'Genel Asistan';
      default: return id.charAt(0).toUpperCase() + id.slice(1).replace(/-/g, ' ');
    }
  }
  
  /**
   * Varsayılan plugin açıklamasını getir
   * @param {string} id - Plugin ID
   * @returns {string} Plugin açıklaması
   */
  getDefaultPluginDescription(id) {
    switch(id) {
      case 'social-media': return 'Sosyal medya içeriği oluşturma ve yönetme';
      case 'developer': return 'Kod geliştirme ve yazılım desteği';
      case 'task-executor': return 'Sistem görevlerini ve otomasyonları yürütür';
      case 'assistant': return 'Genel amaçlı yardımcı asistan';
      default: return 'Özel yardımcı';
    }
  }
  
  /**
   * Varsayılan plugin ikonunu getir
   * @param {string} id - Plugin ID
   * @returns {string} Plugin ikonu
   */
  getDefaultPluginIcon(id) {
    switch(id) {
      case 'social-media': return 'Share2';
      case 'developer': return 'Code';
      case 'task-executor': return 'Server';
      case 'assistant': return 'User';
      default: return 'User';
    }
  }
  
  /**
   * Backend'den pluginleri senkronize et
   */
  async syncFromBackend() {
    try {
      const response = await personaService.getAllPlugins();
      const data = response.data;
      
      if (data.status === 'success' && data.plugins) {
        for (const plugin of data.plugins) {
          if (!this.plugins.has(plugin.id)) {
            // Backend'den gelen plugin metadata'sını kaydet
            this.register({
              ...plugin,
              component: null // Komponent gerektiğinde yüklenecek
            });
          }
        }
      }
      
      return true;
    } catch (error) {
      console.error('Backend plugin senkronizasyonu başarısız:', error);
      return false;
    }
  }
}

// Singleton instance
export const personaRegistry = new PersonaRegistry();

// Ayrıca varsayılan görünümü kontrol et
import('./base/DefaultPersonaView')
  .then(() => console.log('Varsayılan persona görünümü kontrol edildi'))
  .catch((error) => console.error('Varsayılan görünüm dosyası bulunamadı:', error));

// Personaları yükle
personaRegistry.loadDefaultPlugins().then(() => {
  console.log('Varsayılan pluginler yüklendi');
  personaRegistry.syncFromBackend().then(() => {
    console.log('Backend pluginleri senkronize edildi');
  });
});

export default personaRegistry;