// Integration test - Prueba integración con ML Defender
#include "ml_defender/ransomware_detector.hpp"
#include "classifier_tricapa.hpp"
#include "feature_extractor.hpp"
#include "config_loader.hpp"

void test_integration_with_classifier_tricapa() {
    // 1. Cargar config real
    ConfigLoader config("config/ml_detector_config.json");

    // 2. Inicializar classifier con detector embebido
    ClassifierTricapa classifier(config);

    // 3. Crear flow features reales
    FlowFeatures flow = create_real_flow_features();

    // 4. Pipeline completo: extract → detect → classify
    auto result = classifier.classify_level2(flow);

    // 5. Validar que el threshold del config (0.75) se aplica
    assert(result.applied_threshold == 0.75f);
}

void test_feature_extraction_pipeline() {
    // Probar que FeatureExtractor → RansomwareDetector funciona
    FeatureExtractor extractor;
    RansomwareDetector detector;

    // Extract features desde packet data real
    auto features = extractor.extract_ransomware_features(packet_data);

    // Predict usando features extraídas
    auto result = detector.predict(features);

    assert(result.probability >= 0.0f && result.probability <= 1.0f);
}

void test_config_loading_and_threshold() {
    // Validar que el threshold desde config.json se aplica correctamente
    ConfigLoader config("config/ml_detector_config.json");

    auto threshold = config.get_ransomware_threshold();
    assert(threshold == 0.75f);  // Del config que me mostraste

    RansomwareDetector detector;
    RansomwareDetector::Features borderline_features = /* ... */;

    auto result = detector.predict(borderline_features);

    // Probar comportamiento en el borde del threshold
    bool detected = result.is_ransomware(threshold);
    // ... validaciones
}

void test_performance_in_real_pipeline() {
    // Benchmark del detector dentro del pipeline completo
    // incluyendo deserialización protobuf, feature extraction, etc.
}
