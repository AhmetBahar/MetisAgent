"""
RMMS Workflow Node Definitions
Based on MetisEngine WorkflowExecutor.cs and ReactFlow frontend nodeTypes.js
"""

NODE_TYPES = {
    "circularNode": {
        "description": "Start/End node - Marks the beginning or end of workflow",
        "required_data": ["label"],
        "data_schema": {
            "label": "string - 'Start' or 'End'"
        },
        "example": {
            "id": "0",
            "type": "circularNode",
            "data": {"label": "Start"},
            "position": {"x": 250, "y": 5}
        }
    },

    "Condition": {
        "description": "Condition evaluation node - Evaluates a condition and branches workflow",
        "required_data": ["selectedCondition", "selectedVariable1", "selectedVariable2", "inputType1", "inputType2"],
        "alternative_data": ["conditionExpression"],
        "data_schema": {
            "selectedCondition": "string - Comparison operator: '==', '!=', '>', '<', '>=', '<='",
            "selectedVariable1": "string - First variable ID or value",
            "selectedVariable2": "string - Second variable ID or value",
            "inputType1": "string - 'tag', 'variable', 'constant'",
            "inputType2": "string - 'tag', 'variable', 'constant'",
            "conditionExpression": "string - Alternative: Full expression e.g., 'HOUR(NOW()) == 0 && MINUTE(NOW()) < 15'"
        },
        "example": {
            "id": "1",
            "type": "Condition",
            "data": {
                "label": "Check Temperature",
                "selectedCondition": ">",
                "selectedVariable1": "11445",
                "selectedVariable2": "35",
                "inputType1": "tag",
                "inputType2": "constant"
            },
            "position": {"x": 250, "y": 100}
        }
    },

    "And": {
        "description": "Logical AND - Returns true if all connected conditions are true",
        "required_data": [],
        "data_schema": {
            "label": "string - Node label"
        },
        "example": {
            "id": "2",
            "type": "And",
            "data": {"label": "AND Gate"},
            "position": {"x": 250, "y": 200}
        }
    },

    "Or": {
        "description": "Logical OR - Returns true if any connected condition is true",
        "required_data": [],
        "data_schema": {
            "label": "string - Node label"
        },
        "example": {
            "id": "2",
            "type": "Or",
            "data": {"label": "OR Gate"},
            "position": {"x": 250, "y": 200}
        }
    },

    "Xor": {
        "description": "Logical XOR - Returns true if exactly one condition is true",
        "required_data": [],
        "data_schema": {
            "label": "string - Node label"
        },
        "example": {
            "id": "2",
            "type": "Xor",
            "data": {"label": "XOR Gate"},
            "position": {"x": 250, "y": 200}
        }
    },

    "Not": {
        "description": "Logical NOT - Inverts the condition result",
        "required_data": [],
        "data_schema": {
            "label": "string - Node label"
        },
        "example": {
            "id": "2",
            "type": "Not",
            "data": {"label": "NOT Gate"},
            "position": {"x": 250, "y": 200}
        }
    },

    "Arithmetic": {
        "description": "Arithmetic/Math operations node - Evaluates mathematical expressions",
        "required_data": ["expression", "outputVariable", "expressionId"],
        "data_schema": {
            "expression": "string - Display expression",
            "outputVariable": "string - Variable ID to store result",
            "expressionId": "string - Expression with variable IDs for evaluation. Supports: abs, pow, sqrt, sin, cos, tan, log, log10, exp, ceiling, floor, round, min, max, PI, E, Now.Year, Now.Month, Now.Day, Now.Hour, Now.Minute"
        },
        "example": {
            "id": "3",
            "type": "Arithmetic",
            "data": {
                "label": "Calculate Average",
                "expression": "(Tag1 + Tag2) / 2",
                "outputVariable": "lv_average",
                "expressionId": "(11445 + 11446) / 2"
            },
            "position": {"x": 250, "y": 300}
        }
    },

    "Service": {
        "description": "Web Service call node - Calls external REST/SOAP APIs",
        "required_data": ["service", "method"],
        "data_schema": {
            "service": "object - {id: int, type: 'rest'|'soap', url: string}",
            "method": "object - {httpMethod: 'GET'|'POST'|'PUT'|'DELETE', path: string, name: string}",
            "parameterMappings": "object - Maps parameter IDs to variable IDs",
            "inputParameters": "array - [{id, name, type}]",
            "outputMappings": "object - Maps output IDs to variable IDs"
        },
        "example": {
            "id": "4",
            "type": "Service",
            "data": {
                "label": "Call Weather API",
                "service": {"id": 1, "type": "rest", "url": "https://api.weather.com"},
                "method": {"httpMethod": "GET", "path": "/current", "name": "getCurrentWeather"}
            },
            "position": {"x": 250, "y": 400}
        }
    },

    "Switch": {
        "description": "Switch/Case node - Routes workflow based on value matching",
        "required_data": ["switchVariable", "cases"],
        "data_schema": {
            "switchVariable": "string - Variable ID to evaluate",
            "cases": "array - [{value: string, targetNodeId: string}]"
        },
        "example": {
            "id": "5",
            "type": "Switch",
            "data": {
                "label": "Route by Status",
                "switchVariable": "lv_status",
                "cases": [
                    {"value": "active", "targetNodeId": "6"},
                    {"value": "inactive", "targetNodeId": "7"}
                ]
            },
            "position": {"x": 250, "y": 500}
        }
    },

    "For": {
        "description": "For loop node - Iterates a fixed number of times",
        "required_data": ["iterations", "counterVariable"],
        "data_schema": {
            "iterations": "int - Number of iterations",
            "counterVariable": "string - Variable ID for loop counter",
            "nestedNodes": "array - Nodes to execute in each iteration"
        },
        "example": {
            "id": "6",
            "type": "For",
            "data": {
                "label": "Loop 10 Times",
                "iterations": 10,
                "counterVariable": "lv_i"
            },
            "position": {"x": 250, "y": 600}
        }
    },

    "Loop": {
        "description": "While loop node - Iterates while condition is true",
        "required_data": ["condition"],
        "data_schema": {
            "condition": "string - Condition expression",
            "nestedNodes": "array - Nodes to execute in each iteration"
        },
        "example": {
            "id": "7",
            "type": "Loop",
            "data": {
                "label": "While Active",
                "condition": "lv_active == true"
            },
            "position": {"x": 250, "y": 700}
        }
    },

    "Scenario": {
        "description": "Call Workflow node - Executes another workflow (sub-workflow)",
        "required_data": ["workflowName"],
        "data_schema": {
            "workflowName": "string - Name of workflow to execute"
        },
        "example": {
            "id": "8",
            "type": "Scenario",
            "data": {
                "label": "Run Alarm Handler",
                "workflowName": "AlarmHandler"
            },
            "position": {"x": 250, "y": 800}
        }
    },

    "Email": {
        "description": "Email node - Sends email notification",
        "required_data": ["to", "subject", "message"],
        "data_schema": {
            "to": "string - Recipient email address",
            "subject": "string - Email subject",
            "message": "string - Email body (can include {variableName} placeholders)"
        },
        "example": {
            "id": "9",
            "type": "Email",
            "data": {
                "label": "Send Alert Email",
                "to": "operator@company.com",
                "subject": "Temperature Alert",
                "message": "Temperature is {Temperature} which exceeds threshold."
            },
            "position": {"x": 250, "y": 900}
        }
    },

    "SMS": {
        "description": "SMS node - Sends SMS notification",
        "required_data": ["phoneNumber", "message"],
        "alternative_fields": {"phoneNumber": "to"},
        "data_schema": {
            "phoneNumber": "string - Recipient phone number (or use 'to')",
            "to": "string - Alternative field for phone number",
            "message": "string - SMS message (can include {variableName} placeholders)"
        },
        "example": {
            "id": "10",
            "type": "SMS",
            "data": {
                "label": "Send SMS Alert",
                "phoneNumber": "+905551234567",
                "message": "Alert: Temperature is {Temperature}"
            },
            "position": {"x": 250, "y": 1000}
        }
    },

    "Alarm": {
        "description": "Alarm node - Creates an alarm in the system",
        "required_data": ["message", "severity", "variables"],
        "data_schema": {
            "message": "string - Alarm message (can include {tagName} placeholders)",
            "severity": "string - Alarm severity code",
            "variables": "array - [{tagName: string, id: string}] - Tags to include in message"
        },
        "example": {
            "id": "11",
            "type": "Alarm",
            "data": {
                "label": "High Temperature Alarm",
                "message": "Temperature {Temperature} exceeded limit!",
                "severity": "critical",
                "variables": [{"tagName": "Temperature", "id": "11445"}]
            },
            "position": {"x": 250, "y": 1100}
        }
    },

    "PLCCommand": {
        "description": "PLC Command node - Sends command to PLC/device via tag",
        "required_data": ["selectedTag", "commandValue", "tagInputType", "valueInputType"],
        "data_schema": {
            "selectedTag": "string - Tag ID to write to",
            "commandValue": "string - Value to write (tag ID or constant)",
            "tagInputType": "string - 'tag' or 'constant'",
            "valueInputType": "string - 'tag' or 'constant'"
        },
        "example": {
            "id": "12",
            "type": "PLCCommand",
            "data": {
                "label": "Set Fan Speed",
                "selectedTag": "11450",
                "commandValue": "100",
                "tagInputType": "tag",
                "valueInputType": "constant"
            },
            "position": {"x": 250, "y": 1200}
        }
    },

    "RisingEdge": {
        "description": "Rising Edge node - Detects when a condition changes from false to true",
        "required_data": ["condition"],
        "data_schema": {
            "condition": "string - Condition to monitor for rising edge"
        },
        "example": {
            "id": "13",
            "type": "RisingEdge",
            "data": {
                "label": "Detect Start",
                "condition": "11445 > 35"
            },
            "position": {"x": 250, "y": 1300}
        }
    }
}

# Edges connect nodes
EDGE_SCHEMA = {
    "id": "string - Unique edge ID (e.g., 'e1-2')",
    "source": "string - Source node ID",
    "target": "string - Target node ID",
    "sourceHandle": "string - Optional: 'true' or 'false' for condition branches",
    "label": "string - Optional: Edge label"
}

# CRITICAL WORKFLOW EXECUTION RULES
WORKFLOW_RULES = {
    "branching": """
    IMPORTANT: WorkflowExecutor follows a SINGLE execution path.

    BRANCHING RULES:
    1. Only Condition and Switch nodes can have multiple outgoing edges (branches)
    2. All other nodes (including Start/circularNode) must have exactly ONE outgoing edge
    3. Condition nodes branch via sourceHandle: 'true' or 'false'
    4. Switch nodes branch via case matching

    INVALID: Start → [Node1, Node2] (parallel branches from Start)
    VALID:   Start → Condition → (true: Node1, false: Node2)

    For AND/OR logic with multiple conditions:
    - Connect conditions in SERIES, not parallel
    - Example: Start → Condition1 → Condition2 → And → Action → End
    - Each Condition's true branch goes to next step
    - Each Condition's false branch can go directly to End
    """,

    "tag_format": """
    TAG REFERENCE FORMAT:
    - Tag references must use 'tag_XXXX' format (e.g., 'tag_7228')
    - inputType for tag selection should be 'select' (not 'tag')
    - inputType for constant values should be 'text' (not 'constant')

    Example Condition node data:
    {
        "selectedVariable1": "tag_7228",  // Tag reference
        "selectedVariable2": "35",         // Constant value
        "inputType1": "select",            // For tag
        "inputType2": "text"               // For constant
    }
    """,

    "execution_flow": """
    EXECUTION FLOW:
    1. Workflow starts at circularNode with label 'Start'
    2. Executor follows edges sequentially
    3. At Condition nodes, evaluates and follows true/false branch
    4. At Switch nodes, matches value and follows corresponding branch
    5. Workflow ends at circularNode with label 'End'

    The executor CANNOT:
    - Execute parallel branches (except from Condition/Switch)
    - Handle nodes with multiple incoming edges from non-branching sources
    - Process cycles/loops without proper Loop/For nodes
    """,

    "agent_behavior": """
    AGENT BEHAVIOR:
    - If company_id not specified, ASK before creating workflow
    - Tags must belong to the same company as the workflow
    - Use list_tags to verify tag exists if needed
    """
}

EDGE_EXAMPLE = {
    "id": "e1-2",
    "source": "1",
    "target": "2",
    "sourceHandle": "true"  # For condition nodes: 'true' branch or 'false' branch
}

# Workflow JSON structure
WORKFLOW_STRUCTURE = {
    "nodes": "array - List of node objects",
    "edges": "array - List of edge objects connecting nodes",
    "localVars": "array - Local variables defined in workflow [{name, type, initialValue}]"
}

def get_node_type_description(node_type: str) -> dict:
    """Get description for a specific node type"""
    return NODE_TYPES.get(node_type, {"description": "Unknown node type"})

def get_all_node_types() -> list:
    """Get list of all available node types"""
    return list(NODE_TYPES.keys())

def get_node_types_for_llm() -> str:
    """Generate LLM-friendly description of all node types"""
    lines = ["Available RMMS Workflow Node Types:\n"]
    for node_type, info in NODE_TYPES.items():
        lines.append(f"- {node_type}: {info['description']}")
        if info.get('required_data'):
            lines.append(f"  Required: {', '.join(info['required_data'])}")

    # Add critical workflow rules
    lines.append("\n" + "="*50)
    lines.append("CRITICAL WORKFLOW RULES:")
    lines.append("="*50)
    lines.append(WORKFLOW_RULES["branching"])
    lines.append(WORKFLOW_RULES["tag_format"])
    lines.append(WORKFLOW_RULES["execution_flow"])

    return "\n".join(lines)
