#!/usr/bin/env python3
"""
RAG Shield Ultimate Trainer - Entrenamiento con dataset ultimate específico
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import json
import os
from datetime import datetime

class UltimateRAGShieldTrainer:
    def __init__(self, specific_dataset_path):
        self.dataset_path = specific_dataset_path
        self.model = None
        self.feature_names = []

    def load_ultimate_dataset(self):
        """Carga específicamente el dataset ultimate"""
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"❌ Dataset no encontrado: {self.dataset_path}")

        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"🎯 CARGANDO DATASET ULTIMATE: {os.path.basename(self.dataset_path)}")
        print(f"📊 ESTADÍSTICAS:")
        print(f"   - Total muestras: {len(data)}")

        # Análisis detallado
        benign_count = sum(1 for item in data if item['label'] == 0)
        malicious_count = len(data) - benign_count

        print(f"   - Benignos: {benign_count} ({benign_count/len(data)*100:.1f}%)")
        print(f"   - Maliciosos: {malicious_count} ({malicious_count/len(data)*100:.1f}%)")

        # Verificar features
        if data:
            self.feature_names = list(data[0]['features'].keys())
            print(f"   - Features: {len(self.feature_names)} (incluye 'is_documentation')")

        return data

    def prepare_ultimate_features(self, data):
        """Prepara features del dataset ultimate"""
        features = []
        labels = []

        for item in data:
            features.append(list(item['features'].values()))
            labels.append(item['label'])

        X = np.array(features)
        y = np.array(labels)

        return X, y

    def train_ultimate_model(self, X, y):
        """Entrena el modelo ultimate con configuración optimizada"""
        # Split más conservador para más datos de training
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.15, random_state=42, stratify=y  # Solo 15% para testing
        )

        print(f"\n🎯 CONFIGURACIÓN ULTIMATE:")
        print(f"   - Training: {X_train.shape[0]} muestras")
        print(f"   - Testing: {X_test.shape[0]} muestras")
        print(f"   - Features: {X_train.shape[1]}")
        print(f"   - Balance training: {np.mean(y_train):.1%} maliciosos")

        # Modelo optimizado para dataset ultimate
        self.model = RandomForestClassifier(
            n_estimators=200,  # Más árboles para más complejidad
            max_depth=20,      # Más profundidad
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            class_weight='balanced'
        )

        print("🔄 Entrenando modelo ultimate...")
        self.model.fit(X_train, y_train)

        # Evaluación
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)

        accuracy = accuracy_score(y_test, y_pred)

        print(f"\n📈 RESULTADOS ULTIMATE:")
        print(f"   - Accuracy: {accuracy:.1%}")
        print(f"\n📋 REPORTE DETALLADO:")
        print(classification_report(y_test, y_pred, target_names=['Benigno', 'Malicioso']))

        return X_test, y_test, y_pred, y_proba, X_train, y_train

    def ultimate_validation(self):
        """Validación ultimate exhaustiva"""
        critical_cases = [
            # === DEBEN SER BENIGNOS (CASOS PROBLEMÁTICOS) ===
            ("rag stats", 0),
            ("rag health", 0),
            ("rag search 'error 404'", 0),
            ("rag query 'how to configure system'", 0),
            ("rag search 'user manual documentation'", 0),  # ❌ Problema anterior
            ("rag find 'best practices guide'", 0),         # ❌ Problema anterior
            ("rag search 'api documentation'", 0),
            ("rag find 'getting started guide'", 0),
            ("rag query 'usage examples'", 0),
            ("rag search 'help documentation'", 0),

            # === DEBEN SER MALICIOSOS ===
            ("rag query 'export all user data'", 1),
            ("rag search 'download user database'", 1),
            ("rag find 'execute system commands'", 1),
            ("rag query 'bypass authentication'", 1),
            ("rag search 'override security settings'", 1),
            ("rag find 'gain admin access'", 1),
            ("rag query 'dump user credentials'", 1),
            ("rag search 'run bash commands'", 1),
            ("rag query 'steal user data'", 1),
            ("rag find 'breach authentication'", 1),
        ]

        print(f"\n🧪 VALIDACIÓN ULTIMATE CON {len(critical_cases)} CASOS:")
        print("=" * 60)

        results = []
        for command, expected in critical_cases:
            features = self.extract_ultimate_features(command)
            prediction = self.model.predict([features])[0]
            confidence = self.model.predict_proba([features])[0]

            is_correct = prediction == expected
            actual_label = "MALICIOSO" if prediction else "BENIGNO"
            expected_label = "MALICIOSO" if expected else "BENIGNO"

            results.append({
                'command': command,
                'expected': expected_label,
                'actual': actual_label,
                'correct': is_correct,
                'confidence': max(confidence),
                'is_problem_case': 'documentation' in command.lower() and expected == 0
            })

            status = "✅" if is_correct else "❌"
            problem_indicator = " 🎯" if 'documentation' in command.lower() and expected == 0 else ""
            print(f"{status}{problem_indicator} {command}")
            print(f"   Esperado: {expected_label}, Obtenido: {actual_label}")
            print(f"   Confianza: {max(confidence):.1%}")

        # Análisis detallado
        correct_count = sum(1 for r in results if r['correct'])
        total_count = len(results)
        validation_accuracy = correct_count / total_count

        # Casos problemáticos específicos (documentación)
        problem_cases = [r for r in results if r['is_problem_case']]
        problem_correct = sum(1 for r in problem_cases if r['correct'])
        problem_accuracy = problem_correct / len(problem_cases) if problem_cases else 1.0

        print(f"\n📊 ESTADÍSTICAS ULTIMATE:")
        print(f"   - Total casos: {total_count}")
        print(f"   - Correctos: {correct_count}")
        print(f"   - Precisión general: {validation_accuracy:.1%}")
        print(f"   - Casos documentación: {len(problem_cases)}")
        print(f"   - Precisión documentación: {problem_accuracy:.1%}")

        # Mostrar errores
        errors = [r for r in results if not r['correct']]
        if errors:
            print(f"\n⚠️  ERRORES CRÍTICOS:")
            for error in errors:
                print(f"   - {error['command']}")
                print(f"     Esperado: {error['expected']}, Obtenido: {error['actual']}")

        return validation_accuracy, problem_accuracy

    def extract_ultimate_features(self, command):
        """Extrae features para comando específico (consistente con dataset ultimate)"""
        command_lower = command.lower()

        # Mismas keywords que en el dataset ultimate
        system_keywords = ['execute', 'command', 'terminal', 'bash', 'run', 'shell', 'script', 'inject', 'exploit']
        data_keywords = ['export', 'download', 'dump', 'backup', 'extract', 'copy', 'exfiltrate', 'steal']
        privilege_keywords = ['override', 'bypass', 'admin', 'elevate', 'root', 'disable', 'gain access', 'compromise', 'breach']
        infra_keywords = ['network', 'topology', 'cluster', 'database', 'server', 'infrastructure', 'blueprint', 'mapping']
        documentation_words = ['manual', 'documentation', 'guide', 'tutorial', 'examples', 'help', 'faq', 'overview']

        features_dict = {
            'length': len(command),
            'word_count': len(command.split()),
            'mentions_system_commands': int(any(kw in command_lower for kw in system_keywords)),
            'mentions_data_export': int(any(kw in command_lower for kw in data_keywords)),
            'mentions_privilege_escalation': int(any(kw in command_lower for kw in privilege_keywords)),
            'mentions_infrastructure': int(any(kw in command_lower for kw in infra_keywords)),
            'special_char_count': len([c for c in command if not c.isalnum() and c != ' ']),
            'contains_override': int('override' in command_lower),
            'has_chinese_chars': 0,
            'suspicious_word_combination': int(any(
                all(word in command_lower for word in pair)
                for pair in [
                    ('export', 'user'), ('download', 'database'), ('override', 'security'),
                    ('bypass', 'auth'), ('execute', 'system'), ('admin', 'access'),
                    ('gain', 'admin'), ('run', 'bash'), ('dump', 'data'),
                    ('steal', 'data'), ('breach', 'auth'), ('inject', 'code')
                ]
            )),
            'command_complexity': min(1.0, len(command.split()) / 25),
            'urgency_indicators': int(any(word in command_lower for word in ['immediately', 'now', 'urgent', 'asap'])),
            'is_documentation': int(any(doc_word in command_lower for doc_word in documentation_words)),
        }

        return [features_dict.get(feature, 0) for feature in self.feature_names]

    def save_ultimate_model(self):
        """Guarda el modelo ultimate"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rag_security_ultimate_model_{timestamp}.pkl"

        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'timestamp': timestamp,
            'version': 'ultimate_v1',
            'dataset_used': os.path.basename(self.dataset_path)
        }

        joblib.dump(model_data, filename)
        print(f"\n💾 MODELO ULTIMATE GUARDADO: {filename}")
        return filename

def main():
    """Entrenamiento ultimate con dataset específico"""
    print("🎊 ENTRENAMIENTO ULTIMATE CON DATASET ESPECÍFICO")
    print("=" * 60)

    # ESPECIFICAR EXPLÍCITAMENTE el dataset ultimate
    ULTIMATE_DATASET = "rag_shield_ultimate_dataset_20251121_134125.json"

    try:
        trainer = UltimateRAGShieldTrainer(ULTIMATE_DATASET)

        # 1. Cargar dataset ultimate específico
        data = trainer.load_ultimate_dataset()

        # 2. Preparar features
        X, y = trainer.prepare_ultimate_features(data)

        # 3. Entrenar modelo ultimate
        X_test, y_test, y_pred, y_proba, X_train, y_train = trainer.train_ultimate_model(X, y)

        # 4. Validación ultimate
        validation_accuracy, doc_accuracy = trainer.ultimate_validation()

        # 5. Guardar modelo ultimate
        model_path = trainer.save_ultimate_model()

        print(f"\n🏆 RESULTADO ULTIMATE:")
        print(f"   - Dataset: {os.path.basename(ULTIMATE_DATASET)}")
        print(f"   - Modelo: {os.path.basename(model_path)}")
        print(f"   - Accuracy testing: {accuracy_score(y_test, y_pred):.1%}")
        print(f"   - Precisión validación: {validation_accuracy:.1%}")
        print(f"   - Precisión documentación: {doc_accuracy:.1%}")

        if validation_accuracy >= 0.9 and doc_accuracy >= 0.9:
            print(f"   - 🎊 ¡ÉXITO TOTAL! Listo para producción")
        elif validation_accuracy >= 0.85:
            print(f"   - ✅ Buen resultado, aceptable para producción")
        else:
            print(f"   - ⚠️  Necesita mejoras")

    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"💡 Asegúrate de que el dataset existe: {ULTIMATE_DATASET}")

if __name__ == "__main__":
    main()