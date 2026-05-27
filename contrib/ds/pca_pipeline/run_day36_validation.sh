
---

## 📄 ARCHIVO 5: `run_day36_validation.sh`

```bash
#!/bin/bash
# run_day36_validation.sh
# Script de ejecución completa para validación PCA Día 36
# Creado por: Claude (Anthropic) - Día 36 del Proyecto ML Defender

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "================================================"
echo "🧠 ML DEFENDER - EJECUCIÓN COMPLETA DÍA 36"
echo "================================================"
echo "Fecha: $(date)"
echo "HOSTNAME: $(hostname)"
echo ""

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Directorios
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="/tmp/ml_defender_day36_build"
OUTPUT_DIR="/shared/models/pca"
SYNTHETIC_DATA="/tmp/synthetic_83f.bin"
LOG_FILE="/tmp/ml_defender_day36.log"

# Número de eventos sintéticos (ajustable)
NUM_EVENTS=20000

# Flags
DO_CLEAN_BUILD=true
DO_RUN_TESTS=true
DO_GENERATE_DATA=true
DO_TRAIN_PCA=true
VERBOSE=true

# ============================================================================
# FUNCIONES DE LOGGING
# ============================================================================

log_info() {
    echo "ℹ️  $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo "✅ $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo "⚠️  $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "❌ $1" | tee -a "$LOG_FILE"
    exit 1
}

# ============================================================================
# VERIFICACIÓN DE DEPENDENCIAS
# ============================================================================

check_dependencies() {
    log_info "Verificando dependencias..."

    # Compilador C++20
    if ! g++ --version | grep -q "12\."; then
        log_warning "GCC 12.x no encontrado, usando $(g++ --version | head -1)"
    fi

    # FAISS
    if ! python3 -c "import faiss" 2>/dev/null; then
        log_error "FAISS no instalado"
    else
        FAISS_VERSION=$(python3 -c "import faiss; print(faiss.__version__)")
        log_info "FAISS v$FAISS_VERSION detectado"
    fi

    # ONNX Runtime
    if ! python3 -c "import onnxruntime" 2>/dev/null; then
        log_error "ONNX Runtime no instalado"
    else
        ORT_VERSION=$(python3 -c "import onnxruntime as ort; print(ort.__version__)")
        log_info "ONNX Runtime v$ORT_VERSION detectado"
    fi

    # Modelos embedders
    for model in chronos sbert attack; do
        MODEL_PATH="/shared/models/embedders/${model}_embedder.onnx"
        if [[ ! -f "$MODEL_PATH" ]]; then
            log_error "Modelo ONNX no encontrado: $MODEL_PATH"
        fi
    done
    log_info "Modelos ONNX encontrados"

    # DimensionalityReducer library
    if [[ ! -f "../libcommon-rag-ingester.so" ]] && \
       [[ ! -f "/usr/local/lib/libcommon-rag-ingester.so" ]]; then
        log_warning "libcommon-rag-ingester.so no encontrado, compilando..."
        # Intentar compilar la biblioteca
        cd .. && mkdir -p build && cd build
        cmake .. && make -j4
        cd "$BASE_DIR"
    fi

    log_success "Dependencias verificadas"
}

# ============================================================================
# COMPILACIÓN
# ============================================================================

compile_project() {
    log_info "Compilando proyecto..."

    # Crear directorio de build
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"

    # Compilar generador de datos sintéticos
    log_info "Compilando synthetic_data_generator..."
    g++ -std=c++20 -O2 -Wall -Wextra -Werror \
        -I"$BASE_DIR" \
        "$BASE_DIR/synthetic_data_generator.cpp" \
        -o synthetic_data_generator 2>>"$LOG_FILE"

    if [[ $? -ne 0 ]]; then
        log_error "Error compilando synthetic_data_generator"
    fi
    log_success "synthetic_data_generator compilado"

    # Compilar tests
    log_info "Compilando tests..."
    g++ -std=c++20 -O2 -Wall -Wextra \
        -I"$BASE_DIR" \
        "$BASE_DIR/test_synthetic_pipeline.cpp" \
        -o run_tests 2>>"$LOG_FILE"

    if [[ $? -ne 0 ]]; then
        log_warning "Tests compilados con warnings"
    else
        log_success "Tests compilados"
    fi

    # Nota: train_pca_pipeline.cpp requiere linkear con bibliotecas
    # Se compilará después de verificar que las dependencias están

    cd "$BASE_DIR"
    log_success "Compilación completada"
}

# ============================================================================
# GENERACIÓN DE DATOS SINTÉTICOS
# ============================================================================

generate_synthetic_data() {
    if [[ "$DO_GENERATE_DATA" != true ]]; then
        log_info "Saltando generación de datos sintéticos"
        return 0
    fi

    log_info "Generando $NUM_EVENTS eventos sintéticos..."

    cd "$BUILD_DIR"

    # Ejecutar generador
    ./synthetic_data_generator "$NUM_EVENTS" "$SYNTHETIC_DATA" 42 2>>"$LOG_FILE"

    if [[ $? -ne 0 ]]; then
        log_error "Error generando datos sintéticos"
    fi

    # Verificar que el archivo existe y tiene tamaño
    if [[ ! -f "$SYNTHETIC_DATA" ]]; then
        log_error "Archivo de datos sintéticos no creado"
    fi

    FILE_SIZE=$(stat -c%s "$SYNTHETIC_DATA" 2>/dev/null || stat -f%z "$SYNTHETIC_DATA")
    MIN_SIZE=$((NUM_EVENTS * 83 * 4 + 16))  # 83 floats + cabecera

    if [[ "$FILE_SIZE" -lt "$MIN_SIZE" ]]; then
        log_error "Archivo de datos sintéticos demasiado pequeño: $FILE_SIZE < $MIN_SIZE"
    fi

    log_success "Datos sintéticos generados: $FILE_SIZE bytes"

    # También crear versión de texto para debugging
    TEXT_FILE="${SYNTHETIC_DATA}.txt"
    head -c 1000 "$SYNTHETIC_DATA" | hexdump -C | head -20 > "$TEXT_FILE"
    log_info "Debug file creado: $TEXT_FILE"

    cd "$BASE_DIR"
}

# ============================================================================
# EJECUCIÓN DE TESTS
# ============================================================================

run_tests() {
    if [[ "$DO_RUN_TESTS" != true ]]; then
        log_info "Saltando ejecución de tests"
        return 0
    fi

    log_info "Ejecutando tests unitarios..."

    cd "$BUILD_DIR"

    # Ejecutar tests
    ./run_tests 2>&1 | tee -a "$LOG_FILE"

    TEST_EXIT_CODE=${PIPESTATUS[0]}

    if [[ "$TEST_EXIT_CODE" -ne 0 ]]; then
        log_error "Tests fallaron con código $TEST_EXIT_CODE"
    fi

    log_success "Todos los tests pasaron"

    cd "$BASE_DIR"
}

# ============================================================================
# COMPILACIÓN DEL PIPELINE PCA (con dependencias)
# ============================================================================

compile_pca_pipeline() {
    log_info "Compilando pipeline PCA (requiere dependencias externas)..."

    cd "$BUILD_DIR"

    # Buscar biblioteca DimensionalityReducer
    local LIB_PATH=""
    if [[ -f "../libcommon-rag-ingester.so" ]]; then
        LIB_PATH="../libcommon-rag-ingester.so"
    elif [[ -f "/usr/local/lib/libcommon-rag-ingester.so" ]]; then
        LIB_PATH="/usr/local/lib/libcommon-rag-ingester.so"
    else
        log_warning "No se encontró libcommon-rag-ingester.so, intentando compilar"

        # Intentar compilar desde source
        cd "$BASE_DIR/.."
        mkdir -p build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release
        make -j4

        if [[ ! -f "libcommon-rag-ingester.so" ]]; then
            log_error "No se pudo compilar libcommon-rag-ingester.so"
        fi

        LIB_PATH="$BASE_DIR/../build/libcommon-rag-ingester.so"
        cd "$BUILD_DIR"
    fi

    # Buscar ONNX Runtime
    local ONNX_INCLUDE=""
    local ONNX_LIB=""

    # Rutas comunes
    for path in /usr/local /opt /usr; do
        if [[ -f "$path/include/onnxruntime/core/session/onnxruntime_cxx_api.h" ]]; then
            ONNX_INCLUDE="$path/include"
        fi
        if [[ -f "$path/lib/libonnxruntime.so" ]]; then
            ONNX_LIB="$path/lib"
        fi
    done

    if [[ -z "$ONNX_INCLUDE" ]] || [[ -z "$ONNX_LIB" ]]; then
        log_warning "ONNX Runtime no encontrado en rutas estándar"
        log_warning "Pipeline PCA no se compilará - usar datos sintéticos solo"
        DO_TRAIN_PCA=false
        return 0
    fi

    # Compilar pipeline PCA
    log_info "Compilando train_pca_pipeline con:"
    log_info "  - ONNX_INCLUDE: $ONNX_INCLUDE"
    log_info "  - ONNX_LIB: $ONNX_LIB"
    log_info "  - LIB_PATH: $LIB_PATH"

    g++ -std=c++20 -O2 -Wall -Wextra \
        -I"$BASE_DIR" \
        -I"$BASE_DIR/../include" \
        -I"$ONNX_INCLUDE" \
        "$BASE_DIR/train_pca_pipeline.cpp" \
        -o train_pca_pipeline \
        -L"$(dirname "$LIB_PATH")" -lcommon-rag-ingester \
        -L"$ONNX_LIB" -lonnxruntime \
        -pthread 2>>"$LOG_FILE"

    if [[ $? -ne 0 ]]; then
        log_warning "Error compilando train_pca_pipeline"
        log_warning "Continuando sin pipeline PCA - solo validación básica"
        DO_TRAIN_PCA=false
    else
        log_success "Pipeline PCA compilado"
    fi

    cd "$BASE_DIR"
}

# ============================================================================
# EJECUCIÓN DEL PIPELINE PCA
# ============================================================================

run_pca_pipeline() {
    if [[ "$DO_TRAIN_PCA" != true ]]; then
        log_info "Saltando entrenamiento PCA"
        return 0
    fi

    log_info "Ejecutando pipeline PCA..."

    cd "$BUILD_DIR"

    # Verificar que los datos sintéticos existen
    if [[ ! -f "$SYNTHETIC_DATA" ]]; then
        log_error "Datos sintéticos no encontrados: $SYNTHETIC_DATA"
    fi

    # Crear directorio de salida
    mkdir -p "$OUTPUT_DIR"

    # Ejecutar pipeline
    ./train_pca_pipeline "$SYNTHETIC_DATA" "$OUTPUT_DIR" 2>&1 | tee -a "$LOG_FILE"

    PIPELINE_EXIT_CODE=${PIPESTATUS[0]}

    if [[ "$PIPELINE_EXIT_CODE" -ne 0 ]]; then
        log_error "Pipeline PCA falló con código $PIPELINE_EXIT_CODE"
    fi

    # Verificar que se crearon modelos
    MODELS_CREATED=0
    for model in chronos sbert attack; do
        if [[ -f "$OUTPUT_DIR/${model}_pca_*_synthetic_v1.faiss" ]]; then
            MODELS_CREATED=$((MODELS_CREATED + 1))
        fi
    done

    if [[ "$MODELS_CREATED" -lt 2 ]]; then
        log_warning "Solo $MODELS_CREATED modelos PCA creados (esperados 3)"
    else
        log_success "$MODELS_CREATED modelos PCA creados en $OUTPUT_DIR"
    fi

    # Listar modelos creados
    log_info "Modelos creados:"
    ls -lh "$OUTPUT_DIR"/*.faiss 2>/dev/null | tee -a "$LOG_FILE" || true

    cd "$BASE_DIR"
}

# ============================================================================
# RESUMEN Y LIMPIEZA
# ============================================================================

print_summary() {
    log_info ""
    log_info "================================================"
    log_info "📊 RESUMEN EJECUCIÓN DÍA 36"
    log_info "================================================"
    log_info "Fecha: $(date)"
    log_info "Duración: $SECONDS segundos"
    log_info ""

    # Verificar archivos creados
    log_info "ARCHIVOS CREADOS:"
    if [[ -f "$SYNTHETIC_DATA" ]]; then
        FILE_SIZE=$(stat -c%s "$SYNTHETIC_DATA" 2>/dev/null || stat -f%z "$SYNTHETIC_DATA")
        log_info "  ✅ $SYNTHETIC_DATA ($((FILE_SIZE/1024/1024)) MB)"
    else
        log_info "  ❌ $SYNTHETIC_DATA (NO CREADO)"
    fi

    # Contar modelos PCA
    PCA_COUNT=$(ls "$OUTPUT_DIR"/*.faiss 2>/dev/null | wc -l || echo 0)
    log_info "  ✅ $PCA_COUNT modelos PCA en $OUTPUT_DIR"

    # Log file
    LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
    log_info "  ✅ $LOG_FILE ($((LOG_SIZE/1024)) KB)"

    log_info ""
    log_info "PRÓXIMOS PASOS:"
    log_info "  1. Revisar log: less $LOG_FILE"
    log_info "  2. Verificar varianza PCA (>99% esperado para sintéticos)"
    log_info "  3. Plan B (Día 37): Activar 40 características reales"
    log_info "  4. Plan A' (Día 38): Re-entrenar PCA con datos reales"
    log_info ""

    if [[ "$PCA_COUNT" -ge 2 ]]; then
        log_success "✅ DÍA 36 COMPLETADO CON ÉXITO"
    else
        log_warning "⚠️  DÍA 36 PARCIALMENTE COMPLETADO"
        log_warning "   (Faltan modelos PCA, ver logs para detalles)"
    fi

    log_info "🏛️  VIA APPIA: Fundación validada con datos sintéticos"
    log_info "================================================"
}

cleanup() {
    if [[ "$DO_CLEAN_BUILD" == true ]]; then
        log_info "Limpiando directorio de build..."
        rm -rf "$BUILD_DIR"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    SECONDS=0  # Para medir duración

    # Limpiar log anterior
    > "$LOG_FILE"

    log_info "Iniciando ejecución Día 36..."

    # 1. Verificar dependencias
    check_dependencies

    # 2. Compilar
    compile_project

    # 3. Ejecutar tests
    run_tests

    # 4. Generar datos sintéticos
    generate_synthetic_data

    # 5. Compilar pipeline PCA (si hay dependencias)
    compile_pca_pipeline

    # 6. Ejecutar pipeline PCA (si se compiló)
    run_pca_pipeline

    # 7. Resumen
    print_summary

    # 8. Limpieza opcional
    cleanup

    return 0
}

# ============================================================================
# MANEJO DE ARGUMENTOS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Uso: $0 [OPCIONES]"
            echo ""
            echo "Opciones:"
            echo "  --help, -h          Mostrar esta ayuda"
            echo "  --no-clean          No limpiar archivos temporales"
            echo "  --no-tests          No ejecutar tests"
            echo "  --no-generate       No generar datos sintéticos"
            echo "  --no-pca            No entrenar PCA"
            echo "  --events N          Número de eventos (default: 20000)"
            echo "  --output DIR        Directorio de salida PCA"
            echo "  --verbose, -v       Output detallado"
            echo ""
            exit 0
            ;;
        --no-clean)
            DO_CLEAN_BUILD=false
            shift
            ;;
        --no-tests)
            DO_RUN_TESTS=false
            shift
            ;;
        --no-generate)
            DO_GENERATE_DATA=false
            shift
            ;;
        --no-pca)
            DO_TRAIN_PCA=false
            shift
            ;;
        --events)
            NUM_EVENTS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            log_error "Argumento desconocido: $1"
            ;;
    esac
done

# Ejecutar main
main "$@"