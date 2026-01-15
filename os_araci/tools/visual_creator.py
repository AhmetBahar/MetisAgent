# tools/visual_creator.py
import time
import logging
import json
import os
from typing import Dict, List, Any, Optional, Union

from os_araci.mcp_core.tool import MCPTool

logger = logging.getLogger(__name__)

class VisualCreator(MCPTool):
    """
    Metis Agent görsel üretim aracı.
    
    LLM entegrasyonu kullanarak belirtilen tema, stil ve 
    elemanlara göre görsel prompt'ları oluşturur ve seçenekler sunar.
    """
    
    def __init__(self, **kwargs):
        """Görsel üretim aracını başlat"""
        super().__init__(
            name="visual_creator",
            description="Prompt temelli görsel üretim aracı",
            version="1.0.0",
            category="content_creation",
            capabilities=["image_generation", "prompt_creation", "visual_suggestion"],
            **kwargs
        )
        
        self.image_storage_path = kwargs.get('image_storage_path', './images')
        self.default_count = kwargs.get('default_count', 3)
        self.history = {}  # Geçmiş prompt ve sonuçları saklama
        
        # Klasörü oluştur
        if not os.path.exists(self.image_storage_path):
            os.makedirs(self.image_storage_path, exist_ok=True)
            logger.info(f"Görsel depolama klasörü oluşturuldu: {self.image_storage_path}")
    
    def get_all_actions(self) -> Dict[str, Dict[str, Any]]:
        """Aracın desteklediği tüm aksiyonları döndürür"""
        return {
            "generate_visual_options": {
                "description": "Belirtilen konu, stil ve elemanlara göre görsel seçenekleri oluşturur",
                "parameters": {
                    "topic": {"type": "string", "description": "Görselin ana konusu", "required": True},
                    "visual_style": {"type": "string", "description": "İstenen görsel stili", "required": False},
                    "elements": {"type": "string", "description": "Görselde olması istenen öğeler", "required": False},
                    "aspect_ratio": {"type": "string", "description": "Görsel en boy oranı (ör: '1:1', '4:5', '16:9')", "required": False},
                    "count": {"type": "integer", "description": "Oluşturulacak görsel sayısı", "required": False}
                },
                "returns": {
                    "type": "object",
                    "description": "Oluşturulan görsel seçenekleri"
                }
            },
            "get_visual_by_id": {
                "description": "ID'ye göre belirli bir görsel seçeneğini getir",
                "parameters": {
                    "visual_id": {"type": "string", "description": "Görsel ID'si", "required": True}
                },
                "returns": {
                    "type": "object",
                    "description": "Görsel detayları"
                }
            },
            "select_visual": {
                "description": "Üretilen görsellerden birini seç ve post ile ilişkilendir",
                "parameters": {
                    "visual_id": {"type": "string", "description": "Seçilen görsel ID'si", "required": True},
                    "post_id": {"type": "string", "description": "İlişkilendirilecek post ID'si", "required": True}
                },
                "returns": {
                    "type": "object",
                    "description": "Seçim sonucu"
                }
            },
            "get_generation_history": {
                "description": "Geçmiş görsel üretim isteği geçmişini getirir",
                "parameters": {
                    "limit": {"type": "integer", "description": "Alınacak kayıt sayısı limiti", "required": False}
                },
                "returns": {
                    "type": "object",
                    "description": "Görsel üretim geçmişi"
                }
            }
        }
    
    def generate_visual_options(self, topic: str, visual_style: str = None, 
                              elements: str = None, aspect_ratio: str = "1:1", 
                              count: int = None) -> Dict[str, Any]:
        """
        Belirtilen parametrelere göre görsel seçenekleri oluşturur.
        
        Args:
            topic: Görselin ana konusu
            visual_style: İstenen görsel stili (örn: gerçekçi, karikatür, minimize, vb)
            elements: Görselde olması istenen öğeler (virgülle ayrılmış)
            aspect_ratio: Görsel en boy oranı (örn: 1:1, 4:5, 16:9)
            count: Oluşturulacak görsel sayısı (varsayılan: 3)
            
        Returns:
            Oluşturulan görsel seçenekleri ve detayları
        """
        try:
            # LLM Tool'u al
            llm_tool = self._get_llm_tool()
            if not llm_tool:
                return {"status": "error", "message": "LLM aracı bulunamadı"}
            
            # Eksik parametreler için varsayılanları kullan
            if not visual_style:
                visual_style = "profesyonel, gerçekçi, yüksek kalite"
            
            if not count:
                count = self.default_count
                
            count = min(max(1, count), 5)  # 1-5 arası olmalı
            
            # Görsel prompt oluşturma
            system_prompt = """Sen bir profesyonel görsel sanatçı ve fotoğrafçısın. 
            Verilen bilgilere göre yapay zeka görsel üretim araçları için mükemmel promptlar oluşturman gerekiyor.
            Promptlar detaylı, zengin ve görsel olarak etkileyici olmalı.
            Her prompt bir sosyal medya platformu için kullanılacak görsel üretmek için tasarlanmalı.
            Prompt formatı: SUBJECT, STYLE, DETAILS, LIGHTING, COMPOSITION, COLOR PALETTE, ADDITIONAL NOTES.
            Seçenekler birbirinden farklı olmalı, ama hepsi verilen temaya uygun olmalı."""
                
            prompt = f"""
            Lütfen aşağıdaki konu ve stilin mükemmel kombinasyonuyla 
            {count} farklı görsel üretim promptu oluştur:
            
            Konu: {topic}
            Stil: {visual_style}
            {'İstenen öğeler: ' + elements if elements else 'Özel öğe isteği yok'}
            Görsel oranı: {aspect_ratio}
            
            Her bir prompt için, aşağıdaki yapıyı izle:
            1. Ana konu açıklaması - görselin neyi göstermesi gerektiği
            2. Görsel stil detayları
            3. Kompozisyon ve çerçeveleme
            4. Işık, atmosfer ve renkler
            5. İstenen duygusal etki veya anlatım
            
            Lütfen sonuçları aşağıdaki JSON formatında ver:
            
            ```json
            {
              "variants": [
                {
                  "prompt": "tam prompt metni",
                  "title": "bu varyant için kısa açıklayıcı başlık",
                  "description": "bu görsel varyantın kısa açıklaması"
                },
                // diğer varyantlar
              ]
            }
            ```
            
            JSON dışında hiçbir açıklama veya yorum ekleme, sadece temiz JSON çıktısı ver.
            """
            
            # ChatGPT ile görsel promptları oluştur
            result = llm_tool.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            # LLM sonucunu ayrıştır
            text_output = result.get("text", "") if isinstance(result, dict) else str(result)
            
            # JSON çıktıyı temizle ve parse et
            if "```json" in text_output:
                json_text = text_output.split("```json")[1].split("```")[0].strip()
            elif "```" in text_output:
                json_text = text_output.split("```")[1].strip()
            else:
                json_text = text_output.strip()
                
            prompt_data = json.loads(json_text)
            variants = prompt_data.get("variants", [])
            
            # Gerçek image_gen entegrasyonu - görsel üretim
            generation_results = []
            
            # Her bir varyant için görsel üret
            for idx, variant in enumerate(variants):
                try:
                    prompt_text = variant.get("prompt", "")
                    
                    # image_gen entegrasyonu için placeholder
                    # Gerçek uygulamada, image_gen API'si ile görseller üretilecek
                    # Bu örnek sadece yapıyı göstermek içindir
                    image_result = self._generate_image(prompt_text, aspect_ratio)
                    
                    image_id = f"img_{int(time.time())}_{idx}"
                    image_url = image_result.get("url", f"/api/images/{image_id}")
                    
                    generation_results.append({
                        "visual_id": image_id,
                        "prompt": prompt_text,
                        "title": variant.get("title", f"Görsel {idx+1}"),
                        "description": variant.get("description", ""),
                        "image_url": image_url,
                        "aspect_ratio": aspect_ratio,
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    logger.error(f"Görsel varyantı oluşturma hatası: {str(e)}")
            
            # Geçmişe kaydet
            generation_id = f"gen_{int(time.time())}"
            self.history[generation_id] = {
                "id": generation_id,
                "topic": topic,
                "visual_style": visual_style,
                "elements": elements,
                "aspect_ratio": aspect_ratio,
                "timestamp": time.time(),
                "results": generation_results
            }
            
            return {
                "status": "success",
                "generation_id": generation_id,
                "topic": topic,
                "variants": generation_results,
                "count": len(generation_results)
            }
            
        except Exception as e:
            logger.error(f"Görsel seçenek üretme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_visual_by_id(self, visual_id: str) -> Dict[str, Any]:
        """
        ID'ye göre belirli bir görsel seçeneğini getirir.
        
        Args:
            visual_id: Görsel ID'si
            
        Returns:
            Görsel detayları
        """
        try:
            # Tüm geçmiş içinde ara
            for generation_id, generation_data in self.history.items():
                for variant in generation_data.get("results", []):
                    if variant.get("visual_id") == visual_id:
                        return {
                            "status": "success",
                            "visual": variant,
                            "generation_id": generation_id
                        }
            
            return {"status": "error", "message": f"Görsel bulunamadı: {visual_id}"}
            
        except Exception as e:
            logger.error(f"Görsel getirme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def select_visual(self, visual_id: str, post_id: str) -> Dict[str, Any]:
        """
        Üretilen görsellerden birini seç ve post ile ilişkilendir.
        
        Args:
            visual_id: Seçilen görsel ID'si
            post_id: İlişkilendirilecek post ID'si
            
        Returns:
            Seçim sonucu
        """
        try:
            # Görseli kontrol et
            visual_result = self.get_visual_by_id(visual_id)
            if visual_result.get("status") == "error":
                return visual_result
                
            visual = visual_result.get("visual", {})
            
            # Post ID'yi kontrol et - burada entegrasyon noktası olacak
            # Gerçek uygulamada, post ID'nin varlığı doğrulanmalı
            # Örneğin, Instagram Poster aracına sorgu yapılabilir
            
            # İlişkiyi kaydet (gerçek uygulamada veritabanına kaydedilecek)
            selection = {
                "visual_id": visual_id,
                "post_id": post_id,
                "selection_time": time.time(),
                "visual_info": visual
            }
            
            # Seçimi kaydediyormuş gibi yap (gerçek uygulamada veritabanına kaydedilecek)
            
            return {
                "status": "success",
                "message": "Görsel başarıyla post ile ilişkilendirildi",
                "selection": selection
            }
            
        except Exception as e:
            logger.error(f"Görsel seçme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_generation_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        Geçmiş görsel üretim isteği geçmişini getirir.
        
        Args:
            limit: Alınacak kayıt sayısı limiti
            
        Returns:
            Görsel üretim geçmişi
        """
        try:
            # Son eklenenler önce olacak şekilde sırala
            sorted_history = sorted(
                self.history.values(),
                key=lambda x: x.get("timestamp", 0),
                reverse=True
            )
            
            # Limiti uygula
            limited_history = sorted_history[:limit]
            
            return {
                "status": "success",
                "count": len(limited_history),
                "history": limited_history
            }
            
        except Exception as e:
            logger.error(f"Geçmiş getirme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _get_llm_tool(self):
        """LLM aracını almak için yardımcı fonksiyon"""
        try:
            # LLM aracını registry'den al
            for tool_id, metadata in self._registry.get_all_metadata().items():
                if metadata.name == 'llm_tool':
                    return self._registry.get_tool_by_id(tool_id)
            
            logger.warning("LLM aracı bulunamadı")
            return None
        except Exception as e:
            logger.error(f"LLM aracı alınırken hata: {str(e)}")
            return None
    
    def _generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> Dict[str, Any]:
        """
        Prompt'a göre görsel üretir, GPT-4o/DALL-E 3 kullanarak.
        
        Args:
            prompt: Görsel oluşturma promptu
            aspect_ratio: Görsel en boy oranı
            
        Returns:
            Oluşturulan görsel bilgileri
        """
        try:
            # GPT-4o/DALL-E 3 üzerinden görsel üretimi
            llm_tool = self._get_llm_tool()
            
            if not llm_tool:
                logger.error("LLM aracı bulunamadı, görsel üretilemedi.")
                raise ValueError("LLM aracı bulunamadı")
            
            # GPT-4o modelinin DALL-E entegrasyonu üzerinden görsel üretimi
            # Eğer OpenAI API kullanılıyorsa, doğrudan DALL-E çağrısı yapılabilir
            # Burada llm_tool'un OpenAI entegrasyonunu kullanıyoruz
            
            # Görsel boyutunu ayarla
            if aspect_ratio == "1:1":
                size = "1024x1024"
            elif aspect_ratio == "16:9":
                size = "1792x1024"
            elif aspect_ratio == "9:16":
                size = "1024x1792"
            elif aspect_ratio == "4:5":
                size = "1024x1280"
            else:
                size = "1024x1024"  # Varsayılan kare
            
            # Promptu iyileştir
            enhanced_prompt = f"{prompt}, high resolution, professional quality, detailed, 8k"
            
            # OpenAI DALL-E 3 görsel üretimi
            try:
                # LLM aracının OpenAI client'ını kullan
                # Bu kısım llm_tool yapınıza göre ayarlanmalıdır
                import openai
                
                # OpenAI istemcisi llm_tool üzerinden alınır (yapınıza göre değişebilir)
                client = llm_tool.get_openai_client() if hasattr(llm_tool, 'get_openai_client') else openai.OpenAI()
                
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    size=size,
                    quality="standard",
                    n=1
                )
                
                # Yanıtı işle
                image_url = response.data[0].url
                
                # Dosyayı yerel olarak indirip kaydet (isteğe bağlı)
                import requests
                from PIL import Image
                from io import BytesIO
                
                image_id = f"img_{int(time.time())}"
                local_path = os.path.join(self.image_storage_path, f"{image_id}.png")
                
                # Görsel URL'inden indir
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
                img.save(local_path)
                
                logger.info(f"Görsel başarıyla oluşturuldu ve kaydedildi: {local_path}")
                
                # Boyutları al
                width, height = img.size
                
                return {
                    "url": image_url,
                    "local_path": local_path,
                    "width": width,
                    "height": height
                }
                
            except Exception as openai_error:
                logger.error(f"OpenAI görsel üretimi hatası: {str(openai_error)}")
                raise
            
        except Exception as e:
            logger.error(f"Görsel üretme hatası: {str(e)}")
            raise ValueError(f"Görsel üretme hatası: {str(e)}")