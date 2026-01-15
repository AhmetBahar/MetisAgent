#!/usr/bin/env python3
"""
Demo script showing how to use the TestExecutionAgent
"""

import logging
from test_execution_agent import TestExecutionAgent

def main():
    """
    Demonstrate TestExecutionAgent capabilities
    """
    print("🎯 MetisAgent2 Test Execution Agent Demo")
    print("="*50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create and run the test execution agent
    agent = TestExecutionAgent()
    
    print("🚀 Executing automated tests and analyzing results...")
    analysis = agent.execute_automated_tests()
    
    print("\n📊 Analysis Complete!")
    agent.print_concise_summary(analysis)
    
    print("\n🔍 Detailed Analysis Available:")
    print(f"- Full analysis saved to test_reports/")
    print(f"- Health Score: {analysis.get('overall_assessment', {}).get('health_score', 'N/A')}/100")
    
    # Show key insights
    failure_analysis = analysis.get('failure_analysis', {})
    if failure_analysis.get('total_failures', 0) > 0:
        print(f"\n⚠️  Key Issues Detected:")
        patterns = failure_analysis.get('pattern_analysis', {}).get('most_common_patterns', [])
        for pattern, count in patterns[:3]:  # Top 3 patterns
            print(f"  - {pattern.replace('_', ' ').title()}: {count} occurrences")
    
    # Show actionable recommendations
    recommendations = analysis.get('actionable_recommendations', [])
    high_priority = [r for r in recommendations if r.get('priority') == 'CRITICAL']
    if high_priority:
        print(f"\n🚨 Critical Actions Needed:")
        for rec in high_priority:
            print(f"  - {rec.get('action', 'Unknown')}")

if __name__ == "__main__":
    main()