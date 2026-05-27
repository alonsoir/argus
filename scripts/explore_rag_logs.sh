#!/bin/bash
# ML Defender - RAG Logs Explorer
# Via Appia Quality: Know your data before processing 🏛️

set -e

RAG_BASE="/vagrant/logs/rag"
EVENTS_DIR="${RAG_BASE}/events"
ARTIFACTS_DIR="${RAG_BASE}/artifacts"

echo "🔍 ML Defender - RAG Logs Explorer"
echo "===================================="
echo ""

# Check if RAG directories exist
if [ ! -d "${RAG_BASE}" ]; then
    echo "❌ RAG base directory not found: ${RAG_BASE}"
    echo "   Please ensure ml-detector and RAG logger are running"
    exit 1
fi

echo "📁 RAG Directory Structure:"
echo "   Base: ${RAG_BASE}"
echo "   Events: ${EVENTS_DIR}"
echo "   Artifacts: ${ARTIFACTS_DIR}"
echo ""

# Explore JSONL event logs
echo "📊 JSONL Event Logs:"
echo "-------------------"

if [ -d "${EVENTS_DIR}" ]; then
    JSONL_FILES=$(find "${EVENTS_DIR}" -name "*.jsonl" -type f 2>/dev/null | sort)
    JSONL_COUNT=$(echo "${JSONL_FILES}" | grep -c "." || echo "0")

    if [ "${JSONL_COUNT}" -gt 0 ]; then
        echo "   Found ${JSONL_COUNT} JSONL file(s):"
        echo ""

        TOTAL_EVENTS=0

        for jsonl_file in ${JSONL_FILES}; do
            filename=$(basename "${jsonl_file}")
            event_count=$(wc -l < "${jsonl_file}")
            file_size=$(du -h "${jsonl_file}" | cut -f1)

            TOTAL_EVENTS=$((TOTAL_EVENTS + event_count))

            echo "   📄 ${filename}"
            echo "      Events: ${event_count}"
            echo "      Size: ${file_size}"

            # Show first event (sample)
            if [ "${event_count}" -gt 0 ]; then
                echo "      Sample (first event):"
                head -n1 "${jsonl_file}" | jq -C '.' 2>/dev/null | sed 's/^/         /' || echo "         (JSON parse failed)"
            fi
            echo ""
        done

        echo "   ✅ Total events across all files: ${TOTAL_EVENTS}"
    else
        echo "   ⚠️  No JSONL files found"
    fi
else
    echo "   ❌ Events directory not found: ${EVENTS_DIR}"
fi

echo ""

# Explore Protobuf/JSON artifacts
echo "📦 Artifacts (Protobuf + JSON):"
echo "-------------------------------"

if [ -d "${ARTIFACTS_DIR}" ]; then
    ARTIFACT_DIRS=$(find "${ARTIFACTS_DIR}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)
    DIR_COUNT=$(echo "${ARTIFACT_DIRS}" | grep -c "." || echo "0")

    if [ "${DIR_COUNT}" -gt 0 ]; then
        echo "   Found ${DIR_COUNT} artifact directory(ies):"
        echo ""

        TOTAL_PB=0
        TOTAL_JSON=0

        for artifact_dir in ${ARTIFACT_DIRS}; do
            dirname=$(basename "${artifact_dir}")
            pb_count=$(find "${artifact_dir}" -name "*.pb" -type f 2>/dev/null | wc -l)
            json_count=$(find "${artifact_dir}" -name "*.json" -type f 2>/dev/null | wc -l)

            TOTAL_PB=$((TOTAL_PB + pb_count))
            TOTAL_JSON=$((TOTAL_JSON + json_count))

            echo "   📁 ${dirname}/"
            echo "      Protobuf files (.pb): ${pb_count}"
            echo "      JSON files (.json): ${json_count}"

            # Show sample artifact
            if [ "${json_count}" -gt 0 ]; then
                sample_json=$(find "${artifact_dir}" -name "*.json" -type f 2>/dev/null | head -n1)
                if [ -n "${sample_json}" ]; then
                    echo "      Sample artifact:"
                    cat "${sample_json}" | jq -C '.' 2>/dev/null | head -n20 | sed 's/^/         /' || echo "         (JSON parse failed)"
                fi
            fi
            echo ""
        done

        echo "   ✅ Total Protobuf artifacts: ${TOTAL_PB}"
        echo "   ✅ Total JSON artifacts: ${TOTAL_JSON}"
    else
        echo "   ⚠️  No artifact directories found"
    fi
else
    echo "   ❌ Artifacts directory not found: ${ARTIFACTS_DIR}"
fi

echo ""

# Summary and readiness check
echo "📋 Summary & FAISS Readiness:"
echo "=============================="

JSONL_READY="❌"
ARTIFACTS_READY="❌"

if [ "${JSONL_COUNT:-0}" -gt 0 ] && [ "${TOTAL_EVENTS:-0}" -gt 0 ]; then
    JSONL_READY="✅"
fi

if [ "${TOTAL_PB:-0}" -gt 0 ] && [ "${TOTAL_JSON:-0}" -gt 0 ]; then
    ARTIFACTS_READY="✅"
fi

echo "   JSONL Events: ${JSONL_READY}"
echo "   Artifacts: ${ARTIFACTS_READY}"
echo ""

if [ "${JSONL_READY}" == "✅" ] && [ "${ARTIFACTS_READY}" == "✅" ]; then
    echo "✅ RAG logs are ready for FAISS ingestion!"
    echo ""
    echo "Next steps:"
    echo "  1. Export ONNX models (Chronos, SBERT, Custom)"
    echo "  2. Implement ChunkCoordinator"
    echo "  3. Create embedders for the 3 indices"
    echo "  4. Process daily chunks into FAISS"
else
    echo "⚠️  RAG logs not fully ready. Possible reasons:"
    if [ "${JSONL_READY}" != "✅" ]; then
        echo "   - No JSONL event logs found (check ml-detector + RAG logger)"
    fi
    if [ "${ARTIFACTS_READY}" != "✅" ]; then
        echo "   - No artifact files found (check RAG logger configuration)"
    fi
    echo ""
    echo "   Generate some traffic to create logs, then run this script again."
fi

echo ""
echo "Via Appia Quality: Know your foundation before building 🏛️"