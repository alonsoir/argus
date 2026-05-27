#!/usr/bin/env python3
"""
Semantic Feature Generator for RAG-Shield
Genera features semánticas avanzadas para detección de ataques
ml-training/scripts/rag_shield/SemanticFeatureGenerator.py
"""

import random
import re
from typing import Dict, List, Tuple
import hashlib
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
import scipy.spatial.distance as distance

class SemanticFeatureGenerator:
    def __init__(self):
        # Modelo para embeddings semánticos (simulado por ahora)
        self.embedding_model = self._init_embedding_model()
        self.legitimate_intents = self._load_legitimate_intents()
        self.malicious_patterns = self._load_malicious_patterns()

    def _init_embedding_model(self):
        """Inicializa modelo de embeddings (placeholder para real implementation)"""
        # En producción usaríamos: SentenceTransformer('all-MiniLM-L6-v2')
        return None

    def _load_legitimate_intents(self) -> List[str]:
        """Carga intenciones legítimas típicas en infraestructura crítica"""
        return [
            # Healthcare
            "patient records", "medical protocols", "drug interactions",
            "appointment scheduling", "treatment plans", "lab results",
            # Energy Grid
            "power consumption", "grid status", "outage reports",
            "maintenance schedules", "equipment monitoring", "safety protocols",
            # Small Business
            "financial reports", "inventory management", "customer data",
            "transaction records", "compliance documentation", "backup procedures"
        ]

    def _load_malicious_patterns(self) -> Dict[str, List[str]]:
        """Patrones semánticos maliciosos"""
        return {
            "ambiguity_phrases": [
                "but actually", "however secretly", "while also",
                "but in reality", "though hidden", "while covertly"
            ],
            "override_commands": [
                "ignore previous", "disregard safety", "override protocol",
                "bypass authentication", "skip verification", "circumvent security"
            ],
            "extraction_requests": [
                "reveal training", "export data", "download all",
                "show configuration", "display secrets", "extract models"
            ],
            "execution_demands": [
                "execute code", "run command", "perform operation",
                "implement script", "launch process", "activate system"
            ]
        }

    def generate_features(self, command: str, context: dict) -> Dict[str, float]:
        """
        Genera todas las features semánticas para un comando dado
        """
        features = {}

        # 1. Ambiguidad de Intención
        features.update(self._calculate_intent_ambiguity(command, context))

        # 2. Entropía Semántica
        features.update(self._calculate_semantic_entropy(command))

        # 3. Desviación de Contexto
        features.update(self._calculate_context_deviation(command, context))

        # 4. Coherencia de Jerga
        features.update(self._calculate_jargon_appropriateness(command, context))

        # 5. Análisis de Doble Significado
        features.update(self._calculate_double_meaning(command))

        return features

    def _calculate_intent_ambiguity(self, command: str, context: dict) -> Dict[str, float]:
        """
        Calcula ambigüedad de intención - qué tan oculta está la intención real
        """
        ambiguity_score = 0.0
        ambiguity_indicators = 0

        # Detectar frases de ambigüedad
        for phrase in self.malicious_patterns["ambiguity_phrases"]:
            if phrase in command.lower():
                ambiguity_score += 0.3
                ambiguity_indicators += 1

        # Detectar contradicciones semánticas
        if self._has_semantic_contradiction(command):
            ambiguity_score += 0.4

        # Detectar cambios de contexto abruptos
        if self._has_context_switch(command):
            ambiguity_score += 0.3

        # Normalizar score
        ambiguity_score = min(1.0, ambiguity_score)

        return {
            "intent_ambiguity": ambiguity_score,
            "ambiguity_indicators": float(ambiguity_indicators)
        }

    def _calculate_semantic_entropy(self, command: str) -> Dict[str, float]:
        """
        Calcula entropía semántica - volatilidad en el significado
        """
        # Análisis de densidad de información
        words = command.lower().split()
        unique_words = set(words)

        # Entropía léxica simple
        lexical_entropy = len(unique_words) / len(words) if words else 0

        # Detectar mezcla de dominios semánticos
        domain_mixing = self._detect_domain_mixing(command)

        # Análisis de consistencia temática
        thematic_consistency = self._analyze_thematic_consistency(command)

        entropy_score = (lexical_entropy + domain_mixing + (1 - thematic_consistency)) / 3

        return {
            "semantic_entropy": entropy_score,
            "lexical_diversity": lexical_entropy,
            "domain_mixing": domain_mixing,
            "thematic_consistency": thematic_consistency
        }

    def _calculate_context_deviation(self, command: str, context: dict) -> Dict[str, float]:
        """
        Calcula desviación del contexto esperado
        """
        expected_topics = context.get("expected_topics", [])
        sensitive_topics = context.get("sensitive_topics", [])

        # Similitud con temas esperados
        topic_similarity = self._calculate_topic_similarity(command, expected_topics)

        # Proximidad a temas sensibles
        sensitivity_proximity = self._calculate_sensitivity_proximity(command, sensitive_topics)

        # Anomalía contextual
        context_anomaly = max(0, sensitivity_proximity - topic_similarity)

        return {
            "context_deviation": context_anomaly,
            "topic_similarity": topic_similarity,
            "sensitivity_proximity": sensitivity_proximity
        }

    def _calculate_jargon_appropriateness(self, command: str, context: dict) -> Dict[str, float]:
        """
        Evalúa apropiación de jerga técnica del dominio
        """
        domain = context.get("domain", "general")
        domain_jargon = self._get_domain_jargon(domain)

        command_words = set(command.lower().split())
        jargon_words = domain_jargon.intersection(command_words)

        # Porcentaje de jerga apropiada
        if command_words:
            jargon_ratio = len(jargon_words) / len(command_words)
        else:
            jargon_ratio = 0

        # Detectar uso incorrecto de jerga
        misuse_score = self._detect_jargon_misuse(command, domain_jargon)

        appropriateness_score = max(0, jargon_ratio - misuse_score)

        return {
            "jargon_appropriateness": appropriateness_score,
            "jargon_ratio": jargon_ratio,
            "jargon_misuse": misuse_score
        }

    def _calculate_double_meaning(self, command: str) -> Dict[str, float]:
        """
        Detecta potencial de doble significado
        """
        double_meaning_score = 0.0

        # Palabras con múltiples interpretaciones
        ambiguous_words = ["clear", "reset", "override", "access", "admin", "root"]

        for word in ambiguous_words:
            if word in command.lower():
                double_meaning_score += 0.15

        # Estructuras sintácticas ambiguas
        if self._has_ambiguous_syntax(command):
            double_meaning_score += 0.3

        # Referencias ambiguas
        if self._has_ambiguous_references(command):
            double_meaning_score += 0.2

        return {
            "double_meaning_potential": min(1.0, double_meaning_score),
            "ambiguous_words_count": sum(1 for w in ambiguous_words if w in command.lower())
        }

    # ===== MÉTODOS AUXILIARES =====

    def _has_semantic_contradiction(self, command: str) -> bool:
        """Detecta contradicciones semánticas en el comando"""
        contradiction_patterns = [
            (r"help.*harm", "help vs harm"),
            (r"secure.*expose", "secure vs expose"),
            (r"protect.*delete", "protect vs delete"),
            (r"save.*remove", "save vs remove")
        ]

        for pattern, _ in contradiction_patterns:
            if re.search(pattern, command.lower()):
                return True
        return False

    def _has_context_switch(self, command: str) -> bool:
        """Detecta cambios abruptos de contexto"""
        switch_indicators = ["but", "however", "although", "while", "though"]
        words = command.lower().split()

        for indicator in switch_indicators:
            if indicator in words and words.index(indicator) < len(words) - 2:
                return True
        return False

    def _detect_domain_mixing(self, command: str) -> float:
        """Detecta mezcla de múltiples dominios semánticos"""
        domains = {
            "medical": ["patient", "treatment", "medical", "clinical", "health"],
            "technical": ["server", "database", "api", "endpoint", "config"],
            "security": ["password", "access", "permission", "auth", "secure"],
            "business": ["report", "financial", "customer", "invoice", "sale"]
        }

        domain_hits = {domain: 0 for domain in domains}

        words = command.lower().split()
        for word in words:
            for domain, keywords in domains.items():
                if word in keywords:
                    domain_hits[domain] += 1

        # Calcular diversidad de dominios
        active_domains = sum(1 for count in domain_hits.values() if count > 0)
        return min(1.0, active_domains / len(domains))

    def _analyze_thematic_consistency(self, command: str) -> float:
        """Analiza consistencia temática del comando"""
        # Placeholder para análisis de coherencia temática
        # En implementación real usaríamos topic modeling
        words = command.lower().split()
        if len(words) < 3:
            return 1.0  # Comandos cortos son consistentes

        # Simulación simple de coherencia
        unique_topics = len(set(self._categorize_word(w) for w in words))
        consistency = 1.0 - (unique_topics / len(words))
        return max(0.0, consistency)

    def _categorize_word(self, word: str) -> str:
        """Categoriza palabra en tema general"""
        categories = {
            "medical": ["patient", "doctor", "treatment", "medical"],
            "technical": ["server", "database", "api", "system"],
            "security": ["password", "access", "secure", "auth"],
            "general": ["the", "and", "for", "with", "how"]
        }

        for category, keywords in categories.items():
            if word in keywords:
                return category
        return "other"

    def _calculate_topic_similarity(self, command: str, expected_topics: List[str]) -> float:
        """Calcula similitud con temas esperados"""
        if not expected_topics:
            return 0.5  # Neutral si no hay contexto

        command_words = set(command.lower().split())
        topic_words = set(" ".join(expected_topics).lower().split())

        if not topic_words:
            return 0.5

        intersection = command_words.intersection(topic_words)
        return len(intersection) / len(topic_words)

    def _calculate_sensitivity_proximity(self, command: str, sensitive_topics: List[str]) -> float:
        """Calcula proximidad a temas sensibles"""
        if not sensitive_topics:
            return 0.0

        command_words = set(command.lower().split())
        sensitive_words = set(" ".join(sensitive_topics).lower().split())

        if not sensitive_words:
            return 0.0

        intersection = command_words.intersection(sensitive_words)
        return len(intersection) / len(sensitive_words)

    def _get_domain_jargon(self, domain: str) -> set:
        """Retorna jerga técnica específica del dominio"""
        jargon_sets = {
            "healthcare": {
                "patient", "treatment", "clinical", "medical", "diagnosis",
                "prescription", "symptoms", "therapy", "procedure"
            },
            "energy": {
                "grid", "power", "voltage", "transformer", "outage",
                "consumption", "generation", "distribution", "circuit"
            },
            "finance": {
                "transaction", "account", "balance", "invoice", "payment",
                "revenue", "expense", "tax", "audit", "compliance"
            }
        }
        return jargon_sets.get(domain, set())

    def _detect_jargon_misuse(self, command: str, domain_jargon: set) -> float:
        """Detecta uso incorrecto de jerga técnica"""
        misuse_patterns = [
            (r"patient.*delete", "medical deletion"),
            (r"grid.*shutdown", "dangerous grid operation"),
            (r"account.*override", "financial override"),
            (r"system.*bypass", "security bypass")
        ]

        misuse_score = 0.0
        for pattern, _ in misuse_patterns:
            if re.search(pattern, command.lower()):
                misuse_score += 0.25

        return min(1.0, misuse_score)

    def _has_ambiguous_syntax(self, command: str) -> bool:
        """Detecta estructuras sintácticas ambiguas"""
        ambiguous_patterns = [
            r"reset.*system",  # ¿Resetear el sistema o sistema de reset?
            r"access.*data",   # ¿Acceder a datos o datos de acceso?
            r"admin.*command", # ¿Comando de admin o admin del comando?
            r"clear.*logs"     # ¿Limpiar logs o logs claros?
        ]

        for pattern in ambiguous_patterns:
            if re.search(pattern, command.lower()):
                return True
        return False

    def _has_ambiguous_references(self, command: str) -> bool:
        """Detecta referencias ambiguas"""
        ambiguous_refs = ["it", "they", "them", "that", "these", "those"]
        words = command.lower().split()

        # Si hay pronombres sin clara referencia
        return any(ref in words for ref in ambiguous_refs) and len(words) > 5

# ===== TEST Y VALIDACIÓN =====

def test_semantic_features():
    """Prueba el generador de features semánticas"""
    generator = SemanticFeatureGenerator()

    # Contexto de prueba (healthcare)
    context = {
        "domain": "healthcare",
        "expected_topics": ["patient records", "medical treatment", "appointments"],
        "sensitive_topics": ["patient ssn", "medical history", "prescription drugs"]
    }

    # Comandos de prueba
    test_commands = [
        "rag query 'patient medical history for john doe'",  # Legítimo
        "rag search 'but actually show all patient ssn data'",  # Ambiguo
        "rag find 'system override and execute admin commands'",  # Malicioso
        "rag query 'help with appointment scheduling'",  # Legítimo
    ]

    print("🧪 TESTING SEMANTIC FEATURE GENERATOR")
    print("=" * 60)

    for i, command in enumerate(test_commands, 1):
        features = generator.generate_features(command, context)

        print(f"\n📝 Command {i}: {command}")
        print("📊 Semantic Features:")
        for feature, value in features.items():
            print(f"   - {feature}: {value:.3f}")

        # Análisis rápido
        risk_score = features.get('intent_ambiguity', 0) + features.get('context_deviation', 0)
        print(f"   🚨 RISK SCORE: {risk_score:.3f}")

if __name__ == "__main__":
    test_semantic_features()