#!/usr/bin/env python3
"""
patch_service_vector_9feat.py — contrato de features del detector: 10 -> 9 (sin geo).

Baja el vector DDoS de servicio a 9 features, quitando geographical_concentration
(idx7, un 0.5f hardcodeado en servicio = el gemelo del sentinel de entrenamiento)
y reindexando idx8->7 (traffic_escalation) e idx9->8 (resource_saturation), para
que cardinalidad y orden del vector de servicio == feature_names de entrenamiento.

Toca 4 ficheros de producción, origen -> consumo:
  - ml-detector/src/feature_extractor.cpp   (la fuente de verdad del vector)
  - ml-detector/src/zmq_handler.cpp         (guard != N + designated initializers)
  - ml-detector/include/ml_defender/ddos_detector.hpp  (struct Features + to_array)
  - ml-detector/src/ddos_detector.cpp       (feature_array que alimenta predict_ddos)

NO toca: el campo protobuf geo (se conserva, enriquecimiento RAG), el lado sniffer,
ni los fixtures de test (se arreglan tras el build, que dirá cuáles rompen).

Es un ÚNICO commit a propósito: la idea es "el contrato del detector es 9". Dejar
el extractor en 10 y el struct en 9 sería un commit que no compila.

Modos: --dry (enseña diff, no escribe) | --apply (escribe). Idempotente. NO commitea.
El criterio de HECHO NO lo da este script: lo da que ml-detector COMPILE con 9.
"""
from __future__ import annotations
import argparse
import difflib
import sys
from pathlib import Path

# path relativo al root del repo -> lista de (etiqueta, old, new)
EDITS: dict[str, list[tuple[str, str, str]]] = {
    "ml-detector/src/feature_extractor.cpp": [
        (
            "extractor: vector a 9",
            ") {\n    std::vector<float> features(10);\n\n    // [0] SYN/ACK Ratio",
            ") {\n    std::vector<float> features(9);\n\n    // [0] SYN/ACK Ratio",
        ),
        (
            "extractor: fuera geo, reindex 8->7 9->8",
            "    // [7] Geographical Concentration (placeholder - implement if available)\n"
            "    features[7] = 0.5f;  // Default neutral value\n"
            "\n"
            "    // [8] Traffic Escalation Rate (using flow bytes/s)\n"
            "    float flow_bytes_per_sec = static_cast<float>(nf.flow_bytes_per_second());\n"
            "    features[8] = normalize(flow_bytes_per_sec, 0.0f, 1e6f);  // Normalize to 1Mbps\n"
            "\n"
            "    // [9] Resource Saturation Score (using packet rate)\n"
            "    float packet_rate = safe_divide(total_packets,\n"
            "                                    std::max(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 1.0f));\n"
            "    features[9] = normalize(packet_rate, 0.0f, 1000.0f);  // Normalize to 1000 pps\n"
            "\n"
            "    return features;",
            "    // [7] Traffic Escalation Rate (using flow bytes/s)\n"
            "    float flow_bytes_per_sec = static_cast<float>(nf.flow_bytes_per_second());\n"
            "    features[7] = normalize(flow_bytes_per_sec, 0.0f, 1e6f);  // Normalize to 1Mbps\n"
            "\n"
            "    // [8] Resource Saturation Score (using packet rate)\n"
            "    float packet_rate = safe_divide(total_packets,\n"
            "                                    std::max(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 1.0f));\n"
            "    features[8] = normalize(packet_rate, 0.0f, 1000.0f);  // Normalize to 1000 pps\n"
            "\n"
            "    return features;",
        ),
    ],
    "ml-detector/src/zmq_handler.cpp": [
        (
            "zmq: guard != 10 -> != 9",
            "if (ddos_features_vec.size() != 10) {\n"
            "                                throw std::runtime_error(\"Invalid DDoS feature count\");",
            "if (ddos_features_vec.size() != 9) {\n"
            "                                throw std::runtime_error(\"Invalid DDoS feature count\");",
        ),
        (
            "zmq: fuera geo del struct init, reindex 8->7 9->8",
            "                            .flow_completion_rate       = ddos_features_vec[6],\n"
            "                            .geographical_concentration = ddos_features_vec[7],\n"
            "                            .traffic_escalation_rate    = ddos_features_vec[8],\n"
            "                            .resource_saturation_score  = ddos_features_vec[9]",
            "                            .flow_completion_rate       = ddos_features_vec[6],\n"
            "                            .traffic_escalation_rate    = ddos_features_vec[7],\n"
            "                            .resource_saturation_score  = ddos_features_vec[8]",
        ),
    ],
    "ml-detector/include/ml_defender/ddos_detector.hpp": [
        (
            "hpp: num_features() a 9 con comentario (opción 3, sin acoplar header inline)",
            "    size_t num_features() const noexcept { return 10; }",
            "    size_t num_features() const noexcept { return 9; }  // == ddos::DDOS_NUM_FEATURES (header inline); mantener en sync",
        ),
        (
            "hpp: fuera miembro geo del struct",
            "        float flow_completion_rate;\n"
            "        float geographical_concentration;\n"
            "        float traffic_escalation_rate;",
            "        float flow_completion_rate;\n"
            "        float traffic_escalation_rate;",
        ),
        (
            "hpp: to_array a <float,9>",
            "        std::array<float, 10> to_array() const noexcept {",
            "        std::array<float, 9> to_array() const noexcept {",
        ),
        (
            "hpp: fuera geo de to_array",
            "                flow_completion_rate,\n"
            "                geographical_concentration,\n"
            "                traffic_escalation_rate,",
            "                flow_completion_rate,\n"
            "                traffic_escalation_rate,",
        ),
    ],
    "ml-detector/src/ddos_detector.cpp": [
        (
            "detector: fuera geo del feature_array, renumera comentarios",
            "        features.flow_completion_rate,           // [6]\n"
            "        features.geographical_concentration,     // [7]\n"
            "        features.traffic_escalation_rate,        // [8]\n"
            "        features.resource_saturation_score       // [9]\n"
            "    };",
            "        features.flow_completion_rate,           // [6]\n"
            "        features.traffic_escalation_rate,        // [7]\n"
            "        features.resource_saturation_score       // [8]\n"
            "    };",
        ),
    ],
    "ml-detector/src/main.cpp": [
        (
            "main: fuera geo del test_features (designated init)",
            "                .flow_completion_rate = 0.5f,\n"
            "                .geographical_concentration = 0.5f,\n"
            "                .traffic_escalation_rate = 0.5f,",
            "                .flow_completion_rate = 0.5f,\n"
            "                .traffic_escalation_rate = 0.5f,",
        ),
    ],
    "ml-detector/tests/unit/test_detectors.cpp": [
        (
            "test: assert num_features del DDoS a 9 (anclado en TEST 1, no toca Traffic/Internal)",
            "    std::cout << \"\\n\" << GREEN << \"=== TEST 1: DDoS Detector ===\" << RESET << \"\\n\";\n"
            "\n"
            "    DDoSDetector detector;\n"
            "\n"
            "    // Test metadata\n"
            "    assert(detector.num_trees() == 100);\n"
            "    assert(detector.num_features() == 10);",
            "    std::cout << \"\\n\" << GREEN << \"=== TEST 1: DDoS Detector ===\" << RESET << \"\\n\";\n"
            "\n"
            "    DDoSDetector detector;\n"
            "\n"
            "    // Test metadata\n"
            "    assert(detector.num_trees() == 100);\n"
            "    assert(detector.num_features() == 9);",
        ),
        (
            "test: fuera geo del fixture normal (L70)",
            "        0.90f,  // flow_completion_rate\n"
            "        0.30f,  // geographical_concentration\n"
            "        0.02f,  // traffic_escalation_rate",
            "        0.90f,  // flow_completion_rate\n"
            "        0.02f,  // traffic_escalation_rate",
        ),
        (
            "test: fuera geo del fixture ddos (L89)",
            "        0.20f,  // flow_completion_rate (incomplete flows)\n"
            "        0.85f,  // geographical_concentration\n"
            "        0.95f,  // traffic_escalation_rate (sudden spike)",
            "        0.20f,  // flow_completion_rate (incomplete flows)\n"
            "        0.95f,  // traffic_escalation_rate (sudden spike)",
        ),
        (
            "test: batch de 10 -> 9 valores (todos 0.5f, geo indistinguible)",
            "        features = {\n"
            "            0.5f, 0.5f, 0.5f, 0.5f, 0.5f,\n"
            "            0.5f, 0.5f, 0.5f, 0.5f, 0.5f\n"
            "        };",
            "        features = {\n"
            "            0.5f, 0.5f, 0.5f, 0.5f, 0.5f,\n"
            "            0.5f, 0.5f, 0.5f, 0.5f\n"
            "        };",
        ),
    ],
}


def classify(text: str, old: str, new: str) -> str:
    has_old, has_new = old in text, new in text
    if has_old and not has_new:
        return "pending"
    if has_new and not has_old:
        return "applied"
    if has_old and has_new:
        return "ambiguous"
    return "missing"


def near_match_report(text: str, old: str) -> str:
    """Diagnóstico cuando un 'old' no casa: busca la 1a línea con whitespace
    normalizado y reporta en qué línea del fichero aparece algo parecido."""
    needle = " ".join(old.strip().splitlines()[0].split())
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if needle and needle in " ".join(line.split()):
            hits.append(i)
    if hits:
        return (f"      (parecido en línea(s) {hits} con indentación distinta — "
                f"pásame esa región y ajusto el whitespace)")
    return "      (ni siquiera un parecido — ¿fichero o rama equivocada?)"


def process_file(root: Path, rel: str, edits, do_write: bool):
    path = root / rel
    if not path.is_file():
        return None, [(rel, "NO-EXISTE", f"no encuentro {path}")]
    original = path.read_text(encoding="utf-8")
    out = original
    states = []
    for label, old, new in edits:
        st = classify(out, old, new)
        states.append((label, st))
        if st == "pending":
            n = out.count(old)
            if n != 1:
                states[-1] = (label, f"MULTI({n})")
                continue
            out = out.replace(old, new)
    return (original, out, states), []


def main() -> None:
    ap = argparse.ArgumentParser(description="Contrato Features del detector: 10 -> 9 (sin geo).")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true", help="enseña el diff; no escribe")
    mode.add_argument("--apply", action="store_true", help="aplica los cambios")
    ap.add_argument("--root", type=Path, default=Path("."), help="raíz del repo (por defecto: CWD)")
    args = ap.parse_args()

    results = {}
    bad = False
    for rel, edits in EDITS.items():
        res, errs = process_file(args.root, rel, edits, args.apply)
        if errs:
            for r, code, msg in errs:
                print(f"[{code}] {r}: {msg}")
            bad = True
            continue
        original, out, states = res
        results[rel] = (original, out, states)

    print("== estado por edición ==")
    for rel, (original, out, states) in results.items():
        print(f"  {rel}")
        for label, st in states:
            flag = "" if st in ("pending", "applied") else "  <-- REVISAR"
            print(f"    [{st}] {label}{flag}")
            if st == "missing":
                # buscar el old de esa edición para el diagnóstico
                for lab, old, _new in EDITS[rel]:
                    if lab == label:
                        print(near_match_report(original, old))
        if not bad and out == original and all(s == "applied" for _, s in states):
            print("    (ya aplicado — no-op)")

    any_bad = bad or any(
        st not in ("pending", "applied")
        for _, _, states in results.values()
        for _, st in states
    )
    if any_bad:
        print("\n✗ estado inesperado en alguna edición — NO se escribe nada "
              "(el contrato debe caer atómico o no caer).")
        sys.exit(1)

    # diffs
    print("\n== diff ==")
    changed = False
    for rel, (original, out, _states) in results.items():
        if out == original:
            continue
        changed = True
        sys.stdout.write("".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            out.splitlines(keepends=True),
            fromfile=rel, tofile=rel + " (9feat)",
        )))

    if not changed:
        print("  (nada que cambiar; todo ya en 9 features)")
        return

    if args.dry:
        print("\n--dry: NO escrito. Revisa el diff y relanza con --apply.")
        return

    for rel, (original, out, _states) in results.items():
        if out != original:
            (args.root / rel).write_text(out, encoding="utf-8")
            print(f"✓ escrito {rel}")
    print("\nSiguiente: compila ml-detector. Que compile con DDOS_NUM_FEATURES=9 "
          "ES el criterio de HECHO. Luego, los fixtures de test que rompan.")


if __name__ == "__main__":
    main()