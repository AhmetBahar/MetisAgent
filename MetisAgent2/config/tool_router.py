#!/usr/bin/env python3
"""
Configurable Tool Routing System
Dynamic tool selection based on configurable patterns and weights
"""

import json
import re
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolMatch:
    """Tool match result with confidence score"""
    tool_name: str
    confidence: float
    matched_patterns: List[str]
    total_weight: float

class ConfigurableToolRouter:
    """Dynamic tool routing based on configurable patterns"""
    
    def __init__(self, config_file: str = "config/tool_routing.json"):
        self.config_file = config_file
        self.routing_config = {}
        self.tool_patterns = {}
        self.routing_settings = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load tool routing configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.tool_patterns = config.get("tool_routing_patterns", {})
                self.routing_settings = config.get("routing_config", {})
                
                # Compile regex patterns for performance
                self._compile_patterns()
                
                logger.info(f"Loaded tool routing configuration: {len(self.tool_patterns)} tools")
            else:
                logger.error(f"Tool routing config file not found: {self.config_file}")
                self._create_fallback_config()
        except Exception as e:
            logger.error(f"Error loading tool routing configuration: {e}")
            self._create_fallback_config()
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        for tool_name, tool_config in self.tool_patterns.items():
            patterns = tool_config.get("patterns", [])
            compiled_patterns = []
            
            for pattern_config in patterns:
                try:
                    pattern = pattern_config["pattern"]
                    flags = re.IGNORECASE if not self.routing_settings.get("case_sensitive", False) else 0
                    compiled = re.compile(pattern, flags)
                    
                    pattern_config["compiled"] = compiled
                    compiled_patterns.append(pattern_config)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern in {tool_name}: {pattern} - {e}")
            
            tool_config["compiled_patterns"] = compiled_patterns
    
    def _create_fallback_config(self):
        """Create minimal fallback configuration if config file fails"""
        logger.warning("Using fallback tool routing configuration")
        self.tool_patterns = {
            "llm_tool": {
                "description": "Default LLM tool",
                "priority": 1,
                "compiled_patterns": []
            }
        }
        self.routing_settings = {
            "default_tool": "llm_tool",
            "confidence_threshold": 0.1
        }
    
    def detect_language(self, text: str) -> str:
        """Simple language detection"""
        if not self.routing_settings.get("language_detection", True):
            return "both"
        
        # Simple heuristics for Turkish vs English
        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
        turkish_words = ['ve', 'ile', 'için', 'olan', 'bir', 'bu', 'şu', 'o', 'ben', 'sen', 'biz', 'siz', 'onlar']
        english_words = ['the', 'and', 'with', 'for', 'that', 'this', 'a', 'an', 'is', 'are', 'was', 'were']
        
        text_lower = text.lower()
        
        # Check for Turkish characters
        has_turkish_chars = any(char in turkish_chars for char in text)
        
        # Count Turkish and English words
        turkish_count = sum(1 for word in turkish_words if word in text_lower)
        english_count = sum(1 for word in english_words if word in text_lower)
        
        if has_turkish_chars or turkish_count > english_count:
            return "turkish"
        elif english_count > 0:
            return "english"
        else:
            return "both"
    
    def calculate_tool_confidence(self, text: str, tool_name: str, tool_config: Dict) -> ToolMatch:
        """Calculate confidence score for a specific tool"""
        matched_patterns = []
        total_weight = 0.0
        
        detected_lang = self.detect_language(text)
        language_weights = self.routing_settings.get("language_weights", {"turkish": 1.2, "english": 1.0, "both": 1.1})
        
        compiled_patterns = tool_config.get("compiled_patterns", [])
        
        for pattern_config in compiled_patterns:
            compiled_pattern = pattern_config.get("compiled")
            if not compiled_pattern:
                continue
            
            pattern_lang = pattern_config.get("language", "both")
            pattern_weight = pattern_config.get("weight", 1.0)
            
            # Apply language matching bonus/penalty
            lang_multiplier = 1.0
            if pattern_lang == "both" or pattern_lang == detected_lang:
                lang_multiplier = language_weights.get(pattern_lang, 1.0)
            elif pattern_lang != detected_lang:
                lang_multiplier = 0.7  # Slight penalty for language mismatch
            
            # Check if pattern matches
            if compiled_pattern.search(text):
                effective_weight = pattern_weight * lang_multiplier
                total_weight += effective_weight
                matched_patterns.append(pattern_config["pattern"])
        
        # Apply tool priority bonus
        priority_bonus = tool_config.get("priority", 5) * 0.1
        total_weight += priority_bonus
        
        # Normalize confidence (simple approach)
        max_possible_weight = sum(p.get("weight", 1.0) for p in compiled_patterns) + priority_bonus
        confidence = min(total_weight / max(max_possible_weight, 1.0), 1.0) if max_possible_weight > 0 else 0.0
        
        return ToolMatch(
            tool_name=tool_name,
            confidence=confidence,
            matched_patterns=matched_patterns,
            total_weight=total_weight
        )
    
    def find_best_tool(self, user_input: str) -> Tuple[str, float, List[str]]:
        """Find the best tool for user input"""
        if not user_input or not user_input.strip():
            default_tool = self.routing_settings.get("default_tool", "llm_tool")
            return default_tool, 0.1, []
        
        text = user_input.strip()
        tool_matches = []
        
        # Calculate confidence for each tool
        for tool_name, tool_config in self.tool_patterns.items():
            match = self.calculate_tool_confidence(text, tool_name, tool_config)
            if match.confidence > 0:
                tool_matches.append(match)
        
        # Sort by confidence (descending)
        tool_matches.sort(key=lambda x: x.confidence, reverse=True)
        
        # Apply confidence threshold
        confidence_threshold = self.routing_settings.get("confidence_threshold", 0.3)
        
        if tool_matches and tool_matches[0].confidence >= confidence_threshold:
            best_match = tool_matches[0]
            return best_match.tool_name, best_match.confidence, best_match.matched_patterns
        else:
            # Return default tool if no confident match
            default_tool = self.routing_settings.get("default_tool", "llm_tool")
            return default_tool, 0.1, []
    
    def get_tool_suggestions(self, user_input: str, limit: int = 3) -> List[ToolMatch]:
        """Get multiple tool suggestions with confidence scores"""
        if not user_input or not user_input.strip():
            return []
        
        text = user_input.strip()
        tool_matches = []
        
        for tool_name, tool_config in self.tool_patterns.items():
            match = self.calculate_tool_confidence(text, tool_name, tool_config)
            if match.confidence > 0:
                tool_matches.append(match)
        
        # Sort by confidence and return top matches
        tool_matches.sort(key=lambda x: x.confidence, reverse=True)
        return tool_matches[:limit]
    
    def add_custom_pattern(self, tool_name: str, pattern: str, weight: float = 5.0, language: str = "both"):
        """Add custom pattern at runtime"""
        if tool_name not in self.tool_patterns:
            self.tool_patterns[tool_name] = {
                "description": f"Custom tool: {tool_name}",
                "priority": 5,
                "patterns": [],
                "compiled_patterns": []
            }
        
        pattern_config = {
            "pattern": pattern,
            "weight": weight,
            "language": language
        }
        
        try:
            flags = re.IGNORECASE if not self.routing_settings.get("case_sensitive", False) else 0
            compiled = re.compile(pattern, flags)
            pattern_config["compiled"] = compiled
            
            self.tool_patterns[tool_name]["compiled_patterns"].append(pattern_config)
            logger.info(f"Added custom pattern to {tool_name}: {pattern}")
        except re.error as e:
            logger.error(f"Failed to add custom pattern: {pattern} - {e}")
    
    def reload_configuration(self):
        """Reload configuration from file"""
        logger.info("Reloading tool routing configuration...")
        self._load_configuration()
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing system statistics"""
        return {
            "total_tools": len(self.tool_patterns),
            "total_patterns": sum(len(config.get("compiled_patterns", [])) for config in self.tool_patterns.values()),
            "configuration": self.routing_settings,
            "tools": {
                name: {
                    "pattern_count": len(config.get("compiled_patterns", [])),
                    "priority": config.get("priority", 0),
                    "description": config.get("description", "")
                }
                for name, config in self.tool_patterns.items()
            }
        }

# Global router instance
_tool_router = ConfigurableToolRouter()

# Convenience functions
def find_best_tool(user_input: str) -> Tuple[str, float, List[str]]:
    """Find best tool for user input"""
    return _tool_router.find_best_tool(user_input)

def get_tool_suggestions(user_input: str, limit: int = 3) -> List[ToolMatch]:
    """Get tool suggestions"""
    return _tool_router.get_tool_suggestions(user_input, limit)

def reload_routing_config():
    """Reload routing configuration"""
    _tool_router.reload_configuration()

def get_router() -> ConfigurableToolRouter:
    """Get router instance"""
    return _tool_router

# Export main classes and functions
__all__ = [
    'ConfigurableToolRouter', 'ToolMatch',
    'find_best_tool', 'get_tool_suggestions', 'reload_routing_config', 'get_router'
]