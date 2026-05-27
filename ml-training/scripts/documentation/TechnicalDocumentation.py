class TechnicalDocumentation:
    def generate_complete_documentation(self):
        """Genera documentación técnica completa con kernel/user space"""

        documentation = {
            'ransomware': {
                'objective': 'Detección de comportamiento ransomware en endpoints mediante análisis de patrones de sistema',
                'performance': '3,764 nodos totales - 37.6 nodos/árbol promedio',
                'accuracy': '1.0000 en datos sintéticos',
                'kernel_space_features': [
                    'io_intensity - Intensidad de operaciones I/O',
                    'file_operations - Operaciones de archivo (crear, eliminar, renombrar)',
                    'network_activity - Actividad de red del proceso',
                    'data_volume - Volumen de datos leídos/escritos',
                    'access_frequency - Frecuencia de acceso a recursos'
                ],
                'user_space_features': [
                    'entropy - Entropía comportamental del proceso',
                    'behavior_consistency - Consistencia del comportamiento temporal',
                    'temporal_pattern - Patrones temporales de actividad',
                    'process_anomaly - Anomalías estadísticas del proceso',
                    'resource_usage - Uso agregado de recursos del sistema'
                ],
                'integration_notes': 'Requiere hooks de syscall para file operations y network',
                'predict_function': 'predict_ransomware() - Probabilidad comportamiento ransomware (0.0 a 1.0)'
            },

            'external_traffic': {
                'objective': 'Clasificación de tráfico de red entre Internet y redes internas',
                'performance': '1,014 nodos totales - 10.1 nodos/árbol promedio',
                'accuracy': '1.0000 en datos sintéticos',
                'kernel_space_features': [
                    'packet_rate - Tasa de paquetes por segundo',
                    'connection_rate - Tasa de nuevas conexiones por segundo',
                    'tcp_udp_ratio - Ratio entre tráfico TCP y UDP',
                    'avg_packet_size - Tamaño promedio de paquetes',
                    'port_entropy - Entropía de distribución de puertos'
                ],
                'user_space_features': [
                    'flow_duration_std - Desviación estándar de duración de flujos',
                    'src_ip_entropy - Entropía de direcciones IP origen',
                    'dst_ip_concentration - Concentración de IPs destino',
                    'protocol_variety - Variedad de protocolos de red',
                    'temporal_consistency - Consistencia temporal de patrones'
                ],
                'integration_notes': 'Requiere captura a nivel de socket y análisis de headers IP',
                'predict_function': 'predict_traffic() - Probabilidad tráfico INTERNAL (0.0 a 1.0)'
            },

            'ddos': {
                'objective': 'Detección de ataques de Denegación de Servicio Distribuido en tiempo real',
                'performance': '612 nodos totales - 6.1 nodos/árbol promedio',
                'accuracy': '1.0000 en datos sintéticos',
                'kernel_space_features': [
                    'syn_ack_ratio - Ratio entre paquetes SYN y ACK',
                    'packet_symmetry - Simetría entre tráfico entrante/saliente',
                    'source_ip_dispersion - Dispersión de IPs origen',
                    'protocol_anomaly_score - Puntuación de anomalía de protocolos',
                    'packet_size_entropy - Entropía de tamaños de paquete'
                ],
                'user_space_features': [
                    'traffic_amplification_factor - Factor de amplificación de tráfico',
                    'flow_completion_rate - Tasa de completitud de flujos',
                    'geographical_concentration - Concentración geográfica de tráfico',
                    'traffic_escalation_rate - Tasa de escalada de tráfico',
                    'resource_saturation_score - Puntuación de saturación de recursos'
                ],
                'integration_notes': 'Crítico para detección temprana, requiere análisis en tiempo real',
                'predict_function': 'predict_ddos() - Probabilidad ataque DDoS (0.0 a 1.0)'
            },

            'internal_traffic': {
                'objective': 'Detección de amenazas internas y movimiento lateral en la red',
                'performance': '940 nodos totales - 9.4 nodos/árbol promedio',
                'accuracy': '1.0000 en datos sintéticos',
                'kernel_space_features': [
                    'internal_connection_rate - Tasa de conexiones internas',
                    'service_port_consistency - Consistencia de puertos de servicio',
                    'protocol_regularity - Regularidad de protocolos internos',
                    'packet_size_consistency - Consistencia de tamaños de paquete',
                    'connection_duration_std - Desviación de duración de conexiones'
                ],
                'user_space_features': [
                    'lateral_movement_score - Puntuación de movimiento lateral',
                    'service_discovery_patterns - Patrones de descubrimiento de servicios',
                    'data_exfiltration_indicators - Indicadores de exfiltración de datos',
                    'temporal_anomaly_score - Puntuación de anomalía temporal',
                    'access_pattern_entropy - Entropía de patrones de acceso'
                ],
                'integration_notes': 'Esencial para seguridad Zero-Trust, detecta amenazas que evadieron el perímetro',
                'predict_function': 'predict_internal() - Probabilidad tráfico SUSPICIOUS (0.0 a 1.0)'
            }
        }

        return documentation

    def generate_integration_guide(self):
        """Guía de integración para kernel/user space"""
        print("\n🔧 GUÍA DE INTEGRACIÓN KERNEL/USER SPACE")
        print("=" * 60)

        docs = self.generate_complete_documentation()

        for model_name, info in docs.items():
            print(f"\n🎯 {model_name.upper()}:")
            print(f"   KERNEL SPACE ({len(info['kernel_space_features'])} features):")
            for feature in info['kernel_space_features']:
                print(f"     • {feature}")
            print(f"   USER SPACE ({len(info['user_space_features'])} features):")
            for feature in info['user_space_features']:
                print(f"     • {feature}")
            print(f"   NOTAS: {info['integration_notes']}")
            print(f"   PREDICT: {info['predict_function']}")

    def generate_predict_functions_documentation(self):
        """Genera documentación de las funciones predict() disponibles"""

        predict_functions = {
            'ransomware': {
                'function': 'predict_ransomware',
                'namespace': 'ml_defender::ransomware',
                'parameters': 'const float features[RANSOMWARE_NUM_FEATURES]',
                'return': 'float - Probability of ransomware behavior (0.0 to 1.0)',
                'threshold': '> 0.8 for detection',
                'header_file': 'ransomware_trees_inline.hpp'
            },
            'external_traffic': {
                'function': 'predict_traffic',
                'namespace': 'ml_defender::traffic',
                'parameters': 'const float features[TRAFFIC_NUM_FEATURES]',
                'return': 'float - Probability of INTERNAL traffic (0.0 to 1.0)',
                'threshold': '> 0.5 for classification',
                'header_file': 'traffic_trees_inline.hpp'
            },
            'ddos': {
                'function': 'predict_ddos',
                'namespace': 'ml_defender::ddos',
                'parameters': 'const float features[DDOS_NUM_FEATURES]',
                'return': 'float - Probability of DDoS attack (0.0 to 1.0)',
                'threshold': '> 0.7 for mitigation',
                'header_file': 'ddos_trees_inline.hpp'
            },
            'internal_traffic': {
                'function': 'predict_internal',
                'namespace': 'ml_defender::internal',
                'parameters': 'const float features[INTERNAL_NUM_FEATURES]',
                'return': 'float - Probability of SUSPICIOUS traffic (0.0 to 1.0)',
                'threshold': '> 0.6 for investigation',
                'header_file': 'internal_trees_inline.hpp'
            }
        }

        print("\n🎯 FUNCIONES PREDICT() DISPONIBLES")
        print("=" * 50)

        for model, info in predict_functions.items():
            print(f"\n🔹 {model.upper()}:")
            print(f"   Function: {info['function']}")
            print(f"   Namespace: {info['namespace']}")
            print(f"   Parameters: {info['parameters']}")
            print(f"   Returns: {info['return']}")
            print(f"   Threshold: {info['threshold']}")
            print(f"   Header: {info['header_file']}")

    def generate_quick_start_examples(self):
        """Genera ejemplos de inicio rápido para usar las funciones predict()"""

        print("\n🚀 EJEMPLOS DE INICIO RÁPIDO - PREDICT()")
        print("=" * 55)

        print("""
// Incluir headers
#include "ddos_trees_inline.hpp"
#include "traffic_trees_inline.hpp" 
#include "internal_trees_inline.hpp"
#include "ransomware_trees_inline.hpp"

// Inferencia directa con funciones predict()
float features_ddos[DDOS_NUM_FEATURES] = {0.85f, 0.12f, 0.45f, 0.23f, 0.67f, 0.34f, 0.89f, 0.56f, 0.78f, 0.91f};
float ddos_risk = ml_defender::ddos::predict_ddos(features_ddos);

float features_traffic[TRAFFIC_NUM_FEATURES] = {...};
float traffic_type = ml_defender::traffic::predict_traffic(features_traffic);

float features_internal[INTERNAL_NUM_FEATURES] = {...};
float internal_threat = ml_defender::internal::predict_internal(features_internal);

float features_ransomware[RANSOMWARE_NUM_FEATURES] = {...};
float ransomware_prob = ml_defender::ransomware::predict_ransomware(features_ransomware);

// Tomar decisiones basadas en thresholds
if (ddos_risk > 0.7f) trigger_mitigation();
if (traffic_type > 0.5f) classify_as_internal();
if (internal_threat > 0.6f) investigate_incident();
if (ransomware_prob > 0.8f) isolate_process();
        """)

# Ejecutar documentación
if __name__ == "__main__":
    doc_gen = TechnicalDocumentation()
    doc_gen.generate_integration_guide()
    doc_gen.generate_predict_functions_documentation()
    doc_gen.generate_quick_start_examples()