"""
CLAUDE.md Compliance Checker Tool

Bu tool, kod değişikliklerinin CLAUDE.md dosyasındaki kritik kurallara uygunluğunu kontrol eder.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComplianceViolation:
    """Uyumluluk ihlali bilgisi"""
    rule_id: str
    rule_name: str
    file_path: str
    line_number: int
    violation_text: str
    severity: str  # "critical", "high", "medium", "low"
    recommendation: str


class ClaudeComplianceChecker:
    """
    CLAUDE.md kurallarına göre kod uyumluluğunu kontrol eden tool
    """
    
    def __init__(self, project_root: str = None):
        """
        Tool'u başlat
        
        Args:
            project_root: Proje kök dizini
        """
        self.project_root = project_root or "/home/ahmet/MetisAgent/MetisAgent2"
        self.claude_md_path = os.path.join(self.project_root, "CLAUDE.md")
        
        # CLAUDE.md'den çıkarılan kritik kurallar
        self.compliance_rules = self._initialize_compliance_rules()
        
    def _initialize_compliance_rules(self) -> Dict[str, Dict]:
        """
        CLAUDE.md'den kritik kuralları çıkarıp yapılandırır
        """
        return {
            "no_regex_hardcoding": {
                "name": "Regex Hard-coding Yasağı",
                "description": "Hiç bir durumda regex case ekleme, llm ile evaluation kullan",
                "severity": "critical",
                "patterns": [
                    r"if\s+.*\.match\s*\(",
                    r"if\s+.*\.search\s*\(",
                    r"re\.compile\s*\(",
                    r"re\.match\s*\(",
                    r"re\.search\s*\(",
                    r"if\s+.*==.*['\"].*['\"].*:",  # String comparison patterns
                    r"elif\s+.*==.*['\"].*['\"].*:",
                ],
                "exceptions": [
                    "test_",  # Test files can use regex
                    "compliance_checker",  # This tool itself
                ],
                "recommendation": "LLM evaluation kullan, hardcoded regex patterns yerine esnek prompt-based çözümler tercih et"
            },
            
            "no_hardcoded_methods": {
                "name": "Hardcoded Method Yasağı", 
                "description": "Hiç bir durumda hardcoded metod ekleme, çok kullanıcılı ve çok durumlu promptlara göre esnek metodlar ile çöz",
                "severity": "critical",
                "patterns": [
                    r"def\s+handle_.*_workflow\s*\(",
                    r"def\s+process_.*_request\s*\(",
                    r"if\s+.*workflow.*==.*['\"].*['\"]",
                    r"elif\s+.*workflow.*==.*['\"].*['\"]",
                    r"def\s+.*_specific_.*\s*\(",
                ],
                "exceptions": [
                    "test_",
                    "compliance_checker",
                    "__init__",
                    "__str__",
                    "__repr__"
                ],
                "recommendation": "Esnek, parametrik metodlar oluştur. User prompt'larına göre dinamik çözümler kullan"
            },
            
            "sequential_thinking_only": {
                "name": "Sequential Thinking Tek Planner",
                "description": "Sequential Thinking MCP tool temel ve tek workflow planner'dır",
                "severity": "critical", 
                "patterns": [
                    r"class.*Planner\s*\(",
                    r"class.*Orchestrator\s*\(",
                    r"class.*WorkflowManager\s*\(",
                    r"def\s+plan_workflow\s*\(",
                    r"def\s+orchestrate\s*\(",
                ],
                "exceptions": [
                    "SequentialThinking",
                    "tool_coordinator",  # Allowed coordinator
                ],
                "recommendation": "Başka planner layer ekleme. Sequential Thinking MCP + Tool Coordinator yeterli"
            },
            
            "no_working_system_changes": {
                "name": "Çalışan Sisteme Dokunma Yasağı",
                "description": "Atomize edilmiş program bölümleri çalıştıktan sonra DEĞİŞTİRİLMEZ",
                "severity": "critical",
                "patterns": [
                    # Bu rule daha çok değişiklik analizi gerektirir, static pattern kontrolden zor
                ],
                "recommendation": "Çalışan kod parçalarını değiştirme. Sadece bug fix yap veya yeni özellik ekle"
            },
            
            "no_prompt_workflows": {
                "name": "Prompt'ta Özel Workflow Yasağı",
                "description": "Hiç bir şekilde prompta özel workflow yazma",
                "severity": "high",
                "patterns": [
                    r"workflow.*=.*\[.*\]",
                    r"steps.*=.*\[.*step.*\]", 
                    r"if.*['\"]göster['\"].*:",
                    r"if.*['\"]show['\"].*:",
                    r"if.*['\"]display['\"].*:",
                ],
                "recommendation": "LLM'in kendi workflow'unu oluşturmasına izin ver. Keyword-based decision making kullanma"
            },
            
            "no_print_statements": {
                "name": "Print Kullanımı Yasağı",
                "description": "print() kullanılmaz; bunun yerine logging tercih edilir",
                "severity": "medium",
                "patterns": [
                    r"print\s*\(",
                ],
                "exceptions": [
                    "test_",
                    "__main__",
                ],
                "recommendation": "logging.info(), logging.error() veya logger kullan"
            },
            
            "no_import_star": {
                "name": "Import * Yasağı", 
                "description": "import * kullanma",
                "severity": "medium",
                "patterns": [
                    r"from\s+.*\s+import\s+\*",
                ],
                "recommendation": "Specific imports kullan: from module import specific_function"
            },
            
            "no_subprocess_direct": {
                "name": "Doğrudan Subprocess Yasağı",
                "description": "Sistemde subprocess ile doğrudan kullanıcıdan gelen girdiyi çalıştırma",
                "severity": "high", 
                "patterns": [
                    r"subprocess\.call\s*\(.*user.*\)",
                    r"subprocess\.run\s*\(.*user.*\)",
                    r"subprocess\.Popen\s*\(.*user.*\)",
                    r"os\.system\s*\(.*user.*\)",
                ],
                "recommendation": "command_executor.py kullan veya input validation yap"
            }
        }
    
    def check_file_compliance(self, file_path: str) -> List[ComplianceViolation]:
        """
        Tek bir dosyanın uyumluluğunu kontrol eder
        
        Args:
            file_path: Kontrol edilecek dosya yolu
            
        Returns:
            İhlal listesi
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            # Her kural için kontrolü yap
            for rule_id, rule_config in self.compliance_rules.items():
                violations.extend(
                    self._check_rule_violations(file_path, lines, rule_id, rule_config)
                )
                
        except Exception as e:
            logger.error(f"Dosya okuma hatası {file_path}: {e}")
            
        return violations
    
    def _check_rule_violations(self, file_path: str, lines: List[str], 
                             rule_id: str, rule_config: Dict) -> List[ComplianceViolation]:
        """
        Belirli bir kuralın ihlallerini kontrol eder
        """
        violations = []
        
        # Exception kontrolü
        file_name = os.path.basename(file_path)
        exceptions = rule_config.get("exceptions", [])
        
        for exception in exceptions:
            if exception in file_name:
                return violations  # Bu dosya istisna
        
        # Pattern kontrolü
        patterns = rule_config.get("patterns", [])
        
        for line_num, line in enumerate(lines, 1):
            line_clean = line.strip()
            
            for pattern in patterns:
                if re.search(pattern, line_clean, re.IGNORECASE):
                    violation = ComplianceViolation(
                        rule_id=rule_id,
                        rule_name=rule_config["name"],
                        file_path=file_path,
                        line_number=line_num,
                        violation_text=line_clean,
                        severity=rule_config["severity"],
                        recommendation=rule_config["recommendation"]
                    )
                    violations.append(violation)
                    
        return violations
    
    def check_project_compliance(self, exclude_dirs: List[str] = None) -> Dict[str, Any]:
        """
        Tüm proje uyumluluğunu kontrol eder
        
        Args:
            exclude_dirs: Hariç tutulacak dizinler
            
        Returns:
            Compliance raporu
        """
        if exclude_dirs is None:
            exclude_dirs = [
                "node_modules", "__pycache__", ".git", ".venv", 
                "venv", "generated_images", "storage", "conversation_storage",
                "metis_data", "graph_memory_storage", "dynamic_tools/servers"
            ]
        
        all_violations = []
        checked_files = []
        
        # Python dosyalarını tara
        for root, dirs, files in os.walk(self.project_root):
            # Hariç tutulacak dizinleri atla
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    checked_files.append(file_path)
                    
                    violations = self.check_file_compliance(file_path)
                    all_violations.extend(violations)
        
        # Sonuçları kategorize et
        compliance_report = self._generate_compliance_report(all_violations, checked_files)
        return compliance_report
    
    def _generate_compliance_report(self, violations: List[ComplianceViolation], 
                                  checked_files: List[str]) -> Dict[str, Any]:
        """
        Compliance raporu oluşturur
        """
        # Severity'e göre grupla
        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        
        for violation in violations:
            by_severity[violation.severity].append(violation)
        
        # Rule'a göre grupla
        by_rule = {}
        for violation in violations:
            if violation.rule_id not in by_rule:
                by_rule[violation.rule_id] = []
            by_rule[violation.rule_id].append(violation)
        
        # Dosyaya göre grupla
        by_file = {}
        for violation in violations:
            if violation.file_path not in by_file:
                by_file[violation.file_path] = []
            by_file[violation.file_path].append(violation)
        
        report = {
            "summary": {
                "total_files_checked": len(checked_files),
                "total_violations": len(violations),
                "critical_violations": len(by_severity["critical"]),
                "high_violations": len(by_severity["high"]),
                "medium_violations": len(by_severity["medium"]),
                "low_violations": len(by_severity["low"]),
                "compliance_score": self._calculate_compliance_score(violations, checked_files)
            },
            "violations_by_severity": by_severity,
            "violations_by_rule": by_rule,
            "violations_by_file": by_file,
            "checked_files": checked_files,
            "recommendations": self._generate_recommendations(by_rule)
        }
        
        return report
    
    def _calculate_compliance_score(self, violations: List[ComplianceViolation], 
                                  checked_files: List[str]) -> float:
        """
        Uyumluluk skoru hesaplar (0-100)
        """
        if not checked_files:
            return 100.0
        
        # Penalty weights
        penalty_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        
        total_penalty = sum(penalty_weights[v.severity] for v in violations)
        max_possible_penalty = len(checked_files) * 20  # Varsayılan max penalty per file
        
        if max_possible_penalty == 0:
            return 100.0
        
        score = max(0, 100 - (total_penalty / max_possible_penalty * 100))
        return round(score, 2)
    
    def _generate_recommendations(self, violations_by_rule: Dict) -> List[str]:
        """
        Genel öneriler oluşturur
        """
        recommendations = []
        
        for rule_id, rule_violations in violations_by_rule.items():
            if rule_violations:
                rule_config = self.compliance_rules[rule_id]
                recommendations.append(
                    f"{rule_config['name']}: {rule_config['recommendation']} "
                    f"({len(rule_violations)} ihlal)"
                )
        
        return recommendations
    
    def export_report(self, report: Dict[str, Any], output_path: str = None) -> str:
        """
        Raporu JSON olarak dışa aktarır
        """
        if output_path is None:
            output_path = os.path.join(self.project_root, "compliance_report.json")
        
        # Dataclass'ları serialize edilebilir hale getir
        serializable_report = self._make_serializable(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Compliance report exported to: {output_path}")
        return output_path
    
    def _make_serializable(self, obj: Any) -> Any:
        """
        Dataclass ve complex objectleri serialize edilebilir hale getirir
        """
        if isinstance(obj, ComplianceViolation):
            return {
                "rule_id": obj.rule_id,
                "rule_name": obj.rule_name, 
                "file_path": obj.file_path,
                "line_number": obj.line_number,
                "violation_text": obj.violation_text,
                "severity": obj.severity,
                "recommendation": obj.recommendation
            }
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj
    
    def print_summary_report(self, report: Dict[str, Any]) -> None:
        """
        Özet raporu konsola yazdırır
        """
        summary = report["summary"]
        
        print("\n" + "="*60)
        print("CLAUDE.md COMPLIANCE CHECKER RAPORU")
        print("="*60)
        
        print(f"\n📊 ÖZET:")
        print(f"   Kontrol edilen dosya sayısı: {summary['total_files_checked']}")
        print(f"   Toplam ihlal sayısı: {summary['total_violations']}")
        print(f"   Uyumluluk skoru: {summary['compliance_score']}%")
        
        print(f"\n🚨 SEVERITY DAĞILIMI:")
        print(f"   Critical: {summary['critical_violations']}")
        print(f"   High: {summary['high_violations']}")
        print(f"   Medium: {summary['medium_violations']}")
        print(f"   Low: {summary['low_violations']}")
        
        if report["recommendations"]:
            print(f"\n💡 ÖNERİLER:")
            for rec in report["recommendations"]:
                print(f"   • {rec}")
        
        # Critical violations detayı
        critical_violations = report["violations_by_severity"]["critical"]
        if critical_violations:
            print(f"\n🚨 KRİTİK İHLALLER:")
            for violation in critical_violations[:5]:  # İlk 5'ini göster
                print(f"   • {violation.rule_name}")
                print(f"     Dosya: {violation.file_path}:{violation.line_number}")
                print(f"     Kod: {violation.violation_text[:80]}...")
                print()
        
        print("="*60 + "\n")


def check_file_compliance(file_path: str) -> int:
    """
    Belirli bir dosyanın uyumluluğunu kontrol eder (hooks için)
    
    Returns:
        0: Compliance OK
        1: Violations found (blocks tool execution)
    """
    checker = ClaudeComplianceChecker()
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return 1
    
    # Tek dosya kontrolü
    violations = checker.check_file_compliance(file_path)
    
    if not violations:
        print(f"✅ CLAUDE.md compliant: {file_path}")
        return 0
    
    # Violations found - block execution
    print(f"🚨 CLAUDE.md VIOLATIONS FOUND in {file_path}:")
    for violation in violations[:3]:  # İlk 3 violation
        print(f"  • {violation.rule_name} (Line {violation.line_number})")
        print(f"    {violation.violation_text[:100]}...")
        print(f"    → {violation.recommendation}")
        print()
    
    print(f"💥 TOOL EXECUTION BLOCKED due to {len(violations)} violations")
    return 1  # Block tool execution


def main():
    """
    CLI interface for hooks integration
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="CLAUDE.md Compliance Checker")
    parser.add_argument("--check-file", help="Check specific file compliance (for hooks)")
    parser.add_argument("--check-edit", help="Check file before Edit tool execution")  
    parser.add_argument("--check-write", help="Check file before Write tool execution")
    parser.add_argument("--full-report", action="store_true", help="Generate full project report")
    
    args = parser.parse_args()
    
    # Hook mode - check specific file
    if args.check_file:
        exit_code = check_file_compliance(args.check_file)
        exit(exit_code)
    
    if args.check_edit:
        exit_code = check_file_compliance(args.check_edit)
        exit(exit_code)
        
    if args.check_write:
        exit_code = check_file_compliance(args.check_write)
        exit(exit_code)
    
    # Default: Full project report
    checker = ClaudeComplianceChecker()
    print("CLAUDE.md Compliance Checker başlatılıyor...")
    
    report = checker.check_project_compliance()
    checker.print_summary_report(report)
    report_path = checker.export_report(report)
    print(f"Detaylı rapor kaydedildi: {report_path}")


if __name__ == "__main__":
    main()