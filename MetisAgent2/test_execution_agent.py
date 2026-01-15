"""
MetisAgent2 Test Execution & Analysis Subagent
Autonomous execution of automated tests with comprehensive result interpretation
"""

import json
import logging
import subprocess
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class TestExecutionAgent:
    """
    Specialized subagent for executing automated tests and analyzing results
    Focuses on functional validation with skeptical approach to "success" results
    """
    
    def __init__(self):
        self.execution_results = []
        self.functional_validations = []
        self.compliance_violations = []
        self.root_cause_analysis = []
        self.actionable_recommendations = []
        
        # Paths
        self.project_root = Path("/home/ahmet/MetisAgent/MetisAgent2")
        self.test_agent_path = self.project_root / "automated_test_agent.py"
        self.test_reports_dir = self.project_root / "test_reports"
        
        # Known failure patterns and their root causes
        self.failure_patterns = {
            "tool_not_found": {
                "indicators": ["not found", "missing", "null reference"],
                "root_cause": "Tool registration failure or import issues",
                "actions": ["Check MCP core tool loading", "Verify tool imports", "Review registry initialization"]
            },
            "oauth2_authentication": {
                "indicators": ["oauth", "token", "credentials", "authentication"],
                "root_cause": "OAuth2 token expired or user mapping failure",
                "actions": ["Check OAuth2 token validity", "Verify user mapping", "Test credential storage"]
            },
            "workflow_orchestration": {
                "indicators": ["orchestrator", "step_results", "workflow", "coordination"],
                "root_cause": "Workflow orchestration system malfunction",
                "actions": ["Check WorkflowOrchestrator initialization", "Verify step result tracking", "Test tool coordination"]
            },
            "memory_system": {
                "indicators": ["memory", "graph", "mcp", "storage"],
                "root_cause": "Graph memory or MCP communication failure",
                "actions": ["Test MCP Memory server connection", "Check stdio protocol", "Verify graph storage"]
            },
            "command_security": {
                "indicators": ["command_executor", "security", "injection", "unsafe"],
                "root_cause": "Command execution security compromise",
                "actions": ["Review command sanitization", "Test injection prevention", "Audit security filters"]
            }
        }
    
    def execute_automated_tests(self) -> Dict[str, Any]:
        """
        Execute the automated test agent and capture comprehensive results
        """
        logger.info("🚀 Starting Test Execution Agent")
        
        start_time = datetime.now()
        
        try:
            # Ensure conda environment is activated
            conda_cmd = "conda activate MetisAgent && "
            
            # Execute automated test agent
            cmd = f"{conda_cmd}cd {self.project_root} && python automated_test_agent.py"
            
            logger.info(f"Executing: {cmd}")
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            execution_result = {
                "command": cmd,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": str(datetime.now() - start_time),
                "success": result.returncode == 0
            }
            
            self.execution_results.append(execution_result)
            
            # Parse JSON report if available
            test_report = self._find_and_parse_latest_report()
            
            # Perform comprehensive analysis
            analysis_report = self._analyze_test_results(execution_result, test_report)
            
            return analysis_report
            
        except subprocess.TimeoutExpired:
            error_result = {
                "error": "Test execution timeout (5 minutes)",
                "execution_time": str(datetime.now() - start_time),
                "success": False
            }
            self.execution_results.append(error_result)
            return self._create_error_analysis("TIMEOUT", error_result)
            
        except Exception as e:
            error_result = {
                "error": f"Test execution failed: {str(e)}",
                "execution_time": str(datetime.now() - start_time),
                "success": False
            }
            self.execution_results.append(error_result)
            return self._create_error_analysis("EXCEPTION", error_result)
    
    def _find_and_parse_latest_report(self) -> Optional[Dict[str, Any]]:
        """
        Find and parse the latest JSON test report
        """
        try:
            if not self.test_reports_dir.exists():
                logger.warning("Test reports directory not found")
                return None
            
            # Find latest report
            report_files = list(self.test_reports_dir.glob("automated_test_report_*.json"))
            if not report_files:
                logger.warning("No test report files found")
                return None
            
            latest_report = max(report_files, key=os.path.getctime)
            
            with open(latest_report, 'r') as f:
                report_data = json.load(f)
            
            logger.info(f"📄 Parsed test report: {latest_report}")
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to parse test report: {e}")
            return None
    
    def _analyze_test_results(self, execution_result: Dict, test_report: Optional[Dict]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of test results with functional validation
        """
        analysis = {
            "analysis_timestamp": datetime.now().isoformat(),
            "execution_analysis": self._analyze_execution_result(execution_result),
            "test_report_analysis": self._analyze_test_report(test_report) if test_report else None,
            "functional_validation": self._perform_functional_validation(test_report),
            "failure_analysis": self._perform_failure_analysis(execution_result, test_report),
            "compliance_check": self._check_claude_md_compliance(test_report),
            "root_cause_analysis": self._perform_root_cause_analysis(),
            "actionable_recommendations": self._generate_actionable_recommendations(),
            "overall_assessment": self._generate_overall_assessment()
        }
        
        # Save analysis report
        self._save_analysis_report(analysis)
        
        return analysis
    
    def _analyze_execution_result(self, execution_result: Dict) -> Dict[str, Any]:
        """
        Analyze the execution result itself (not just test outcomes)
        """
        analysis = {
            "execution_successful": execution_result["success"],
            "return_code": execution_result["return_code"],
            "has_stdout": bool(execution_result.get("stdout", "").strip()),
            "has_stderr": bool(execution_result.get("stderr", "").strip()),
            "execution_time": execution_result["execution_time"]
        }
        
        # Analyze stderr for critical issues
        stderr = execution_result.get("stderr", "")
        if stderr:
            analysis["stderr_issues"] = self._analyze_stderr(stderr)
        
        # Analyze stdout for test execution indicators
        stdout = execution_result.get("stdout", "")
        if stdout:
            analysis["stdout_analysis"] = self._analyze_stdout(stdout)
        
        return analysis
    
    def _analyze_stderr(self, stderr: str) -> List[Dict[str, Any]]:
        """
        Analyze stderr output for specific error patterns
        """
        issues = []
        
        error_patterns = {
            "import_error": ["ImportError", "ModuleNotFoundError", "No module named"],
            "permission_error": ["PermissionError", "Access denied", "Permission denied"],
            "file_not_found": ["FileNotFoundError", "No such file", "does not exist"],
            "json_decode_error": ["JSONDecodeError", "JSON decode error", "Expecting value"],
            "connection_error": ["ConnectionError", "Connection refused", "timeout"]
        }
        
        for error_type, patterns in error_patterns.items():
            for pattern in patterns:
                if pattern in stderr:
                    issues.append({
                        "type": error_type,
                        "pattern": pattern,
                        "severity": "HIGH" if error_type in ["import_error", "permission_error"] else "MEDIUM"
                    })
        
        return issues
    
    def _analyze_stdout(self, stdout: str) -> Dict[str, Any]:
        """
        Analyze stdout for test execution indicators
        """
        analysis = {
            "test_summary_found": "AUTOMATED TEST SUMMARY" in stdout,
            "overall_result": None,
            "test_counts": {},
            "violations_detected": False
        }
        
        # Extract test results if summary found
        if analysis["test_summary_found"]:
            lines = stdout.split('\n')
            for line in lines:
                if "Overall Success:" in line:
                    analysis["overall_result"] = "PASS" if "✅ PASS" in line else "FAIL"
                elif "Tests Run:" in line:
                    try:
                        analysis["test_counts"]["total"] = int(line.split(":")[1].strip())
                    except:
                        pass
                elif "Passed:" in line:
                    try:
                        analysis["test_counts"]["passed"] = int(line.split(":")[1].strip())
                    except:
                        pass
                elif "Failed:" in line:
                    try:
                        analysis["test_counts"]["failed"] = int(line.split(":")[1].strip())
                    except:
                        pass
                elif "CLAUDE.md VIOLATIONS:" in line:
                    analysis["violations_detected"] = True
        
        return analysis
    
    def _analyze_test_report(self, test_report: Dict) -> Dict[str, Any]:
        """
        Deep analysis of the JSON test report
        """
        analysis = {
            "report_valid": True,
            "overall_success": test_report.get("overall_success", False),
            "test_statistics": {
                "total_tests": test_report.get("total_tests", 0),
                "passed": test_report.get("passed", 0),
                "failed": test_report.get("failed", 0),
                "categories_tested": test_report.get("categories_tested", 0)
            },
            "failed_categories": [],
            "critical_failures": [],
            "claude_md_violations": test_report.get("claude_md_violations", [])
        }
        
        # Analyze detailed results
        detailed_results = test_report.get("detailed_results", [])
        for result in detailed_results:
            if not result.get("success", True):
                failure_info = {
                    "category": result.get("category"),
                    "error": result.get("error"),
                    "details": result.get("details", {})
                }
                analysis["failed_categories"].append(failure_info)
                
                # Check for critical failures
                if self._is_critical_failure(failure_info):
                    analysis["critical_failures"].append(failure_info)
        
        return analysis
    
    def _perform_functional_validation(self, test_report: Optional[Dict]) -> Dict[str, Any]:
        """
        Skeptical functional validation - verify that "success" actually means working
        """
        validation = {
            "skeptical_analysis_performed": True,
            "suspicious_successes": [],
            "functional_verification": {},
            "recommendations": []
        }
        
        if not test_report:
            validation["error"] = "No test report available for functional validation"
            return validation
        
        # Check each "successful" test category for potential false positives
        detailed_results = test_report.get("detailed_results", [])
        for result in detailed_results:
            if result.get("success", False):
                category = result.get("category")
                details = result.get("details", {})
                
                # Skeptical checks per category
                skeptical_check = self._skeptical_category_check(category, details)
                if skeptical_check["suspicious"]:
                    validation["suspicious_successes"].append({
                        "category": category,
                        "reason": skeptical_check["reason"],
                        "evidence": skeptical_check["evidence"]
                    })
        
        # Generate functional verification recommendations
        if validation["suspicious_successes"]:
            validation["recommendations"].append(
                "🔍 FUNCTIONAL VERIFICATION REQUIRED: Some 'successful' tests may not indicate actual functionality"
            )
            validation["recommendations"].append(
                "🧪 RUNTIME TESTING: Execute actual workflows to verify functionality"
            )
        
        return validation
    
    def _skeptical_category_check(self, category: str, details: Dict) -> Dict[str, Any]:
        """
        Skeptical analysis of individual test category success
        """
        skeptical_checks = {
            "gmail_workflows": {
                "must_have": ["gmail_tool_exists", "available_actions"],
                "suspicious_if": ["missing_actions", "sequential_thinking_available"],
                "functional_test": "Should test actual Gmail API call, not just tool existence"
            },
            "visual_generation": {
                "must_have": ["available_actions"],
                "suspicious_if": ["missing_actions", "auto_display_implemented"],
                "functional_test": "Should test actual image generation, not just tool existence"
            },
            "oauth2_authentication": {
                "must_have": ["oauth_tool_exists", "token_refresh_capability"],
                "suspicious_if": [],
                "functional_test": "Should test actual token refresh, not just capability check"
            },
            "workflow_orchestration": {
                "must_have": ["orchestrator_instantiated", "step_results_attribute"],
                "suspicious_if": [],
                "functional_test": "Should test actual workflow execution, not just instantiation"
            }
        }
        
        check_config = skeptical_checks.get(category, {})
        
        # Check for missing must-have details
        must_have = check_config.get("must_have", [])
        missing_must_have = [key for key in must_have if not details.get(key, False)]
        
        # Check for suspicious indicators
        suspicious_if = check_config.get("suspicious_if", [])
        suspicious_indicators = [key for key in suspicious_if if details.get(key)]
        
        is_suspicious = bool(missing_must_have or suspicious_indicators)
        
        return {
            "suspicious": is_suspicious,
            "reason": check_config.get("functional_test", "Needs runtime verification"),
            "evidence": {
                "missing_must_have": missing_must_have,
                "suspicious_indicators": suspicious_indicators
            }
        }
    
    def _perform_failure_analysis(self, execution_result: Dict, test_report: Optional[Dict]) -> Dict[str, Any]:
        """
        Detailed failure analysis with pattern matching
        """
        failures = []
        
        # Analyze execution failures
        if not execution_result["success"]:
            failures.append({
                "type": "EXECUTION_FAILURE",
                "details": execution_result,
                "pattern_match": self._match_failure_patterns(str(execution_result))
            })
        
        # Analyze test report failures
        if test_report:
            detailed_results = test_report.get("detailed_results", [])
            for result in detailed_results:
                if not result.get("success", True):
                    failures.append({
                        "type": "TEST_CATEGORY_FAILURE",
                        "category": result.get("category"),
                        "details": result,
                        "pattern_match": self._match_failure_patterns(str(result))
                    })
        
        return {
            "total_failures": len(failures),
            "failure_details": failures,
            "pattern_analysis": self._analyze_failure_patterns(failures)
        }
    
    def _match_failure_patterns(self, failure_text: str) -> List[Dict[str, Any]]:
        """
        Match failure text against known patterns
        """
        matches = []
        failure_text_lower = failure_text.lower()
        
        for pattern_name, pattern_config in self.failure_patterns.items():
            indicators = pattern_config["indicators"]
            if any(indicator in failure_text_lower for indicator in indicators):
                matches.append({
                    "pattern": pattern_name,
                    "root_cause": pattern_config["root_cause"],
                    "recommended_actions": pattern_config["actions"]
                })
        
        return matches
    
    def _analyze_failure_patterns(self, failures: List[Dict]) -> Dict[str, Any]:
        """
        Analyze patterns across all failures
        """
        pattern_counts = {}
        all_recommended_actions = set()
        
        for failure in failures:
            pattern_matches = failure.get("pattern_match", [])
            for match in pattern_matches:
                pattern = match["pattern"]
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                all_recommended_actions.update(match["recommended_actions"])
        
        return {
            "most_common_patterns": sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True),
            "aggregated_actions": list(all_recommended_actions),
            "systemic_issues": [pattern for pattern, count in pattern_counts.items() if count > 1]
        }
    
    def _check_claude_md_compliance(self, test_report: Optional[Dict]) -> Dict[str, Any]:
        """
        Check CLAUDE.md compliance violations
        """
        compliance = {
            "violations_found": False,
            "violation_details": [],
            "severity_assessment": "NONE"
        }
        
        if test_report:
            violations = test_report.get("claude_md_violations", [])
            if violations:
                compliance["violations_found"] = True
                compliance["violation_details"] = violations
                
                # Assess severity
                severities = [v.get("severity", "LOW") for v in violations]
                if "CRITICAL" in severities:
                    compliance["severity_assessment"] = "CRITICAL"
                elif "HIGH" in severities:
                    compliance["severity_assessment"] = "HIGH"
                elif "MEDIUM" in severities:
                    compliance["severity_assessment"] = "MEDIUM"
                else:
                    compliance["severity_assessment"] = "LOW"
        
        return compliance
    
    def _perform_root_cause_analysis(self) -> Dict[str, Any]:
        """
        Perform root cause analysis across all collected data
        """
        # This would be more sophisticated in a real implementation
        # For now, aggregate the pattern-based analysis
        root_causes = {
            "primary_issues": [],
            "systemic_problems": [],
            "environment_issues": [],
            "configuration_problems": []
        }
        
        # This would analyze the collected data to identify root causes
        # For now, return placeholder structure
        return root_causes
    
    def _generate_actionable_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate prioritized, actionable recommendations
        """
        recommendations = []
        
        # High priority recommendations based on failure patterns
        if any(result.get("return_code", 0) != 0 for result in self.execution_results):
            recommendations.append({
                "priority": "CRITICAL",
                "action": "Fix test execution environment",
                "description": "Automated test agent failed to execute properly",
                "steps": [
                    "Verify conda environment activation",
                    "Check Python path and imports",
                    "Review execution permissions"
                ]
            })
        
        # Functional verification recommendations
        recommendations.append({
            "priority": "HIGH",
            "action": "Implement runtime functional testing",
            "description": "Current tests may not verify actual functionality",
            "steps": [
                "Create end-to-end workflow tests",
                "Test actual Gmail API calls with real data",
                "Verify visual generation produces actual images",
                "Test OAuth2 token refresh with expired tokens"
            ]
        })
        
        # CLAUDE.md compliance
        recommendations.append({
            "priority": "MEDIUM",
            "action": "Enhance CLAUDE.md compliance monitoring",
            "description": "Strengthen automated compliance checking",
            "steps": [
                "Implement git history analysis",
                "Add file modification timestamp checking",
                "Create security audit automation"
            ]
        })
        
        return recommendations
    
    def _generate_overall_assessment(self) -> Dict[str, Any]:
        """
        Generate overall system health assessment
        """
        # Calculate health score based on various factors
        health_score = 100
        assessment_factors = []
        
        # Execution success factor
        execution_success = any(result.get("success", False) for result in self.execution_results)
        if not execution_success:
            health_score -= 50
            assessment_factors.append("Test execution completely failed")
        
        # Functional validation concerns
        if self.functional_validations:
            suspicious_count = len([v for v in self.functional_validations if v.get("suspicious_successes")])
            health_score -= min(suspicious_count * 10, 30)
            if suspicious_count > 0:
                assessment_factors.append(f"{suspicious_count} suspicious success results")
        
        # Compliance violations
        if self.compliance_violations:
            critical_violations = [v for v in self.compliance_violations if v.get("severity") == "CRITICAL"]
            health_score -= len(critical_violations) * 20
            if critical_violations:
                assessment_factors.append(f"{len(critical_violations)} critical compliance violations")
        
        # Health level
        if health_score >= 90:
            health_level = "EXCELLENT"
        elif health_score >= 70:
            health_level = "GOOD"
        elif health_score >= 50:
            health_level = "FAIR"
        elif health_score >= 30:
            health_level = "POOR"
        else:
            health_level = "CRITICAL"
        
        return {
            "health_score": max(health_score, 0),
            "health_level": health_level,
            "assessment_factors": assessment_factors,
            "recommendation": self._get_health_recommendation(health_level)
        }
    
    def _get_health_recommendation(self, health_level: str) -> str:
        """
        Get recommendation based on health level
        """
        recommendations = {
            "EXCELLENT": "System is healthy. Continue with regular monitoring.",
            "GOOD": "System is mostly healthy. Address minor issues proactively.",
            "FAIR": "System has moderate issues. Plan remediation activities.",
            "POOR": "System has significant problems. Immediate attention required.",
            "CRITICAL": "System is in critical state. Stop deployment and fix immediately."
        }
        return recommendations.get(health_level, "Unable to assess health level")
    
    def _is_critical_failure(self, failure_info: Dict) -> bool:
        """
        Determine if a failure is critical to system operation
        """
        critical_categories = [
            "core_tool_registry",
            "workflow_orchestration", 
            "sequential_thinking"
        ]
        
        category = failure_info.get("category", "")
        return category in critical_categories
    
    def _create_error_analysis(self, error_type: str, error_result: Dict) -> Dict[str, Any]:
        """
        Create analysis report for execution errors
        """
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_details": error_result,
            "execution_analysis": {
                "execution_successful": False,
                "error_type": error_type
            },
            "actionable_recommendations": [
                {
                    "priority": "CRITICAL",
                    "action": f"Fix {error_type} in test execution",
                    "description": f"Test execution failed with {error_type}",
                    "steps": [
                        "Check system environment and dependencies",
                        "Verify test agent script integrity",
                        "Review execution permissions and paths"
                    ]
                }
            ],
            "overall_assessment": {
                "health_score": 0,
                "health_level": "CRITICAL",
                "assessment_factors": [f"Test execution {error_type}"],
                "recommendation": "Cannot assess system health due to test execution failure"
            }
        }
    
    def _save_analysis_report(self, analysis: Dict[str, Any]):
        """
        Save comprehensive analysis report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_path = self.test_reports_dir / f"test_execution_analysis_{timestamp}.json"
        
        # Ensure directory exists
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Analysis report saved: {analysis_path}")
    
    def print_concise_summary(self, analysis: Dict[str, Any]):
        """
        Print concise summary for user consumption
        """
        print("\n" + "="*80)
        print("🔍 TEST EXECUTION AGENT ANALYSIS SUMMARY")
        print("="*80)
        
        overall = analysis.get("overall_assessment", {})
        print(f"System Health: {overall.get('health_level', 'UNKNOWN')} ({overall.get('health_score', 0)}/100)")
        
        exec_analysis = analysis.get("execution_analysis", {})
        print(f"Test Execution: {'✅ SUCCESS' if exec_analysis.get('execution_successful', False) else '❌ FAILED'}")
        
        report_analysis = analysis.get("test_report_analysis", {})
        if report_analysis:
            stats = report_analysis.get("test_statistics", {})
            print(f"Test Results: {stats.get('passed', 0)}/{stats.get('total_tests', 0)} passed")
        
        # Functional validation concerns
        functional = analysis.get("functional_validation", {})
        suspicious = functional.get("suspicious_successes", [])
        if suspicious:
            print(f"⚠️  Suspicious Success Results: {len(suspicious)}")
        
        # Critical failures
        failure_analysis = analysis.get("failure_analysis", {})
        failures = failure_analysis.get("failure_details", [])
        critical_failures = [f for f in failures if self._is_critical_failure(f)]
        if critical_failures:
            print(f"🚨 Critical Failures: {len(critical_failures)}")
        
        # Recommendations
        recommendations = analysis.get("actionable_recommendations", [])
        high_priority = [r for r in recommendations if r.get("priority") in ["CRITICAL", "HIGH"]]
        print(f"📋 High Priority Actions: {len(high_priority)}")
        
        if high_priority:
            print("\nTop Recommendations:")
            for i, rec in enumerate(high_priority[:3], 1):
                print(f"  {i}. {rec.get('action', 'Unknown action')}")
        
        print("="*80)

def main():
    """
    Execute test execution agent as standalone tool
    """
    logging.basicConfig(level=logging.INFO)
    
    agent = TestExecutionAgent()
    analysis = agent.execute_automated_tests()
    agent.print_concise_summary(analysis)
    
    # Exit with error code based on health assessment
    health_level = analysis.get("overall_assessment", {}).get("health_level", "CRITICAL")
    exit_code = 0 if health_level in ["EXCELLENT", "GOOD"] else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()