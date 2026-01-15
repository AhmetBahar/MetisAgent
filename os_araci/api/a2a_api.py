# api/a2a_api.py
from flask import Blueprint, request, jsonify
import logging
import asyncio
from a2a_protocol.protocol import A2AProtocol
from personas.persona_factory import PersonaFactory

logger = logging.getLogger(__name__)

# A2A API Blueprint
a2a_api = Blueprint('a2a_api', __name__)

# A2A Protokolü örneği
a2a_protocol = A2AProtocol()
persona_factory = PersonaFactory()

# api/a2a_api.py (devam)
# Asenkron fonksiyonları Flask ile çalıştırmak için yardımcı fonksiyon
def run_async(func):
    """Asenkron fonksiyonu senkron şekilde çalıştır"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func)
    finally:
        loop.close()

# API Başlatma
@a2a_api.before_app_first_request
def initialize_a2a():
    """A2A protokolünü başlat"""
    try:
        run_async(a2a_protocol.initialize())
        logger.info("A2A API başlatıldı")
    except Exception as e:
        logger.error(f"A2A API başlatma hatası: {str(e)}")

# API Kapatma
@a2a_api.teardown_app_request
def shutdown_a2a(exception=None):
    """Uygulama kapanırken temizlik yap"""
    try:
        run_async(a2a_protocol.shutdown())
        logger.info("A2A API kapatıldı")
    except Exception as e:
        logger.error(f"A2A API kapatma hatası: {str(e)}")

# ------- API ENDPOINTS -------

@a2a_api.route('/api/a2a/personas', methods=['GET'])
def list_personas():
    """Tüm aktif personaları listele"""
    try:
        persona_statuses = run_async(a2a_protocol.get_persona_status())
        return jsonify({
            "status": "success",
            "personas": persona_statuses
        })
    except Exception as e:
        logger.error(f"Persona listeleme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/personas/<persona_id>', methods=['GET'])
def get_persona(persona_id):
    """Belirli bir personanın durumunu al"""
    try:
        persona_status = run_async(a2a_protocol.get_persona_status(persona_id))
        if "error" in persona_status:
            return jsonify({"status": "error", "message": persona_status["error"]}), 404
        
        return jsonify({
            "status": "success",
            "persona": persona_status
        })
    except Exception as e:
        logger.error(f"Persona bilgisi alma hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/personas', methods=['POST'])
def create_persona():
    """Yeni bir persona oluştur ve başlat"""
    try:
        data = request.json
        template_id = data.get('template_id')
        config = data.get('config', {})
        
        if not template_id:
            return jsonify({"status": "error", "message": "template_id required"}), 400
        
        # Personayı oluştur ve başlat
        persona = run_async(a2a_protocol.create_and_start_persona(template_id, **config))
        
        if not persona:
            return jsonify({"status": "error", "message": f"Failed to create persona from template: {template_id}"}), 500
        
        return jsonify({
            "status": "success",
            "persona_id": persona.persona_id,
            "name": persona.name,
            "description": persona.description
        })
    except Exception as e:
        logger.error(f"Persona oluşturma hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/personas/<persona_id>', methods=['DELETE'])
def stop_persona(persona_id):
    """Bir personayı durdur"""
    try:
        success = run_async(a2a_protocol.stop_persona(persona_id))
        
        if not success:
            return jsonify({"status": "error", "message": f"Failed to stop persona: {persona_id}"}), 404
        
        return jsonify({
            "status": "success",
            "message": f"Persona stopped: {persona_id}"
        })
    except Exception as e:
        logger.error(f"Persona durdurma hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/templates', methods=['GET'])
def list_templates():
    """Kullanılabilir tüm persona şablonlarını listele"""
    try:
        templates = persona_factory.list_available_templates()
        return jsonify({
            "status": "success",
            "templates": templates,
            "count": len(templates)
        })
    except Exception as e:
        logger.error(f"Şablon listeleme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    """Belirli bir şablonun detaylarını getir"""
    try:
        template = persona_factory.get_template(template_id)
        
        if not template:
            return jsonify({"status": "error", "message": f"Template not found: {template_id}"}), 404
        
        return jsonify({
            "status": "success",
            "template": template
        })
    except Exception as e:
        logger.error(f"Şablon bilgisi alma hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/messages', methods=['POST'])
def send_message():
    """Bir mesaj gönder"""
    try:
        data = request.json
        sender = data.get('sender')
        receiver = data.get('receiver')
        message_type = data.get('message_type')
        content = data.get('content', {})
        
        if not sender or not receiver or not message_type:
            return jsonify({"status": "error", "message": "sender, receiver, and message_type required"}), 400
        
        # Mesajı gönder
        message_id = run_async(a2a_protocol.send_message(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content
        ))
        
        return jsonify({
            "status": "success",
            "message_id": message_id
        })
    except Exception as e:
        logger.error(f"Mesaj gönderme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/broadcast', methods=['POST'])
def broadcast_message():
    """Broadcast mesajı gönder"""
    try:
        data = request.json
        sender = data.get('sender')
        message_type = data.get('message_type')
        content = data.get('content', {})
        
        if not sender or not message_type:
            return jsonify({"status": "error", "message": "sender and message_type required"}), 400
        
        # Broadcast mesajı gönder
        message_id = run_async(a2a_protocol.broadcast(
            sender=sender,
            message_type=message_type,
            content=content
        ))
        
        return jsonify({
            "status": "success",
            "message_id": message_id
        })
    except Exception as e:
        logger.error(f"Broadcast mesajı gönderme hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@a2a_api.route('/api/a2a/task', methods=['POST'])
def execute_task_with_persona():
    """Görevi bir persona ile çalıştır"""
    try:
        data = request.json
        task = data.get('task')
        context = data.get('context', {})
        target_persona = data.get('target_persona')
        timeout = data.get('timeout', 120.0)
        
        if not task:
            return jsonify({"status": "error", "message": "task required"}), 400
        
        # MCPCoordinator'a A2A protokolü entegrasyonunu al
        from coordination.coordinator_a2a import MCPCoordinatorA2A
        from os_araci.coordination.coordinator import MCPCoordinator
        
        coordinator = MCPCoordinator()
        coordinator_a2a = MCPCoordinatorA2A(coordinator)
        
        # Görevi çalıştır
        result = run_async(coordinator_a2a.execute_task_with_persona(
            task=task,
            context=context,
            target_persona=target_persona,
            timeout=timeout
        ))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Görev çalıştırma hatası: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500