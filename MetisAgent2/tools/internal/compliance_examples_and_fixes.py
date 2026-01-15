"""
CLAUDE.md Compliance Examples ve Fix Önerileri

Bu dosya, yaygın compliance ihlallerini ve çözümlerini örneklerle gösterir.
"""

# ==========================================
# VIOLATION EXAMPLES VE FIX ÖNERİLERİ
# ==========================================

def violation_examples():
    """
    Yaygın CLAUDE.md compliance ihlalleri ve çözümleri
    """
    
    examples = {
        "no_regex_hardcoding": {
            "description": "Regex hard-coding yasağı",
            "violation_example": '''
# ❌ YANLIŞ - Hardcoded regex patterns
def handle_user_request(request):
    if re.match(r"^create.*", request):
        return create_workflow()
    elif re.search(r"delete.*", request):
        return delete_workflow()
    elif request == "show dashboard":
        return show_dashboard()
            ''',
            "fix_example": '''
# ✅ DOĞRU - LLM-based evaluation
def handle_user_request(request, llm_tool):
    # LLM ile user intent'ini analiz et
    analysis_prompt = f"""
    Analyze this user request and determine the action:
    Request: {request}
    
    Possible actions: create, delete, show, modify, list
    Return the primary action and any objects mentioned.
    """
    
    result = llm_tool.generate_response(analysis_prompt)
    action_data = json.loads(result)
    
    # LLM analiz sonucuna göre dinamik routing
    return route_action(action_data)
            ''',
            "why_wrong": "Hardcoded regex patterns esnek değil, yeni use case'ler için kod değişikliği gerektirir",
            "why_right": "LLM evaluation esnek ve adaptif, yeni request tiplerini otomatik handle eder"
        },
        
        "no_hardcoded_methods": {
            "description": "Hardcoded method yasağı",
            "violation_example": '''
# ❌ YANLIŞ - Specific workflow methods
def handle_gmail_show_workflow(user_id):
    emails = get_emails(user_id)
    return display_emails(emails)

def handle_gmail_visual_workflow(user_id, subject):
    emails = get_emails(user_id)
    visual = create_visual(subject)
    return display_visual(visual)

def handle_calendar_create_workflow(user_id, event_data):
    calendar = get_calendar(user_id)
    calendar.create_event(event_data)
    return success_response()
            ''',
            "fix_example": '''
# ✅ DOĞRU - Generic, parameterized methods
def execute_workflow(user_id, workflow_config, llm_tool):
    """
    Generic workflow executor that adapts to any use case
    """
    # LLM ile workflow steps'lerini dinamik oluştur
    planning_prompt = f"""
    Create a workflow plan for this configuration:
    User: {user_id}
    Goal: {workflow_config.get('goal', '')}
    Available Tools: {workflow_config.get('tools', [])}
    Parameters: {workflow_config.get('params', {})}
    
    Return a JSON plan with steps and tool calls.
    """
    
    plan = llm_tool.generate_response(planning_prompt)
    workflow_steps = json.loads(plan)
    
    # Plan'ı execute et
    return execute_dynamic_plan(workflow_steps, user_id)

def route_action(action_data):
    """
    Generic action router - no specific workflows
    """
    workflow_config = {
        'goal': action_data.get('action'),
        'params': action_data.get('parameters', {}),
        'tools': determine_required_tools(action_data)
    }
    
    return execute_workflow(action_data.get('user_id'), workflow_config)
            ''',
            "why_wrong": "Her use case için ayrı method yazmak scalable değil",
            "why_right": "Generic methods parametrelerle her duruma adapt olur"
        },
        
        "sequential_thinking_only": {
            "description": "Sequential Thinking tek planner yasağı",
            "violation_example": '''
# ❌ YANLIŞ - Additional planner layers
class WorkflowPlanner:
    def plan_workflow(self, request):
        steps = self.analyze_request(request)
        return self.create_execution_plan(steps)

class TaskOrchestrator:
    def orchestrate_tasks(self, plan):
        return self.execute_plan_sequentially(plan)

# Multiple planning systems
def handle_request(request):
    planner = WorkflowPlanner()
    orchestrator = TaskOrchestrator()
    
    plan = planner.plan_workflow(request)
    result = orchestrator.orchestrate_tasks(plan)
    return result
            ''',
            "fix_example": '''
# ✅ DOĞRU - Only Sequential Thinking MCP + Tool Coordinator
def handle_request(request, user_id):
    """
    Single planning system using Sequential Thinking MCP
    """
    # Tool Coordinator ile tool registry hazırla
    tool_coordinator = ToolCoordinator()
    available_tools = tool_coordinator.get_user_tools(user_id)
    
    # Sequential Thinking MCP'ye delege et
    sequential_thinking = SequentialThinkingTool()
    
    # Single planning call
    result = sequential_thinking.plan_and_execute(
        request=request,
        user_id=user_id,
        available_tools=available_tools
    )
    
    return result
            ''',
            "why_wrong": "Multiple planner layer'ları karmaşıklık yaratır ve duplicate system oluşturur",
            "why_right": "Sequential Thinking MCP tek planner olarak yeterli, Tool Coordinator ile birlikte"
        },
        
        "no_prompt_workflows": {
            "description": "Prompt'ta özel workflow yasağı",
            "violation_example": '''
# ❌ YANLIŞ - Hardcoded prompt workflows
def generate_llm_prompt(request):
    if "göster" in request.lower():
        return """
        Follow this 2-step workflow:
        1. Get data from source
        2. Display the results
        """
    elif "görsel" in request.lower():
        return """
        Follow this 3-step workflow:
        1. Analyze request content
        2. Generate visual with DALL-E
        3. Display the visual
        """
            ''',
            "fix_example": '''
# ✅ DOĞRU - Let LLM create its own workflow
def generate_llm_prompt(request, available_tools):
    return f"""
    User Request: {request}
    
    Available Tools: {available_tools}
    
    Please analyze this request and create an appropriate workflow.
    Determine what steps are needed and which tools to use.
    Be flexible and intelligent in your planning.
    
    Return a JSON plan with your reasoning and execution steps.
    """
            ''',
            "why_wrong": "Keyword-based decision making esnek değil, LLM'in zekasını kısıtlar",
            "why_right": "LLM kendi workflow'unu oluşturur, daha esnek ve intelligent"
        },
        
        "no_working_system_changes": {
            "description": "Çalışan sisteme dokunma yasağı",
            "violation_example": '''
# ❌ YANLIŞ - Working system'i tamamen değiştirme
# Önceki working code:
def visual_creator_working_method():
    # Bu method çalışıyor ve görsel oluşturuyor
    image = generate_image_with_dalle()
    save_path = save_image(image)
    return {"success": True, "path": save_path}

# Violation: Çalışan methodu tamamen değiştirme
def visual_creator_working_method():
    # Tamamen yeni implementation
    # Bu değişiklik sistemin çalışmasını bozabilir
    pass
            ''',
            "fix_example": '''
# ✅ DOĞRU - Working system'i koruyarak extend etme
def visual_creator_working_method():
    # Original working code korunur
    image = generate_image_with_dalle()
    save_path = save_image(image)
    return {"success": True, "path": save_path}

# Yeni özellik eklemek için ayrı method
def visual_creator_enhanced_method():
    # Working method'u çağır
    base_result = visual_creator_working_method()
    
    # Sadece enhancement ekle
    if base_result["success"]:
        base_result["enhancement"] = add_new_feature()
    
    return base_result
            ''',
            "why_wrong": "Çalışan sistemleri bozmak stability sorunlarına yol açar",
            "why_right": "Working code korunur, yeni özellikler extension olarak eklenir"
        }
    }
    
    return examples


def generate_fix_suggestions(violation: str, context: str = "") -> str:
    """
    Belirli bir violation için fix önerisi oluşturur
    
    Args:
        violation: Violation rule ID'si
        context: Kod konteksti
        
    Returns:
        Fix önerisi
    """
    examples = violation_examples()
    
    if violation in examples:
        example = examples[violation]
        
        suggestion = f"""
🚨 VIOLATION: {example['description']}

❌ Problem:
{example['why_wrong']}

✅ Çözüm:
{example['why_right']}

📝 Örnek Fix:
{example['fix_example']}

💡 Bu violation için genel yaklaşım:
- LLM evaluation kullan, hardcoded patterns kullanma
- Generic, parameterized methods yaz
- Working systems'i koruyarak extend et
- Sequential Thinking MCP'ye güven
"""
        return suggestion
    
    return f"❓ {violation} için genel fix önerisi bulunamadı"


def automated_fix_attempt(file_path: str, violation_line: str, rule_id: str) -> str:
    """
    Otomatik fix önerisi oluşturur (tam otomatik değil, öneri)
    
    Args:
        file_path: Dosya yolu
        violation_line: İhlal satırı
        rule_id: Kural ID'si
        
    Returns:
        Fix önerisi
    """
    
    # Basit otomatik fix önerileri
    fixes = {
        "no_print_statements": {
            "pattern": r"print\s*\(",
            "replacement": "logger.info(",
            "additional": "# logging import ekle: import logging; logger = logging.getLogger(__name__)"
        },
        
        "no_import_star": {
            "pattern": r"from\s+(.*)\s+import\s+\*",
            "replacement": "# from \\1 import specific_functions",
            "additional": "# Specific import'ları belirle ve tek tek import et"
        }
    }
    
    if rule_id in fixes:
        fix_info = fixes[rule_id]
        
        return f"""
🔧 OTOMATIK FIX ÖNERİSİ:

Dosya: {file_path}
Satır: {violation_line}

Değişiklik:
{violation_line} 
↓
{re.sub(fix_info['pattern'], fix_info['replacement'], violation_line)}

Ek Gereksinimler:
{fix_info['additional']}
"""
    
    return "🤖 Bu violation için otomatik fix önerisi bulunmuyor, manual review gerekli"


def main():
    """
    Examples'ı test etmek için
    """
    examples = violation_examples()
    
    print("CLAUDE.md COMPLIANCE EXAMPLES VE FIX ÖNERİLERİ")
    print("=" * 60)
    
    for rule_id, example in examples.items():
        print(f"\n📋 {rule_id.upper()}")
        print(f"   Açıklama: {example['description']}")
        print(f"   Neden Yanlış: {example['why_wrong']}")
        print(f"   Neden Doğru: {example['why_right']}")
        print("-" * 60)


if __name__ == "__main__":
    main()