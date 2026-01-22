"""
Category Index - Tool Category Definitions and Mappings

Defines tool categories for the 3-stage selection system:
- scada: SCADA/HMI, tag operations, real-time monitoring
- workorder: Work order management, task assignment
- maintenance: TPM, predictive maintenance, spare parts
- alarm: Alarm management, notifications
- datascience: ML, forecasting, anomaly detection
- mes: Manufacturing execution, production tracking
- oee: OEE metrics, equipment efficiency
- quality: QC, SPC, inspection
- traceability: Product tracking, genealogy
- energy: Energy optimization, carbon footprint
- computer: File system, browser, code execution (HIGH RISK)
- general: Fallback category
"""

from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass, field


class ToolCategory(str, Enum):
    """Tool category classification"""
    SCADA = "scada"
    WORKORDER = "workorder"
    MAINTENANCE = "maintenance"
    ALARM = "alarm"
    DATASCIENCE = "datascience"
    MES = "mes"
    OEE = "oee"
    QUALITY = "quality"
    TRACEABILITY = "traceability"
    ENERGY = "energy"
    COMPUTER = "computer"
    GENERAL = "general"


@dataclass
class CategoryDefinition:
    """Definition for a tool category with keywords and patterns"""
    category: ToolCategory
    keywords: Set[str] = field(default_factory=set)
    patterns: List[str] = field(default_factory=list)
    description: str = ""
    risk_level: str = "low"  # low, medium, high, critical


class CategoryIndex:
    """Index of tool categories with keyword mappings for fast classification"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._categories: Dict[ToolCategory, CategoryDefinition] = {}
        self._keyword_index: Dict[str, Set[ToolCategory]] = {}
        self._initialize_categories()

    def _initialize_categories(self):
        """Initialize category definitions with keywords"""

        # SCADA Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.SCADA,
            keywords={
                "scada", "tag", "plc", "hmi", "sensor", "actuator", "setpoint",
                "realtime", "real-time", "live", "monitoring", "signal", "io",
                "channel", "address", "value", "read", "write", "analog", "digital",
                "modbus", "opc", "mqtt", "historian", "trend", "mimic", "screen",
                "dashboard", "widget", "gauge", "meter", "display"
            },
            patterns=["tag_*", "*_value", "get_tag*", "set_tag*", "read_*", "write_*"],
            description="SCADA/HMI operations, tag management, real-time monitoring",
            risk_level="medium"
        ))

        # Work Order Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.WORKORDER,
            keywords={
                "workorder", "work_order", "task", "assignment", "ticket", "request",
                "job", "order", "schedule", "assign", "complete", "close", "open",
                "priority", "due_date", "deadline", "technician", "worker", "crew",
                "dispatch", "status", "progress", "completion",
                # Turkish keywords
                "iş", "emri", "görev", "atama", "talep", "sipariş", "oluştur"
            },
            patterns=["create_workorder*", "update_workorder*", "*_task", "*_job"],
            description="Work order management, task assignment, job tracking",
            risk_level="low"
        ))

        # Maintenance Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.MAINTENANCE,
            keywords={
                "maintenance", "tpm", "predictive", "preventive", "corrective",
                "spare_part", "inventory", "health_score", "equipment", "asset",
                "breakdown", "repair", "overhaul", "inspection", "lubrication",
                "calibration", "autonomous", "scheduled", "mttr", "mtbf", "downtime",
                "uptime", "reliability", "failure", "fault"
            },
            patterns=["*_maintenance", "schedule_*", "health_*", "*_spare*"],
            description="TPM, predictive/preventive maintenance, spare parts management",
            risk_level="low"
        ))

        # Alarm Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.ALARM,
            keywords={
                "alarm", "alert", "notification", "warning", "critical", "emergency",
                "acknowledge", "ack", "confirm", "silence", "escalate", "priority",
                "severity", "threshold", "limit", "high", "low", "hihi", "lolo",
                "active", "cleared", "pending", "unacknowledged"
            },
            patterns=["*_alarm*", "*_alert*", "get_active*", "acknowledge_*"],
            description="Alarm management, notifications, alert handling",
            risk_level="low"
        ))

        # Data Science Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.DATASCIENCE,
            keywords={
                "datascience", "data_science", "ml", "machine_learning", "ai",
                "forecast", "prediction", "anomaly", "detection", "analysis",
                "model", "train", "inference", "correlation", "regression",
                "classification", "clustering", "timeseries", "resample", "aggregate",
                "statistics", "trend", "pattern", "insight", "prophet", "arima"
            },
            patterns=["run_*_analysis", "forecast_*", "detect_*", "train_*"],
            description="Machine learning, forecasting, anomaly detection, analytics",
            risk_level="low"
        ))

        # MES Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.MES,
            keywords={
                "mes", "production", "manufacturing", "batch", "lot", "routing",
                "bom", "bill_of_materials", "recipe", "process_order", "work_center",
                "operation", "sequence", "cycle_time", "takt_time", "throughput",
                "yield", "scrap", "rework", "wip", "work_in_progress"
            },
            patterns=["*_production*", "*_batch*", "*_lot*", "start_*", "end_*"],
            description="Manufacturing execution, production tracking, batch management",
            risk_level="medium"
        ))

        # OEE Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.OEE,
            keywords={
                "oee", "overall_equipment_effectiveness", "availability", "performance",
                "quality_rate", "downtime", "planned_stop", "unplanned_stop", "speed_loss",
                "minor_stop", "defect", "reject", "ideal_cycle", "actual_cycle",
                "shift", "utilization", "efficiency", "productivity"
            },
            patterns=["get_oee*", "calculate_*", "*_efficiency*", "*_downtime*"],
            description="OEE metrics, equipment effectiveness, efficiency tracking",
            risk_level="low"
        ))

        # Quality Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.QUALITY,
            keywords={
                "quality", "qc", "spc", "statistical_process_control", "inspection",
                "measurement", "specification", "tolerance", "cpk", "ppk", "ucl", "lcl",
                "control_chart", "xbar", "range", "defect", "nonconformance", "ncr",
                "capa", "audit", "certificate", "coa", "test", "sample"
            },
            patterns=["*_inspection*", "*_measurement*", "spc_*", "check_*"],
            description="Quality control, SPC, inspection, compliance",
            risk_level="low"
        ))

        # Traceability Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.TRACEABILITY,
            keywords={
                "traceability", "trace", "track", "genealogy", "serial", "barcode",
                "qr_code", "rfid", "lot_tracking", "batch_tracking", "material",
                "component", "assembly", "parent", "child", "where_used", "contains",
                "recall", "containment", "supplier", "origin"
            },
            patterns=["trace_*", "track_*", "*_genealogy*", "get_history*"],
            description="Product traceability, genealogy, material tracking",
            risk_level="low"
        ))

        # Energy Category
        self._add_category(CategoryDefinition(
            category=ToolCategory.ENERGY,
            keywords={
                "energy", "power", "electricity", "gas", "water", "consumption",
                "kwh", "mwh", "carbon", "emission", "footprint", "sustainability",
                "efficiency", "optimization", "cost", "tariff", "peak", "demand",
                "renewable", "solar", "wind", "green",
                # Turkish keywords
                "enerji", "elektrik", "tüketim", "güç", "karbon", "verimlilik"
            },
            patterns=["*_energy*", "*_consumption*", "*_carbon*", "optimize_*"],
            description="Energy management, carbon footprint, sustainability",
            risk_level="low"
        ))

        # Computer Category (HIGH RISK)
        self._add_category(CategoryDefinition(
            category=ToolCategory.COMPUTER,
            keywords={
                "computer", "file", "filesystem", "directory", "folder", "browser",
                "web", "shell", "terminal", "command", "execute", "run", "script",
                "code", "compile", "install", "download", "upload", "delete", "remove",
                "copy", "move", "rename", "create", "write_file", "read_file",
                # Turkish keywords
                "python", "kod", "kodu", "çalıştır", "dosya", "klasör", "terminal",
                "komut", "yükle", "indir", "sil", "kopyala", "taşı"
            },
            patterns=["execute_*", "run_*", "file_*", "shell_*", "browser_*"],
            description="File system, browser, code execution - HIGH RISK operations",
            risk_level="critical"
        ))

        # General Category (Fallback)
        self._add_category(CategoryDefinition(
            category=ToolCategory.GENERAL,
            keywords={
                "help", "info", "status", "list", "get", "search", "find", "query",
                "count", "summary", "overview", "report", "export", "import"
            },
            patterns=["*"],
            description="General operations, fallback category",
            risk_level="low"
        ))

        # Build keyword index for fast lookup
        self._build_keyword_index()

    def _add_category(self, definition: CategoryDefinition):
        """Add a category definition"""
        self._categories[definition.category] = definition

    def _build_keyword_index(self):
        """Build inverted index from keywords to categories"""
        for category, definition in self._categories.items():
            for keyword in definition.keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = set()
                self._keyword_index[keyword].add(category)

    def get_category(self, category: ToolCategory) -> CategoryDefinition:
        """Get category definition"""
        return self._categories.get(category)

    def get_categories_for_keyword(self, keyword: str) -> Set[ToolCategory]:
        """Get categories matching a keyword"""
        keyword_lower = keyword.lower().replace("-", "_").replace(" ", "_")
        return self._keyword_index.get(keyword_lower, set())

    def get_all_keywords(self, category: ToolCategory) -> Set[str]:
        """Get all keywords for a category"""
        definition = self._categories.get(category)
        return definition.keywords if definition else set()

    def get_risk_level(self, category: ToolCategory) -> str:
        """Get risk level for a category"""
        definition = self._categories.get(category)
        return definition.risk_level if definition else "low"

    def classify_by_keywords(self, text: str) -> Dict[ToolCategory, float]:
        """Classify text by keyword matching, return category scores"""
        text_lower = text.lower()
        words = set(text_lower.replace("-", "_").replace(".", " ").split())

        scores: Dict[ToolCategory, float] = {}

        for category, definition in self._categories.items():
            if category == ToolCategory.GENERAL:
                continue  # Skip general for scoring

            matches = words.intersection(definition.keywords)
            if matches:
                # Score based on number of matches
                score = len(matches) / len(definition.keywords)
                scores[category] = score

        # Normalize scores
        total_score = sum(scores.values())
        if total_score > 0:
            scores = {k: v / total_score for k, v in scores.items()}

        return scores

    def get_top_categories(self, text: str, top_n: int = 3) -> List[ToolCategory]:
        """Get top N categories for text"""
        scores = self.classify_by_keywords(text)
        if not scores:
            return [ToolCategory.GENERAL]

        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_categories[:top_n]]
