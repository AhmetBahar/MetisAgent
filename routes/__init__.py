"""
Routes package for MetisAgent
Contains modular blueprint routes for different API endpoints
"""

from .persona_routes import persona_bp, init_persona_routes
from .plugin_routes import plugin_bp, init_plugin_routes

__all__ = ['persona_bp', 'plugin_bp', 'init_persona_routes', 'init_plugin_routes']