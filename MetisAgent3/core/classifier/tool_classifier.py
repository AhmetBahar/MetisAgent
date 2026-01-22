"""
Tool Classifier - 3-Stage Tool Selection System

Orchestrates the complete tool selection pipeline:
Stage 1: Category Classification (fast, keyword-based)
Stage 1.5: Tool Shortlist (BM25 + optional embeddings)
Stage 2: Returns shortlist for main LLM selection

This reduces token usage by only sending 5-8 relevant tools
to the main LLM instead of all 50+ tools.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .category_index import ToolCategory, CategoryIndex
from .tool_shortlist import ToolShortlistSelector, ToolScore

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of the 3-stage classification process"""
    query: str
    primary_category: ToolCategory
    secondary_categories: List[ToolCategory]
    category_scores: Dict[ToolCategory, float]
    shortlist: List[ToolScore]
    tool_names: List[str]
    high_risk_detected: bool = False
    requires_confirmation: bool = False
    classification_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "query": self.query,
            "primary_category": self.primary_category.value,
            "secondary_categories": [c.value for c in self.secondary_categories],
            "category_scores": {k.value: v for k, v in self.category_scores.items()},
            "tool_names": self.tool_names,
            "high_risk_detected": self.high_risk_detected,
            "requires_confirmation": self.requires_confirmation,
            "classification_time_ms": self.classification_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class ToolClassifier:
    """
    3-Stage Tool Selection System.

    Usage:
        classifier = ToolClassifier()
        classifier.index_tools(tool_manager.registry.tools)

        result = classifier.classify(user_query)
        # result.tool_names contains 5-8 relevant tools for main LLM
    """

    def __init__(
        self,
        shortlist_size: int = 8,
        embedding_weight: float = 0.3,
        category_threshold: float = 0.1
    ):
        """
        Initialize tool classifier.

        Args:
            shortlist_size: Number of tools to include in shortlist (default 8)
            embedding_weight: Weight for embedding scores (0.0-1.0)
            category_threshold: Minimum score to include secondary categories
        """
        self.shortlist_size = shortlist_size
        self.category_threshold = category_threshold
        self.category_index = CategoryIndex()
        self.shortlist_selector = ToolShortlistSelector(embedding_weight)
        self.indexed = False
        self._tool_categories: Dict[str, ToolCategory] = {}

    def index_tools(self, tools_metadata: Dict[str, Any]):
        """
        Index all tools for classification.

        Args:
            tools_metadata: Dict of tool_name -> ToolMetadata
        """
        logger.info(f"Indexing {len(tools_metadata)} tools for classification")

        # Index in shortlist selector
        self.shortlist_selector.index_tools(tools_metadata)

        # Build tool -> category mapping
        for tool_name in tools_metadata:
            docs = self.shortlist_selector.tool_documents.get(tool_name, [])
            if docs:
                self._tool_categories[tool_name] = docs[0].category

        self.indexed = True
        logger.info(f"Tool classifier indexed: {self.shortlist_selector.get_tool_count()} tools, "
                   f"{self.shortlist_selector.get_capability_count()} capabilities")

    def classify(
        self,
        query: str,
        include_high_risk: bool = False,
        force_categories: Optional[List[ToolCategory]] = None
    ) -> ClassificationResult:
        """
        Classify query and return tool shortlist.

        Args:
            query: User query text
            include_high_risk: Whether to include high-risk tools (default False)
            force_categories: Override category detection with specific categories

        Returns:
            ClassificationResult with shortlist of tools
        """
        start_time = datetime.now()

        if not self.indexed:
            logger.warning("Tools not indexed, returning empty result")
            return ClassificationResult(
                query=query,
                primary_category=ToolCategory.GENERAL,
                secondary_categories=[],
                category_scores={},
                shortlist=[],
                tool_names=[]
            )

        # Stage 1: Category Classification
        if force_categories:
            categories = force_categories
            category_scores = {c: 1.0 for c in categories}
            primary_category = categories[0]
        else:
            category_scores = self.category_index.classify_by_keywords(query)
            categories = self._get_relevant_categories(category_scores)
            primary_category = categories[0] if categories else ToolCategory.GENERAL

        # Check for high-risk category
        high_risk_detected = any(
            self.category_index.get_risk_level(cat) in ('high', 'critical')
            for cat in categories
        )

        # Stage 1.5: Tool Shortlist (BM25 + embeddings)
        shortlist = self.shortlist_selector.get_shortlist(
            query=query,
            categories=categories if categories else None,
            top_k=self.shortlist_size,
            include_high_risk=include_high_risk
        )

        # Extract tool names
        tool_names = [score.tool_name for score in shortlist]

        # Check if any shortlisted tool requires confirmation
        requires_confirmation = any(
            self._check_requires_confirmation(score.tool_name)
            for score in shortlist
        )

        # Calculate classification time
        elapsed = datetime.now() - start_time
        classification_time_ms = elapsed.total_seconds() * 1000

        result = ClassificationResult(
            query=query,
            primary_category=primary_category,
            secondary_categories=categories[1:] if len(categories) > 1 else [],
            category_scores=category_scores,
            shortlist=shortlist,
            tool_names=tool_names,
            high_risk_detected=high_risk_detected,
            requires_confirmation=requires_confirmation,
            classification_time_ms=classification_time_ms
        )

        logger.info(f"Classified query: category={primary_category.value}, "
                   f"tools={len(tool_names)}, time={classification_time_ms:.1f}ms")

        return result

    def _get_relevant_categories(self, scores: Dict[ToolCategory, float]) -> List[ToolCategory]:
        """Get relevant categories above threshold"""
        if not scores:
            return [ToolCategory.GENERAL]

        # Filter by threshold
        relevant = [
            (cat, score)
            for cat, score in scores.items()
            if score >= self.category_threshold
        ]

        if not relevant:
            # Return top category if nothing above threshold
            top_cat = max(scores.items(), key=lambda x: x[1])
            return [top_cat[0]]

        # Sort by score and return categories
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in relevant]

    def _check_requires_confirmation(self, tool_name: str) -> bool:
        """Check if tool requires confirmation"""
        docs = self.shortlist_selector.tool_documents.get(tool_name, [])
        for doc in docs:
            if doc.requires_confirmation or doc.risk_level in ('high', 'critical'):
                return True
        return False

    def get_tool_category(self, tool_name: str) -> Optional[ToolCategory]:
        """Get category for a specific tool"""
        return self._tool_categories.get(tool_name)

    def get_tools_for_prompt(self, result: ClassificationResult) -> str:
        """
        Format shortlisted tools for LLM prompt.

        Returns a concise representation of tools for the main LLM.
        """
        lines = ["Available tools for this request:"]

        for score in result.shortlist:
            # Get capability descriptions
            docs = self.shortlist_selector.tool_documents.get(score.tool_name, [])
            capabilities = [doc.capability_name for doc in docs]

            risk_marker = ""
            if docs and docs[0].risk_level in ('high', 'critical'):
                risk_marker = " [HIGH RISK]"

            lines.append(f"- {score.tool_name}{risk_marker}: {', '.join(capabilities[:5])}")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics"""
        category_counts = {}
        for cat in ToolCategory:
            tools = self.shortlist_selector.get_tools_by_category(cat)
            category_counts[cat.value] = len(tools)

        return {
            "indexed": self.indexed,
            "total_tools": self.shortlist_selector.get_tool_count(),
            "total_capabilities": self.shortlist_selector.get_capability_count(),
            "shortlist_size": self.shortlist_size,
            "category_counts": category_counts
        }


class ToolClassifierFactory:
    """Factory for creating configured tool classifiers"""

    @staticmethod
    def create_default() -> ToolClassifier:
        """Create classifier with default settings"""
        return ToolClassifier(
            shortlist_size=8,
            embedding_weight=0.3,
            category_threshold=0.1
        )

    @staticmethod
    def create_strict() -> ToolClassifier:
        """Create classifier with strict settings (fewer tools)"""
        return ToolClassifier(
            shortlist_size=5,
            embedding_weight=0.3,
            category_threshold=0.2
        )

    @staticmethod
    def create_permissive() -> ToolClassifier:
        """Create classifier with permissive settings (more tools)"""
        return ToolClassifier(
            shortlist_size=12,
            embedding_weight=0.3,
            category_threshold=0.05
        )
