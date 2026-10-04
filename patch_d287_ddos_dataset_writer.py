#!/usr/bin/env python3
"""DAY287 [DDOS-DATASET-D287]: escritor de dataset DDoS v2 de laboratorio en el ml-detector.
CSV plano, un fichero por arranque, apagado por defecto. Columnas: identidad del evento,
8 rasgos del contrato v2 y veredicto del bosque viejo (old_ddos_prob, old_ddos_class; -1 = no evaluada).
Uso: python3 patch_d287_ddos_dataset_writer.py --check | --apply
Atomico (todo o nada), idempotente, no compila, no commitea."""
import json
import sys
from pathlib import Path

MARK = "[DDOS-DATASET-D287]"
ROOT = Path(__file__).resolve().parent
HDR_REL = "ml-detector/include/ddos_dataset_writer.hpp"

HDR_TEMPLATE = r'''// ddos_dataset_writer.hpp — aRGus NDR — DAY287 [DDOS-DATASET-D287]
// Dataset DDoS v2 de laboratorio: una fila por evento, en el mismo punto que [DDOS-V2],
// sin depender de VERBOSE. CSV plano (sin HMAC): la integridad la da el sha256 en el
// manifiesto del entrenamiento. Un fichero por arranque del ml-detector.
#pragma once
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <stdexcept>
#include <string>
@@PROTO_INCLUDE@@

namespace ml_defender {

class DdosDatasetWriter {
public:
    explicit DdosDatasetWriter(const std::string& base_dir) {
        std::filesystem::create_directories(base_dir);
        std::time_t t = std::time(nullptr);
        std::tm tm{};
        localtime_r(&t, &tm);
        char ts[32];
        std::strftime(ts, sizeof(ts), "%Y%m%d-%H%M%S", &tm);
        path_ = base_dir + "/ddos_dataset_" + ts + ".csv";
        out_.open(path_, std::ios::out | std::ios::trunc);
        if (!out_) throw std::runtime_error("no se pudo abrir " + path_);
        out_ << "ts_ns,community_id,src_ip,dst_ip,src_port,dst_port,proto,event_kind,"
                "syn_ack_ratio,mean_packet_size,reflection_signature,packet_size_entropy,"
                "flow_packet_count,flow_completion_rate,victim_rate_ratio,victim_pps,"
                "old_ddos_prob,old_ddos_class\n";
        out_.flush();
    }

    ~DdosDatasetWriter() {
        std::lock_guard<std::mutex> lock(mutex_);
        out_.flush();
    }

    DdosDatasetWriter(const DdosDatasetWriter&) = delete;
    DdosDatasetWriter& operator=(const DdosDatasetWriter&) = delete;

    // old_class < 0 => la cabeza vieja no corrio en este evento: prob y clase = -1
    void write(const protobuf::NetworkSecurityEvent& ev, int old_class, double old_prob) {
        const auto& nf = ev.network_features();
        const auto& d  = nf.ddos_embedded();
        const auto& ts = ev.event_timestamp();
        const unsigned long long ts_ns =
            static_cast<unsigned long long>(ts.seconds()) * 1000000000ULL +
            static_cast<unsigned long long>(ts.nanos());
        char buf[1024];
        const int n = std::snprintf(buf, sizeof(buf),
            "%llu,%s,%s,%s,%u,%u,%u,%d,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6f,%d\n",
            ts_ns, nf.community_id().c_str(), nf.source_ip().c_str(), nf.destination_ip().c_str(),
            static_cast<unsigned>(nf.source_port()), static_cast<unsigned>(nf.destination_port()),
            static_cast<unsigned>(nf.protocol_number()), static_cast<int>(ev.event_kind()),
            static_cast<double>(d.syn_ack_ratio()), static_cast<double>(d.mean_packet_size()),
            static_cast<double>(d.reflection_signature()), static_cast<double>(d.packet_size_entropy()),
            static_cast<double>(d.flow_packet_count()), static_cast<double>(d.flow_completion_rate()),
            static_cast<double>(d.victim_rate_ratio()), static_cast<double>(d.victim_pps()),
            old_class < 0 ? -1.0 : old_prob, old_class < 0 ? -1 : old_class);
        std::lock_guard<std::mutex> lock(mutex_);
        if (n <= 0 || n >= static_cast<int>(sizeof(buf))) { ++dropped_; return; }
        out_.write(buf, n);
        ++rows_;
        out_.flush();  // flush por fila: pipeline-stop no corre destructores (DAY287 P11, 26 filas perdidas)
    }

    const std::string& path() const noexcept { return path_; }

private:
    std::string path_;
    std::ofstream out_;
    std::mutex mutex_;
    uint64_t rows_ = 0;
    uint64_t dropped_ = 0;
};

}  // namespace ml_defender
'''

# (fichero, ancla exacta, insercion, 'after'|'before')
EDITS = [
    ("ml-detector/include/config_loader.hpp",
     "        int rotation_seconds;\n    } correlation_writer;\n",
     "\n    // [DDOS-DATASET-D287] dataset DDoS v2 de laboratorio (CSV plano); apagado por defecto\n"
     "    struct {\n"
     "        bool enabled = false;\n"
     "        std::string base_dir;\n"
     "    } ddos_dataset_writer;\n",
     "after"),
    ("ml-detector/src/config_loader.cpp",
     '        config.correlation_writer.rotation_seconds = get_required<int>(corr, "rotation_seconds", "correlation_writer");\n    }\n',
     "\n    // [DDOS-DATASET-D287] opcional: sin bloque en el JSON queda apagado\n"
     '    if (json_.contains("ddos_dataset_writer")) {\n'
     '        const auto& dd = json_["ddos_dataset_writer"];\n'
     '        config.ddos_dataset_writer.enabled  = dd.value("enabled", false);\n'
     '        config.ddos_dataset_writer.base_dir = dd.value("base_dir", std::string("/vagrant/logs/lab/ddos_dataset"));\n'
     "    }\n",
     "after"),
    ("ml-detector/include/zmq_handler.hpp",
     '#include "correlation_writer.hpp"\n',
     '#include "ddos_dataset_writer.hpp"  // [DDOS-DATASET-D287]\n',
     "after"),
    ("ml-detector/include/zmq_handler.hpp",
     "    std::shared_ptr<ml_defender::CorrelationWriter> correlation_writer_;\n",
     "    std::unique_ptr<ml_defender::DdosDatasetWriter> ddos_dataset_writer_;  // [DDOS-DATASET-D287]\n",
     "after"),
    ("ml-detector/src/zmq_handler.cpp",
     "            correlation_writer_ = nullptr;\n        }\n    }\n",
     "\n    // [DDOS-DATASET-D287] dataset DDoS v2 de laboratorio; no depende de la clave HMAC\n"
     "    if (config_.ddos_dataset_writer.enabled) {\n"
     "        try {\n"
     "            ddos_dataset_writer_ = std::make_unique<ml_defender::DdosDatasetWriter>(config_.ddos_dataset_writer.base_dir);\n"
     '            logger_->info("✅ DdosDatasetWriter initialized ({})", ddos_dataset_writer_->path());\n'
     "        } catch (const std::exception& e) {\n"
     '            logger_->error("❌ Failed to initialize DdosDatasetWriter: {}", e.what());\n'
     "            ddos_dataset_writer_.reset();\n"
     "        }\n"
     "    }\n",
     "after"),
    ("ml-detector/src/zmq_handler.cpp",
     "        if (logger_->should_log(spdlog::level::debug)) {  // [DDOS-V2-D286]",
     "        if (ddos_dataset_writer_) {  // [DDOS-DATASET-D287] cada evento una vez, sin depender de VERBOSE\n"
     "            ddos_dataset_writer_->write(event, hs_ddos_c, hs_ddos_p);\n"
     "        }\n",
     "before"),
    ("ml-detector/config/ml_detector_config.json",
     '    "base_dir": "/vagrant/logs/correlation",\n    "rotation_seconds": 30\n  },\n',
     '  "ddos_dataset_writer": {\n'
     '    "_comment": "[DDOS-DATASET-D287] Dataset DDoS v2 de laboratorio (CSV plano, un fichero por arranque). Integridad: sha256 en el manifiesto del entrenamiento.",\n'
     '    "enabled": false,\n'
     '    "base_dir": "/vagrant/logs/lab/ddos_dataset"\n'
     "  },\n",
     "after"),
]


def proto_include():
    for rel in ("ml-detector/include/correlation_writer.hpp", "ml-detector/include/zmq_handler.hpp"):
        p = ROOT / rel
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            s = line.strip()
            if s.startswith("#include") and "network_security.pb.h" in s:
                return s
    return None


def die(msg):
    print(f"[ABORT] {msg}")
    sys.exit(2)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(1)
    apply = sys.argv[1] == "--apply"

    inc = proto_include()
    if inc is None:
        die("no encuentro el #include de network_security.pb.h en correlation_writer.hpp ni en zmq_handler.hpp")
    hdr_text = HDR_TEMPLATE.replace("@@PROTO_INCLUDE@@", inc)
    hdr_path = ROOT / HDR_REL
    hdr_state = "falta"
    if hdr_path.exists():
        if hdr_path.read_text() == hdr_text:
            hdr_state = "aplicado"
        else:
            die(f"{HDR_REL} existe y difiere del esperado")

    texts = {}
    for rel, _, _, _ in EDITS:
        if rel not in texts:
            p = ROOT / rel
            if not p.exists():
                die(f"no existe {rel}")
            texts[rel] = p.read_text()

    states = []
    for rel, anchor, ins, _ in EDITS:
        states.append("aplicado" if ins in texts[rel] else "falta")
    all_states = states + [hdr_state]

    if all(s == "aplicado" for s in all_states):
        print("[OK] YA APLICADO: los 7 sitios + header presentes. Nada que hacer.")
        return
    if any(s == "aplicado" for s in all_states):
        die(f"estado PARCIAL (header={hdr_state}, sitios={states}); revisar a mano con git diff")

    new = dict(texts)
    for rel, anchor, ins, where in EDITS:
        c = new[rel].count(anchor)
        if c != 1:
            die(f"ancla en {rel} aparece {c} veces (esperado 1): {anchor[:70]!r}")
        repl = anchor + ins if where == "after" else ins + anchor
        new[rel] = new[rel].replace(anchor, repl, 1)
        print(f"[PLAN] {rel}: insercion {where} de ancla ({len(ins.splitlines())} lineas)")
    print(f"[PLAN] {HDR_REL}: nuevo ({len(hdr_text.splitlines())} lineas), include = {inc}")

    jrel = "ml-detector/config/ml_detector_config.json"
    try:
        cfg = json.loads(new[jrel])
    except json.JSONDecodeError as e:
        die(f"el JSON resultante no es valido: {e}")
    if cfg.get("ddos_dataset_writer", {}).get("enabled") is not False:
        die("ddos_dataset_writer.enabled no queda en false")
    print("[OK] JSON resultante valido; ddos_dataset_writer.enabled=false")

    if not apply:
        print("[CHECK] sin cambios en disco. Lanza --apply.")
        return

    tmp = hdr_path.with_suffix(".hpp.tmp")
    tmp.write_text(hdr_text)
    tmp.replace(hdr_path)
    for rel, text in new.items():
        if text == texts[rel]:
            continue
        p = ROOT / rel
        t = p.with_name(p.name + ".tmp")
        t.write_text(text)
        t.replace(p)
        print(f"[APPLY] {rel}")
    print(f"[APPLY] {HDR_REL}")
    print("[OK] aplicado. Siguiente: make pipeline-build PROFILE=production (en el Mac).")


if __name__ == "__main__":
    main()
