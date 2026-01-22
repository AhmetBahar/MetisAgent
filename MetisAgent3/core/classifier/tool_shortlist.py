"""
Tool Shortlist Selector - Stage 1.5 of 3-Stage Selection

Implements BM25 + embedding scoring to select 5-8 tools from category.
This reduces the number of tools sent to the main LLM for final selection.

Algorithm:
1. Get tools from classified categories
2. Score tools using BM25 on capability descriptions
3. Optionally boost with embedding similarity (if available)
4. Return top-k tools (default 8)
"""

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from .category_index import ToolCategory, CategoryIndex

logger = logging.getLogger(__name__)


@dataclass
class ToolScore:
    """Score for a tool in shortlist selection"""
    tool_name: str
    capability_name: str
    bm25_score: float = 0.0
    embedding_score: float = 0.0
    category_boost: float = 0.0
    total_score: float = 0.0


@dataclass
class ToolDocument:
    """Document representation of a tool for indexing"""
    tool_name: str
    capability_name: str
    category: ToolCategory
    text: str  # Combined searchable text
    tokens: List[str] = field(default_factory=list)
    risk_level: str = "low"
    requires_confirmation: bool = False


class BM25Index:
    """BM25 index for tool documents"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[ToolDocument] = []
        self.doc_freqs: Dict[str, int] = defaultdict(int)  # term -> doc frequency
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.idf_cache: Dict[str, float] = {}

    def add_document(self, doc: ToolDocument):
        """Add a document to the index"""
        self.documents.append(doc)
        self.doc_lengths.append(len(doc.tokens))

        # Update document frequencies
        seen_terms = set()
        for token in doc.tokens:
            if token not in seen_terms:
                self.doc_freqs[token] += 1
                seen_terms.add(token)

        # Update average document length
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)

        # Clear IDF cache
        self.idf_cache.clear()

    def _compute_idf(self, term: str) -> float:
        """Compute IDF for a term"""
        if term in self.idf_cache:
            return self.idf_cache[term]

        n = len(self.documents)
        df = self.doc_freqs.get(term, 0)

        if df == 0:
            idf = 0.0
        else:
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)

        self.idf_cache[term] = idf
        return idf

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        """Compute BM25 score for a document given query tokens"""
        doc = self.documents[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        score = 0.0

        # Count term frequencies in document
        term_freqs = defaultdict(int)
        for token in doc.tokens:
            term_freqs[token] += 1

        for term in query_tokens:
            if term not in term_freqs:
                continue

            tf = term_freqs[term]
            idf = self._compute_idf(term)

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))
            score += idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Search for documents matching query, return (doc_idx, score) pairs"""
        query_tokens = tokenize(query)

        scores = []
        for idx in range(len(self.documents)):
            score = self.score(query_tokens, idx)
            if score > 0:
                scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def tokenize(text: str) -> List[str]:
    """Tokenize text for BM25 indexing"""
    # Lowercase and split on non-alphanumeric characters
    text = text.lower()
    tokens = re.split(r'[^a-z0-9]+', text)
    # Remove empty tokens and very short tokens
    tokens = [t for t in tokens if len(t) > 1]
    return tokens


class ToolShortlistSelector:
    """
    Selects shortlist of tools for main LLM using BM25 + optional embeddings.

    Usage:
        selector = ToolShortlistSelector()
        selector.index_tools(tools_metadata)  # Index all tools
        shortlist = selector.get_shortlist(query, categories, top_k=8)
    """

    def __init__(self, embedding_weight: float = 0.3):
        """
        Initialize shortlist selector.

        Args:
            embedding_weight: Weight for embedding scores (0.0-1.0)
                            BM25 weight = 1.0 - embedding_weight
        """
        self.bm25_index = BM25Index()
        self.embedding_weight = embedding_weight
        self.category_index = CategoryIndex()
        self.tool_documents: Dict[str, List[ToolDocument]] = {}  # tool_name -> documents
        self.embedding_service = None  # Optional embedding service

    def index_tools(self, tools_metadata: Dict[str, Any]):
        """
        Index all tools for shortlist selection.

        Args:
            tools_metadata: Dict of tool_name -> ToolMetadata
        """
        logger.info(f"Indexing {len(tools_metadata)} tools for shortlist selection")

        for tool_name, metadata in tools_metadata.items():
            self._index_tool(tool_name, metadata)

        logger.info(f"Indexed {len(self.bm25_index.documents)} capabilities from {len(tools_metadata)} tools")

    def _index_tool(self, tool_name: str, metadata: Any):
        """Index a single tool's capabilities"""
        # Determine tool category from name or tags
        category = self._detect_category(tool_name, metadata)

        # Get risk level from category or metadata
        risk_level = getattr(metadata, 'risk_level', None)
        if not risk_level:
            risk_level = self.category_index.get_risk_level(category)

        requires_confirmation = getattr(metadata, 'requires_confirmation', False)

        self.tool_documents[tool_name] = []

        # Index each capability
        capabilities = getattr(metadata, 'capabilities', [])
        for cap in capabilities:
            cap_name = getattr(cap, 'name', str(cap))
            cap_desc = getattr(cap, 'description', '')
            cap_type = getattr(cap, 'capability_type', None)

            # Build searchable text
            text_parts = [
                tool_name,
                cap_name,
                cap_desc,
                str(cap_type.value) if cap_type else ''
            ]

            # Add input/output schema fields if available
            input_schema = getattr(cap, 'input_schema', {})
            if input_schema:
                text_parts.extend(input_schema.get('properties', {}).keys())

            text = ' '.join(text_parts)
            tokens = tokenize(text)

            doc = ToolDocument(
                tool_name=tool_name,
                capability_name=cap_name,
                category=category,
                text=text,
                tokens=tokens,
                risk_level=risk_level,
                requires_confirmation=requires_confirmation
            )

            self.bm25_index.add_document(doc)
            self.tool_documents[tool_name].append(doc)

    def _detect_category(self, tool_name: str, metadata: Any) -> ToolCategory:
        """Detect category from tool name and metadata"""
        # Check tags first
        tags = getattr(metadata, 'tags', set())
        for tag in tags:
            categories = self.category_index.get_categories_for_keyword(tag)
            if categories:
                return list(categories)[0]

        # Check tool name patterns
        tool_lower = tool_name.lower()
        if 'scada' in tool_lower or 'tag' in tool_lower:
            return ToolCategory.SCADA
        elif 'workorder' in tool_lower or 'work_order' in tool_lower:
            return ToolCategory.WORKORDER
        elif 'maintenance' in tool_lower:
            return ToolCategory.MAINTENANCE
        elif 'alarm' in tool_lower:
            return ToolCategory.ALARM
        elif 'datascience' in tool_lower or 'data_science' in tool_lower:
            return ToolCategory.DATASCIENCE
        elif 'mes' in tool_lower or 'production' in tool_lower:
            return ToolCategory.MES
        elif 'oee' in tool_lower:
            return ToolCategory.OEE
        elif 'quality' in tool_lower or 'qc' in tool_lower:
            return ToolCategory.QUALITY
        elif 'trace' in tool_lower:
            return ToolCategory.TRACEABILITY
        elif 'energy' in tool_lower:
            return ToolCategory.ENERGY
        elif 'computer' in tool_lower or 'file' in tool_lower or 'browser' in tool_lower:
            return ToolCategory.COMPUTER

        return ToolCategory.GENERAL

    def get_shortlist(
        self,
        query: str,
        categories: Optional[List[ToolCategory]] = None,
        top_k: int = 8,
        include_high_risk: bool = False
    ) -> List[ToolScore]:
        """
        Get shortlist of tools for query.

        Args:
            query: User query text
            categories: Optional list of categories to filter (from Stage 1)
            top_k: Number of tools to return (default 8)
            include_high_risk: Whether to include high-risk tools (default False)

        Returns:
            List of ToolScore objects sorted by total_score descending
        """
        if not self.bm25_index.documents:
            logger.warning("No tools indexed, returning empty shortlist")
            return []

        # BM25 search
        bm25_results = self.bm25_index.search(query, top_k=top_k * 3)  # Get more for filtering

        # Build scores
        scores: List[ToolScore] = []
        seen_tools: Set[str] = set()  # Avoid duplicate tools

        for doc_idx, bm25_score in bm25_results:
            doc = self.bm25_index.documents[doc_idx]

            # Filter by category if specified
            if categories and doc.category not in categories:
                continue

            # Filter high-risk tools unless explicitly allowed
            if not include_high_risk and doc.risk_level in ('high', 'critical'):
                continue

            # Skip if we already have this tool
            if doc.tool_name in seen_tools:
                continue

            seen_tools.add(doc.tool_name)

            # Category boost: higher score if category matches query
            category_boost = 0.0
            if categories and doc.category in categories:
                category_boost = 0.2

            # Calculate embedding score if service available
            embedding_score = 0.0
            if self.embedding_service:
                embedding_score = self._compute_embedding_score(query, doc)

            # Calculate total score
            bm25_weight = 1.0 - self.embedding_weight
            total_score = (
                bm25_score * bm25_weight +
                embedding_score * self.embedding_weight +
                category_boost
            )

            scores.append(ToolScore(
                tool_name=doc.tool_name,
                capability_name=doc.capability_name,
                bm25_score=bm25_score,
                embedding_score=embedding_score,
                category_boost=category_boost,
                total_score=total_score
            ))

        # Sort by total score and return top_k
        scores.sort(key=lambda x: x.total_score, reverse=True)
        return scores[:top_k]

    def _compute_embedding_score(self, query: str, doc: ToolDocument) -> float:
        """Compute embedding similarity score (placeholder)"""
        # This would use an embedding service to compute cosine similarity
        # between query embedding and document embedding
        # For now, return 0.0 as placeholder
        return 0.0

    def set_embedding_service(self, embedding_service):
        """Set embedding service for similarity scoring"""
        self.embedding_service = embedding_service

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get all tools in a category"""
        tools = set()
        for doc in self.bm25_index.documents:
            if doc.category == category:
                tools.add(doc.tool_name)
        return list(tools)

    def get_tool_count(self) -> int:
        """Get total number of indexed tools"""
        return len(self.tool_documents)

    def get_capability_count(self) -> int:
        """Get total number of indexed capabilities"""
        return len(self.bm25_index.documents)
