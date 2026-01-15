# examples/social_media_workflow_plugin.py
from os_araci.plugins.workflow_plugin import WorkflowPlugin
from typing import Dict, Any, List, Optional

class SocialMediaWorkflowPlugin(WorkflowPlugin):
    """Sosyal medya iş akışı için özelleştirilmiş plugin"""
    
    def __init__(self, 
                persona_id: str, 
                name: str,
                description: str,
                **kwargs):
        
        # Sosyal medya iş akışı adımları
        workflow_steps = [
            {
                "step_id": "briefing",
                "name": "Brifing",
                "description": "Amacı, hedef kitleyi, ana mesajı ve platformları tanımlama",
                "required_inputs": ["purpose", "target_audience", "main_message", "platforms"],
                "responsible_roles": ["Müşteri", "Marka Yöneticisi", "Pazarlama Ekibi", "Stratejist"]
            },
            {
                "step_id": "creative_idea",
                "name": "Yaratıcı Fikir Üretimi",
                "description": "Gönderi türünü, konsepti, tonu ve görselleri belirleme",
                "required_inputs": ["post_type", "concept", "tone", "visual_ideas", "formats"],
                "responsible_roles": ["Sosyal Medya Uzmanı", "Yazar", "Sanat Yönetmeni"]
            },
            {
                "step_id": "post_content",
                "name": "Post İçeriği",
                "description": "Gönderi başlığı/mesajı yazma, video senaryosu hazırlama, görsel tanımlama",
                "required_inputs": ["post_title", "post_message", "video_script", "visual_description"],
                "responsible_roles": ["Yazar", "İçerik Yöneticisi", "Yaratıcı Ekip"]
            },
            {
                "step_id": "sharing_content",
                "name": "Paylaşım İçeriği",
                "description": "Paylaşım metnini yazma, emojileri ve hashtagleri ekleme",
                "required_inputs": ["share_text", "emojis", "hashtags"],
                "responsible_roles": ["Sosyal Medya Uzmanı", "İçerik Yöneticisi"]
            },
            {
                "step_id": "visual_production",
                "name": "Görsel Prodüksiyon",
                "description": "Statik post bileşenlerini tasarlama, video planlama, kurgu yapma",
                "required_inputs": ["static_designs", "video_plan", "subtitles"],
                "responsible_roles": ["SM Tasarımcısı", "Motion Designer"]
            },
            {
                "step_id": "approval",
                "name": "Onay",
                "description": "Brif ve yönlendirmelere uygunluğu kontrol etme, müşteri onayı alma",
                "required_inputs": ["validation_points", "client_approval"],
                "responsible_roles": ["SM Uzmanı", "Kreatif Direktör", "Marka Yöneticisi", "Müşteri"]
            },
            {
                "step_id": "scheduling",
                "name": "Planlama ve Yayınlama",
                "description": "Programlama araçlarına giriş ve yükleme, zamanlama, kontrol",
                "required_inputs": ["publishing_tool", "schedule_time", "links_tags_check"],
                "responsible_roles": ["Sosyal Medya Uzmanı"]
            },
            {
                "step_id": "monitoring",
                "name": "İzleme ve Etkileşim",
                "description": "Yorumlara yanıt verme, uygunsuz içeriği denetleme, geri bildirimleri işaretleme",
                "required_inputs": ["response_strategy", "moderation_rules"],
                "responsible_roles": ["SM Uzmanı", "Müşteri Yöneticisi"]
            },
            {
                "step_id": "reporting",
                "name": "Raporlama ve Analiz",
                "description": "Ölçümleri değerlendirme, karşılaştırma, rapor hazırlama",
                "required_inputs": ["metrics", "benchmarks", "report_template"],
                "responsible_roles": ["SM Uzmanı", "Medya Planlama Uzmanı"]
            }
        ]
        
        # İş akışı geçişleri (opsiyonel)
        workflow_transitions = [
            {
                "from_step": "briefing",
                "to_step": "creative_idea"
            },
            {
                "from_step": "creative_idea",
                "to_step": "post_content"
            },
            {
                "from_step": "post_content",
                "to_step": "sharing_content"
            },
            {
                "from_step": "sharing_content",
                "to_step": "visual_production"
            },
            {
                "from_step": "visual_production",
                "to_step": "approval"
            },
            {
                "from_step": "approval",
                "to_step": "scheduling",
                "condition": "approval_granted"  # Örnek koşul
            },
            {
                "from_step": "approval",
                "to_step": "post_content",
                "condition": "revision_needed"  # Örnek koşul
            },
            {
                "from_step": "scheduling",
                "to_step": "monitoring"
            },
            {
                "from_step": "monitoring",
                "to_step": "reporting"
            }
        ]
        
        # Ana sınıfın başlatıcısını çağır
        super().__init__(
            persona_id=persona_id,
            name=name,
            description=description,
            workflow_steps=workflow_steps,
            workflow_transitions=workflow_transitions,
            **kwargs
        )