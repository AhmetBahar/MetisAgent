"""
Social Media Workflow Tool Package - Dynamic Plugin
LLM-driven 8-step social media campaign management with hybrid graph memory
"""

import sys
import os
import json

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Read class configuration to prevent hardcoded corruption
class_config_path = os.path.join(current_dir, "tool_class.json")
try:
    with open(class_config_path, 'r') as f:
        config = json.load(f)
    actual_class_name = config["class_name"]
    module_name = config["module_name"]
except:
    actual_class_name = "SocialMediaWorkflowTool"
    module_name = "social_media_workflow_tool"

try:
    # Dynamic import using config
    module = __import__(module_name, fromlist=[actual_class_name, 'register_tool'])
    globals()[actual_class_name] = getattr(module, actual_class_name)
    globals()['register_tool'] = getattr(module, 'register_tool')
except ImportError:
    # Fallback import
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(current_dir, f"{module_name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    globals()[actual_class_name] = getattr(module, actual_class_name)
    globals()['register_tool'] = getattr(module, 'register_tool')

__all__ = [actual_class_name, 'register_tool']