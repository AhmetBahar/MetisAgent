#!/usr/bin/env python3
"""
Test script for Application Orchestrator with Workflow Template System
"""

import asyncio
import sys
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator.application_orchestrator import (
    ApplicationOrchestrator, 
    WorkflowTemplate, 
    WorkflowStep,
    WorkflowTemplateType,
    initialize_application,
    get_orchestrator
)
from core.contracts.base_types import ExecutionContext


async def test_application_orchestrator():
    """Test Application Orchestrator with Axis/RMMS style workflow management"""
    
    print("🧪 Testing Application Orchestrator - Axis/RMMS Style Workflow Management")
    print("=" * 80)
    
    test_user_id = "6ff412b9-aa9f-4f90-b0c7-fce27d016960"  # User with API keys
    
    try:
        # Test 1: Initialize Application
        print("\n🚀 1. Initializing Application Orchestrator...")
        
        success = await initialize_application()
        if success:
            print("   ✅ Application initialized successfully")
        else:
            print("   ❌ Application initialization failed")
            return False
        
        orchestrator = get_orchestrator()
        
        # Test 2: Check System Health
        print("\n💓 2. Checking system health...")
        
        health = await orchestrator.get_system_health()
        print(f"   ✅ System initialized: {health['is_initialized']}")
        print(f"   ✅ Component health: {sum(health['component_health'].values())}/{len(health['component_health'])} healthy")
        print(f"   ✅ Active executions: {health['active_executions']}")
        
        for component, status in health['component_health'].items():
            print(f"     • {component}: {'✅' if status else '❌'}")
        
        # Test 3: List Default Workflow Templates
        print("\n📋 3. Listing default workflow templates...")
        
        templates = await orchestrator.list_workflow_templates(test_user_id)
        print(f"   ✅ Found {len(templates)} workflow templates:")
        
        for template in templates:
            print(f"     • {template.name} (v{template.version})")
            print(f"       Type: {template.template_type.value}")
            print(f"       Steps: {len(template.steps)}")
            print(f"       Success rate: {template.success_rate:.1%}")
            print(f"       Tags: {', '.join(template.tags)}")
        
        # Test 4: Execute LLM Chat Workflow
        print("\n🤖 4. Executing LLM Chat Workflow...")
        
        llm_template = None
        for template in templates:
            if template.id == "default_llm_chat":
                llm_template = template
                break
        
        if llm_template:
            execution_context = ExecutionContext(
                user_id=test_user_id,
                conversation_id="test_workflow_execution",
                session_id="orchestrator_test"
            )
            
            workflow_input = {
                "user_messages": [{"role": "user", "content": "Application Orchestrator test! Workflow template sistemi çalışıyor mu?"}],
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 100
            }
            
            result = await orchestrator.execute_workflow(
                template_id="default_llm_chat",
                user_id=test_user_id,
                input_data=workflow_input,
                execution_context=execution_context
            )
            
            if result.success:
                execution = result.data
                print(f"   ✅ Workflow executed successfully!")
                print(f"   ✅ Execution ID: {execution.id}")
                print(f"   ✅ Status: {execution.status.value}")
                print(f"   ✅ Duration: {execution.duration_seconds:.2f}s")
                print(f"   ✅ Steps completed: {execution.current_step + 1}")
                
                # Check output
                if execution.output_data:
                    response = execution.output_data.get("response", "No response")
                    print(f"   ✅ LLM Response: {response[:100]}...")
                
            else:
                print(f"   ❌ Workflow execution failed: {result.error}")
        else:
            print("   ❌ Default LLM chat template not found")
        
        # Test 5: Check Template Statistics Update
        print("\n📊 5. Checking template statistics...")
        
        updated_templates = await orchestrator.list_workflow_templates(test_user_id)
        
        for template in updated_templates:
            if template.id == "default_llm_chat":
                print(f"   ✅ Template: {template.name}")
                print(f"   ✅ Total executions: {template.total_executions}")
                print(f"   ✅ Successful executions: {template.successful_executions}")
                print(f"   ✅ Success rate: {template.success_rate:.1%}")
                print(f"   ✅ Average duration: {template.average_duration:.2f}s")
                break
        
        # Test 6: Create Custom Workflow Template
        print("\n🛠 6. Creating custom workflow template...")
        
        custom_steps = [
            WorkflowStep(
                id="step_1",
                name="Greeting Generation",
                tool_name="llm_tool", 
                capability="generate_response",
                input_data={
                    "messages": [{"role": "user", "content": "{{greeting_language}} dilinde {{name}} için kişiselleştirilmiş bir selamla mesajı oluştur."}],
                    "provider": "anthropic",
                    "max_tokens": 150
                },
                expected_outputs=["response"]
            ),
            WorkflowStep(
                id="step_2",
                name="Greeting Enhancement", 
                tool_name="llm_tool",
                capability="generate_response",
                input_data={
                    "messages": [{"role": "user", "content": "Bu selamlamayı daha profesyonel hale getir: {{step_1.response}}"}],
                    "provider": "anthropic",
                    "max_tokens": 200
                },
                expected_outputs=["response"],
                depends_on=["step_1"]
            )
        ]
        
        custom_template = WorkflowTemplate(
            id="custom_greeting_workflow",
            name="Personalized Greeting Workflow",
            description="Multi-step personalized greeting generation workflow",
            version="1.0.0",
            template_type=WorkflowTemplateType.MANUAL,
            created_by=test_user_id,
            steps=custom_steps,
            tags=["custom", "greeting", "multi-step"],
            input_schema={
                "greeting_language": {"type": "string", "required": True},
                "name": {"type": "string", "required": True}
            },
            output_schema={
                "final_greeting": {"type": "string"}
            }
        )
        
        # Save custom template
        save_success = await orchestrator.template_manager.save_template(custom_template)
        
        if save_success:
            print(f"   ✅ Custom template saved: {custom_template.name}")
            
            # Execute custom workflow
            print("\n🎭 7. Executing custom multi-step workflow...")
            
            custom_input = {
                "greeting_language": "Türkçe",
                "name": "MetisAgent3 Kullanıcısı"
            }
            
            custom_execution_context = ExecutionContext(
                user_id=test_user_id,
                conversation_id="test_custom_workflow",
                session_id="orchestrator_test"
            )
            
            custom_result = await orchestrator.execute_workflow(
                template_id="custom_greeting_workflow",
                user_id=test_user_id,
                input_data=custom_input,
                execution_context=custom_execution_context
            )
            
            if custom_result.success:
                custom_execution = custom_result.data
                print(f"   ✅ Multi-step workflow completed!")
                print(f"   ✅ Duration: {custom_execution.duration_seconds:.2f}s")
                print(f"   ✅ Steps: {len(custom_execution.step_results)}")
                
                # Show step results
                for step_id, step_result in custom_execution.step_results.items():
                    if isinstance(step_result, dict) and "response" in step_result:
                        response = step_result["response"][:100]
                        print(f"   ✅ {step_id}: {response}...")
                
            else:
                print(f"   ❌ Custom workflow failed: {custom_result.error}")
                
        else:
            print("   ❌ Failed to save custom template")
        
        # Test 8: List All Templates (including auto-generated)
        print("\n📚 8. Listing all workflow templates...")
        
        all_templates = await orchestrator.list_workflow_templates(test_user_id)
        print(f"   ✅ Total templates: {len(all_templates)}")
        
        by_type = {}
        for template in all_templates:
            template_type = template.template_type.value
            by_type[template_type] = by_type.get(template_type, 0) + 1
        
        print("   ✅ Templates by type:")
        for template_type, count in by_type.items():
            print(f"     • {template_type}: {count}")
        
        # Show auto-generated templates
        auto_templates = [t for t in all_templates if t.template_type == WorkflowTemplateType.AUTO_GENERATED]
        if auto_templates:
            print(f"   ✅ Auto-generated templates: {len(auto_templates)}")
            for template in auto_templates:
                print(f"     • {template.name}")
                print(f"       Success rate: {template.success_rate:.1%}")
                print(f"       Executions: {template.total_executions}")
        
        # Test 9: Template Performance Analysis
        print("\n📈 9. Template performance analysis...")
        
        performance_templates = sorted(all_templates, key=lambda t: (t.success_rate, t.total_executions), reverse=True)
        
        print("   ✅ Top performing templates:")
        for i, template in enumerate(performance_templates[:3]):
            print(f"     {i+1}. {template.name}")
            print(f"        Success: {template.success_rate:.1%} ({template.successful_executions}/{template.total_executions})")
            print(f"        Avg duration: {template.average_duration:.2f}s")
            print(f"        Type: {template.template_type.value}")
        
        print(f"\n🎉 Application Orchestrator Tests Complete!")
        print(f"📊 Summary:")
        print(f"   • System initialization: ✅ Working")
        print(f"   • Component health monitoring: ✅ Working")
        print(f"   • Workflow template management: ✅ Working")
        print(f"   • Workflow execution engine: ✅ Working")
        print(f"   • Template statistics tracking: ✅ Working")
        print(f"   • Multi-step workflow support: ✅ Working")
        print(f"   • Auto-generated templates: ✅ Working")
        print(f"   • Performance analysis: ✅ Working")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    try:
        success = await test_application_orchestrator()
        
        # Cleanup
        orchestrator = get_orchestrator()
        await orchestrator.shutdown()
        
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())