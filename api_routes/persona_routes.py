"""
Persona routes - persona management and execution
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def register_persona_routes(app, coordinator_a2a=None, persona_factory=None, db_manager=None):
    """Register persona management routes"""
    
    @app.route('/api/personas', methods=['GET'])
    def get_personas():
        """Tüm personaları listele"""
        try:
            if coordinator_a2a:
                personas = coordinator_a2a.get_all_personas()
                return jsonify({
                    "status": "success",
                    "personas": personas
                })
            else:
                # Fallback: mock persona listesi
                mock_personas = [
                    {
                        "id": "assistant",
                        "name": "Genel Asistan",
                        "type": "assistant",
                        "status": "active",
                        "description": "Genel amaçlı AI asistanı"
                    },
                    {
                        "id": "social_media",
                        "name": "Sosyal Medya Uzmanı",
                        "type": "social_media",
                        "status": "inactive",
                        "description": "Instagram ve sosyal medya içerik uzmanı"
                    }
                ]
                return jsonify({
                    "status": "success",
                    "personas": mock_personas
                })
        except Exception as e:
            logger.error(f"Personalar listelenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas', methods=['POST'])
    def create_persona():
        """Yeni persona oluştur"""
        try:
            data = request.get_json()
            persona_type = data.get('type')
            persona_config = data.get('config', {})
            
            if not persona_type:
                return jsonify({"status": "error", "message": "Persona type required"}), 400
            
            if persona_factory:
                persona = persona_factory.create_persona(persona_type, persona_config)
                return jsonify({
                    "status": "success",
                    "persona_id": persona.persona_id,
                    "message": "Persona created successfully"
                })
            else:
                return jsonify({"status": "error", "message": "Persona factory not available"}), 500
                
        except Exception as e:
            logger.error(f"Persona oluşturulurken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>', methods=['GET'])
    def get_persona(persona_id):
        """Persona detaylarını getir"""
        try:
            if coordinator_a2a:
                persona = coordinator_a2a.get_persona(persona_id)
                if persona:
                    return jsonify({
                        "status": "success",
                        "persona": persona.to_dict()
                    })
                else:
                    return jsonify({"status": "error", "message": "Persona not found"}), 404
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/start', methods=['POST'])
    def start_persona(persona_id):
        """Persona başlat"""
        try:
            if coordinator_a2a:
                result = coordinator_a2a.start_persona(persona_id)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona başlatılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/stop', methods=['POST'])
    def stop_persona(persona_id):
        """Persona durdur"""
        try:
            if coordinator_a2a:
                result = coordinator_a2a.stop_persona(persona_id)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona durdurulurken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/status', methods=['GET'])
    def get_persona_status(persona_id):
        """Persona durumunu getir"""
        try:
            if coordinator_a2a:
                status = coordinator_a2a.get_persona_status(persona_id)
                return jsonify({
                    "status": "success",
                    "persona_status": status
                })
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona durumu getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/restart', methods=['POST'])
    def restart_persona(persona_id):
        """Persona yeniden başlat"""
        try:
            if coordinator_a2a:
                result = coordinator_a2a.restart_persona(persona_id)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona yeniden başlatılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/execute-task', methods=['POST'])
    def execute_persona_task(persona_id):
        """Persona ile görev çalıştır"""
        try:
            data = request.get_json()
            task_data = data.get('task', {})
            
            if coordinator_a2a:
                result = coordinator_a2a.execute_persona_task(persona_id, task_data)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona görevi çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/data', methods=['GET'])
    def get_persona_data(persona_id):
        """Persona verilerini getir"""
        try:
            if coordinator_a2a:
                data = coordinator_a2a.get_persona_data(persona_id)
                return jsonify({
                    "status": "success",
                    "data": data
                })
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona verileri getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/personas/<persona_id>/data', methods=['POST'])
    def update_persona_data(persona_id):
        """Persona verilerini güncelle"""
        try:
            data = request.get_json()
            updates = data.get('data', {})
            
            if coordinator_a2a:
                result = coordinator_a2a.update_persona_data(persona_id, updates)
                return jsonify(result)
            else:
                return jsonify({"status": "error", "message": "Coordinator not available"}), 500
        except Exception as e:
            logger.error(f"Persona verileri güncellenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("Persona routes registered")