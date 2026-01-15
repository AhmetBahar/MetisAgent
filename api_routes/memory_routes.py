"""
Memory routes - memory storage, retrieval, search, and management
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def get_memory_manager(registry):
    """Helper function to get memory manager instance from registry"""
    memory_manager = None
    tool_id = None
    
    try:
        tools = registry.get_all_tools()
        for tid, tool_data in tools.items():
            if tid == 'memory_manager' or tool_data.get('name') == 'memory_manager':
                memory_manager = registry.get_tool(tid)
                tool_id = tid
                break
    except Exception as e:
        logger.debug(f"Memory manager lookup error: {str(e)}")
        pass
        
    return memory_manager, tool_id

def register_memory_routes(app, registry, memory_manager=None):
    """Register memory management routes"""
    
    @app.route('/api/memory/store', methods=['POST'])
    def store_memory():
        """Bellek kaydı oluştur API endpoint'i"""
        try:
            data = request.get_json()
            
            if memory_manager:
                result = memory_manager.store_memory(
                    content=data.get('content'),
                    category=data.get('category', 'general'),
                    tags=data.get('tags', [])
                )
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "store_memory", 
                                              content=data.get('content'),
                                              category=data.get('category', 'general'),
                                              tags=data.get('tags', []))
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Bellek kaydı oluşturulurken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/memory/retrieve', methods=['GET'])
    def retrieve_memories():
        """Bellek kayıtlarını getir API endpoint'i"""
        try:
            query = request.args.get('query')
            category = request.args.get('category')
            tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
            limit = int(request.args.get('limit', 10))
            
            if memory_manager:
                result = memory_manager.retrieve_memories(
                    query=query,
                    category=category,
                    tags=tags,
                    limit=limit
                )
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "retrieve_memories", 
                                              query=query,
                                              category=category,
                                              tags=tags,
                                              limit=limit)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Bellek kayıtları getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/memory/search', methods=['GET'])
    def search_memories_by_similarity():
        """Benzerliğe göre bellek kayıtlarını ara API endpoint'i"""
        try:
            query = request.args.get('query')
            limit = int(request.args.get('limit', 5))
            
            if not query:
                return jsonify({"status": "error", "message": "Query parameter required"}), 400
            
            if memory_manager:
                result = memory_manager.search_by_similarity(query=query, limit=limit)
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "search_by_similarity", 
                                              query=query,
                                              limit=limit)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Benzerlik araması yapılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/memory/update/<int:memory_id>', methods=['PUT'])
    def update_memory(memory_id):
        """Bellek kaydını güncelle API endpoint'i"""
        try:
            data = request.get_json()
            
            if memory_manager:
                result = memory_manager.update_memory(
                    memory_id=memory_id,
                    content=data.get('content'),
                    category=data.get('category'),
                    tags=data.get('tags')
                )
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "update_memory", 
                                              memory_id=memory_id,
                                              content=data.get('content'),
                                              category=data.get('category'),
                                              tags=data.get('tags'))
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Bellek kaydı güncellenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/memory/delete/<int:memory_id>', methods=['DELETE'])
    def delete_memory(memory_id):
        """Bellek kaydını sil API endpoint'i"""
        try:
            if memory_manager:
                result = memory_manager.delete_memory(memory_id=memory_id)
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "delete_memory", memory_id=memory_id)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Bellek kaydı silinirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/memory/clear', methods=['POST'])
    def clear_all_memories():
        """Tüm bellek kayıtlarını temizle API endpoint'i"""
        try:
            if memory_manager:
                result = memory_manager.clear_all_memories()
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "clear_all_memories")
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Bellek kayıtları temizlenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/memory/user/<username>', methods=['POST'])
    def set_memory_user(username):
        """Bellek yöneticisi için aktif kullanıcıyı ayarla API endpoint'i"""
        try:
            if memory_manager:
                result = memory_manager.set_user(username=username)
            else:
                mm, tool_id = get_memory_manager(registry)
                if not mm:
                    return jsonify({"status": "error", "message": "Memory manager not found"}), 404
                
                result = registry.call_handler(tool_id, "set_user", username=username)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Bellek kullanıcısı ayarlanırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("Memory routes registered")