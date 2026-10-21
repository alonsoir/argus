#!/usr/bin/env python3
"""DAY299 -- DEBT-DDOS-ESTADO-ARRANQUE-001 (decision b de Alonso, DAY298).

Sin foto del agregador del kernel el evento salia sin victim_state. Ahora:
  - plazo de arranque (ddos_victim_arranque_ventanas, sniffer.json) marcado en el tablero ANTES de
    arrancar el consumidor del anillo si el agregador esta activo; borrado si el lector no arranca;
  - sin foto y dentro del plazo: se sella FRIO; fuera del plazo o sin plazo: no se sella (UNKNOWN)
    y el sniffer escribe una vez [DDOS-ARRANQUE] ERROR;
  - el lector mide el arranque: [DDOS-ARRANQUE] primera foto a X ms (Y ventanas), N sellados FRIO;
  - el ml-detector renombra el aviso a [DDOS-V2-ANOMALIA] estado_victima_ausente con la guia.
Uso: python3 scripts/timebase/d299_patch_estado_arranque.py --check | --apply   (desde la raiz)
"""
import os
import sys

M = "[DDOS-ESTADO-ARRANQUE-D299]"

CONTRATO = "sniffer/include/ddos_contract_v2.hpp"
CFG = "sniffer/src/userspace/config_manager.cpp"
JSONF = "sniffer/config/sniffer.json"
BOARD = "sniffer/include/ddos_victim_board.hpp"
READER = "sniffer/include/ddos_kernel_reader.hpp"
RCH = "sniffer/include/ring_consumer.hpp"
RCC = "sniffer/src/userspace/ring_consumer.cpp"
MAIN = "sniffer/src/userspace/main.cpp"
ZMQ = "ml-detector/src/zmq_handler.cpp"
TEST = "sniffer/tests/test_ddos_victim_board.cpp"
GUIA = "docs/operaciones/GUIA_OPERACIONES.md"

EDITS = []


def ins_after(path, anchor, text):
    EDITS.append((path, anchor, anchor + text))


def ins_before(path, anchor, text):
    EDITS.append((path, anchor, text + anchor))


def repl(path, old, new):
    EDITS.append((path, old, new))


# --- contrato: campo, rango y validacion ---
ins_after(CONTRATO,
          "    double interval_ms = 1000.0;    // ventana nominal del lector (ddos_kernel_agg_interval_ms)\n",
          "    uint64_t arranque_ventanas = 5; // " + M + " plazo sin foto del agregador aceptado como arranque\n")
ins_after(CONTRATO,
          "inline constexpr double kVictimEwmaEvictMin = 60.0, kVictimEwmaEvictMax = 86400.0;\n",
          "inline constexpr double kVictimArranqueVentanasMin = 2.0, kVictimArranqueVentanasMax = 60.0;  // " + M + "\n")
ins_before(CONTRATO,
           "           p.interval_ms > 0.0 && p.k_out < p.k_in;\n",
           "           victim_ewma_in_range(static_cast<double>(p.arranque_ventanas), kVictimArranqueVentanasMin,\n"
           "                                kVictimArranqueVentanasMax) &&  // " + M + "\n")

# --- config: parseo y linea [DDOS-HYST] ---
ins_after(CFG,
          "    p.evict_windows = static_cast<uint64_t>(x);\n",
          '    n += ddos_ewma_num(k, "ddos_victim_arranque_ventanas", static_cast<double>(d.arranque_ventanas),\n'
          "                       dd::kVictimArranqueVentanasMin, dd::kVictimArranqueVentanasMax, true, x);\n"
          "    p.arranque_ventanas = static_cast<uint64_t>(x);  // " + M + "\n")
repl(CFG,
     '              << " interval_ms=" << p.interval_ms << std::endl;\n',
     '              << " interval_ms=" << p.interval_ms << " arranque_ventanas=" << p.arranque_ventanas\n'
     "              << std::endl;  // " + M + "\n")

# --- sniffer.json ---
ins_after(JSONF,
          '    "ddos_victim_ewma_evict_windows": 3600,\n',
          '    "_doc_ddos_victim_arranque_ventanas": "entero, rango [2, 60], defecto 5. ' + M + ' Plazo de arranque de la '
          'cabeza DDoS, en ventanas del lector (ddos_kernel_agg_interval_ms; con 1000 ms el defecto son 5 s). El agregador '
          'necesita una ventana de baseline y otra para dar la primera tasa: hasta la primera foto la cabeza DDoS no puede ver '
          'un ataque (ceguera fisica de unas 2 ventanas, que este campo no crea ni alarga). Mientras no hay foto y dura el plazo, '
          'las victimas se sellan FRIO; en cuanto llega la primera foto el sellado es el real. Si el plazo vence sin foto, los '
          'eventos salen sin victim_state, el sniffer escribe [DDOS-ARRANQUE] ERROR y el ml-detector avisa '
          '[DDOS-V2-ANOMALIA] estado_victima_ausente (docs/operaciones/GUIA_OPERACIONES.md). La linea [DDOS-ARRANQUE] '
          'primera foto de cada arranque mide el valor real para calibrarlo en cada instalacion. Si falta o esta fuera de '
          'rango: defecto con [CONFIG-DEFAULT].",\n'
          '    "ddos_victim_arranque_ventanas": 5,\n')

# --- tablero ---
repl(BOARD,
     "#include <mutex>\n#include <unordered_map>\n",
     "#include <mutex>\n#include <optional>  // " + M + "\n#include <unordered_map>\n")
ins_after(BOARD,
          "    uint64_t age_ms = 0;  // edad del snapshot al consultar\n",
          "    bool en_arranque = false;       // " + M + " sin foto y dentro del plazo de arranque\n"
          "    bool arranque_vencido = false;  // " + M + " sin foto, plazo marcado y ya vencido\n")
ins_before(BOARD,
           "class DdosVictimBoard {\n",
           "// " + M + " Estado que se sella en el evento. Con foto: el del tablero (victima ausente = NORMAL).\n"
           "// Sin foto y dentro del plazo de arranque: FRIO (la victima aun no tiene historia). Sin foto fuera\n"
           "// del plazo, o sin plazo marcado (agregador apagado o lector sin arrancar): nada; el evento llega con\n"
           "// victim_state UNKNOWN y el ml-detector avisa [DDOS-V2-ANOMALIA] estado_victima_ausente.\n"
           "inline std::optional<::argus::ddos::VictimEwmaEstado> sello_estado_victima(const DdosVictimLookup& r) noexcept {\n"
           "    if (r.have_snapshot) return r.estado;\n"
           "    if (r.en_arranque) return ::argus::ddos::VictimEwmaEstado::Frio;\n"
           "    return std::nullopt;\n"
           "}\n\n")
repl(BOARD,
     "        if (!s) return r;\n        r.have_snapshot = true;\n",
     "        if (!s) {  // " + M + "\n"
     "            const uint64_t ini = arranque_ns_.load(std::memory_order_acquire);\n"
     "            if (ini != 0) {\n"
     "                const uint64_t plazo = arranque_plazo_ns_.load(std::memory_order_relaxed);\n"
     "                if (now_ns < ini || now_ns - ini < plazo) {\n"
     "                    r.en_arranque = true;\n"
     "                    frio_arranque_.fetch_add(1, std::memory_order_relaxed);\n"
     "                } else {\n"
     "                    r.arranque_vencido = true;\n"
     "                }\n"
     "            }\n"
     "            return r;\n"
     "        }\n"
     "        r.have_snapshot = true;\n")
ins_after(BOARD,
          "    uint64_t published() const { return published_.load(std::memory_order_relaxed); }\n",
          "\n"
          "    // " + M + " Plazo de arranque: main lo marca ANTES de arrancar el consumidor del anillo si el\n"
          "    // agregador esta activo, y lo borra si el lector no llega a arrancar.\n"
          "    void marcar_arranque(uint64_t inicio_ns, uint64_t plazo_ns) {\n"
          "        arranque_plazo_ns_.store(plazo_ns, std::memory_order_relaxed);\n"
          "        arranque_ns_.store(inicio_ns == 0 ? 1 : inicio_ns, std::memory_order_release);\n"
          "    }\n"
          "    void borrar_arranque() { arranque_ns_.store(0, std::memory_order_release); }\n"
          "    uint64_t arranque_ns() const { return arranque_ns_.load(std::memory_order_acquire); }\n"
          "    uint64_t frio_arranque() const { return frio_arranque_.load(std::memory_order_relaxed); }\n")
ins_after(BOARD,
          "    std::atomic<uint64_t> published_{0};\n",
          "    std::atomic<uint64_t> arranque_ns_{0};            // " + M + " 0 = sin plazo marcado\n"
          "    std::atomic<uint64_t> arranque_plazo_ns_{0};      // " + M + "\n"
          "    mutable std::atomic<uint64_t> frio_arranque_{0};  // " + M + " eventos sellados FRIO sin foto\n")

# --- lector: medida del arranque ---
repl(READER,
     "            if (board_ && w->t_start_ns != 0) board_->publish_window(win, *w);\n",
     "            if (board_ && w->t_start_ns != 0) {\n"
     "                board_->publish_window(win, *w);\n"
     "                if (board_->published() == 1) {  // " + M + " medida del plazo de arranque\n"
     "                    const uint64_t ini = board_->arranque_ns();\n"
     "                    const uint64_t ahora = ddos_steady_now_ns();\n"
     "                    const double ms = (ini != 0 && ahora >= ini) ? static_cast<double>(ahora - ini) / 1.0e6 : -1.0;\n"
     "                    std::cout << \"[DDOS-ARRANQUE] primera foto del agregador a \" << ms\n"
     "                              << \" ms del arranque (\" << (interval_ms_ > 0 ? ms / interval_ms_ : 0.0)\n"
     "                              << \" ventanas de \" << interval_ms_ << \" ms); eventos sellados FRIO sin foto: \"\n"
     "                              << board_->frio_arranque() << std::endl;\n"
     "                }\n"
     "            }\n")

# --- sellado ---
ins_after(RCH,
          "    std::shared_ptr<::sniffer::DdosVictimBoard> victim_board_;  // [DDOS-VWIN-D279:RC-MEMBER]\n",
          "    mutable std::atomic<bool> aviso_arranque_vencido_{false};  // " + M + " el ERROR se escribe una vez\n")
repl(RCC,
     "    if (!r.have_snapshot) return;\n    auto* vw = ev.mutable_victim_window();\n",
     "    if (!r.have_snapshot) {  // " + M + "\n"
     "        const auto sello = ::sniffer::sello_estado_victima(r);\n"
     "        if (sello) {\n"
     "            ev.mutable_network_features()->mutable_ddos_embedded()->set_victim_state(\n"
     "                static_cast<protobuf::VictimState>(*sello));\n"
     "        } else if (r.arranque_vencido && !aviso_arranque_vencido_.exchange(true)) {\n"
     "            std::cerr << \"[DDOS-ARRANQUE] ERROR sin foto del agregador tras el plazo de arranque \"\n"
     "                         \"(ddos_victim_arranque_ventanas): la cabeza DDoS no ve el estado de las victimas. \"\n"
     "                         \"Guia: docs/operaciones/GUIA_OPERACIONES.md seccion DDOS-V2-ANOMALIA\" << std::endl;\n"
     "        }\n"
     "        return;\n"
     "    }\n"
     "    auto* vw = ev.mutable_victim_window();\n")

# --- main: marcar y borrar el plazo ---
ins_before(MAIN,
           "        if (!ring_consumer.start()) {\n",
           "        // " + M + " plazo de arranque de la cabeza DDoS: se marca ANTES de arrancar el consumidor del\n"
           "        // anillo (los primeros eventos se sellan antes de que exista el lector) y se borra mas abajo si el\n"
           "        // lector no llega a arrancar. Agregador apagado = sin plazo = anomalia visible en el ml-detector.\n"
           "        if (g_config.kernel_space.ddos_kernel_agg_enabled) {\n"
           "            const auto& pe = g_config.kernel_space.ddos_victim_ewma;\n"
           "            g_ddos_victim_board->marcar_arranque(\n"
           "                sniffer::ddos_steady_now_ns(),\n"
           "                static_cast<uint64_t>(static_cast<double>(pe.arranque_ventanas) * pe.interval_ms * 1.0e6));\n"
           "        }\n")
ins_after(MAIN,
          "                    ddos_reader_ptr = nullptr;\n                }\n            }\n        }\n",
          "        if (!ddos_reader_ptr) g_ddos_victim_board->borrar_arranque();  // " + M + " sin lector no hay foto: anomalia, no FRIO\n")

# --- ml-detector: aviso ---
repl(ZMQ,
     '                    logger_->warn("[DDOS-V2] sin_estado={} en los últimos {} s: eventos sin victim_state (sniffer "\n'
     '                                  "antiguo o sin snapshot del lector); se aplica la etapa 1 antigua (ratio >= k_ratio)",\n'
     "                                  d_v2s, secs);\n",
     '                    logger_->warn("[DDOS-V2-ANOMALIA] estado_victima_ausente={} en los últimos {} s: eventos sin "\n'
     '                                  "victim_state (campo 16); la cabeza DDoS no puede marcar ataques en ellos. Causas: "\n'
     '                                  "agregador del kernel apagado o sin foto, o sniffer sin el campo 16. Qué hacer: "\n'
     '                                  "docs/operaciones/GUIA_OPERACIONES.md §DDOS-V2-ANOMALIA",\n'
     "                                  d_v2s, secs);  // " + M + "\n")

# --- test 14 ---
ins_after(TEST,
          "int main() {\n",
          "    {   // 14. " + M + " sellado sin foto del agregador (plazo de arranque)\n"
          "        using ::sniffer::sello_estado_victima;\n"
          "        using E = ::argus::ddos::VictimEwmaEstado;\n"
          "        const uint64_t T0 = 1000000000ULL, PLAZO = 5000000000ULL;\n"
          "        ::sniffer::DdosVictimBoard b;\n"
          "        // 14a sin plazo marcado (agregador apagado o lector sin arrancar): no se sella\n"
          "        auto r = b.lookup(0x0A000001u, 17u, T0);\n"
          "        CHECK(!r.have_snapshot && !r.en_arranque && !r.arranque_vencido);\n"
          "        CHECK(!sello_estado_victima(r).has_value());\n"
          "        // 14b sin foto dentro del plazo: FRIO\n"
          "        b.marcar_arranque(T0, PLAZO);\n"
          "        r = b.lookup(0x0A000001u, 17u, T0 + PLAZO - 1);\n"
          "        CHECK(r.en_arranque && !r.arranque_vencido);\n"
          "        CHECK(sello_estado_victima(r) == std::optional<E>(E::Frio));\n"
          "        CHECK(b.frio_arranque() == 1);\n"
          "        // 14c plazo vencido sin foto: no se sella, vencido\n"
          "        r = b.lookup(0x0A000001u, 17u, T0 + PLAZO);\n"
          "        CHECK(!r.en_arranque && r.arranque_vencido);\n"
          "        CHECK(!sello_estado_victima(r).has_value());\n"
          "        // 14d plazo borrado (el lector no arranco): no se sella\n"
          "        b.borrar_arranque();\n"
          "        r = b.lookup(0x0A000001u, 17u, T0 + 1);\n"
          "        CHECK(!r.en_arranque && !r.arranque_vencido && !sello_estado_victima(r).has_value());\n"
          "        // 14e llega la foto dentro del plazo: manda la foto (victima ausente = NORMAL, contrato DAY298)\n"
          "        b.marcar_arranque(T0, PLAZO);\n"
          "        auto s = std::make_shared<::sniffer::DdosVictimSnapshot>();\n"
          "        s->seq = 1;\n"
          "        s->window_ms = 1000;\n"
          "        s->published_ns = T0;\n"
          "        b.publish(s);\n"
          "        r = b.lookup(0x0A000001u, 17u, T0 + 1000);\n"
          "        CHECK(r.have_snapshot && !r.en_arranque && !r.arranque_vencido);\n"
          "        CHECK(sello_estado_victima(r) == std::optional<E>(E::Normal));\n"
          "        CHECK(b.frio_arranque() == 1);\n"
          "        // 14f con foto, el estado del tablero pasa tal cual\n"
          "        ::sniffer::DdosVictimLookup f;\n"
          "        f.have_snapshot = true;\n"
          "        f.window_ms = 1000;\n"
          "        f.estado = E::BajoPresion;\n"
          "        CHECK(sello_estado_victima(f) == std::optional<E>(E::BajoPresion));\n"
          "        std::printf(\"ESTADO-ARRANQUE: 14a-14f frio_arranque=%llu\\n\",\n"
          "                    static_cast<unsigned long long>(b.frio_arranque()));\n"
          "    }\n")

# --- guia: texto exacto del ERROR ---
repl(GUIA,
     "   - Síntoma: `[DDOS-ARRANQUE] ERROR sin foto del agregador tras N ventanas`.\n",
     "   - Síntoma: `[DDOS-ARRANQUE] ERROR sin foto del agregador tras el plazo de arranque`.\n")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d299_patch_estado_arranque.py --check | --apply")
        return 2
    textos = {}
    for p, _, _ in EDITS:
        if p not in textos:
            if not os.path.isfile(p):
                print(f"[FALLA] no existe {p} (lanzar desde la raiz del repo)")
                return 1
            with open(p, encoding="utf-8") as fh:
                textos[p] = fh.read()
    estados, fallo = [], False
    for i, (p, old, new) in enumerate(EDITS):
        t = textos[p]
        if new in t:
            estados.append("aplicada")
            continue
        n = t.count(old)
        if n != 1:
            print(f"[FALLA] edicion {i} en {p}: el ancla aparece {n} veces")
            print("        ancla: " + old.splitlines()[0][:110])
            fallo = True
        estados.append("pendiente")
    if fallo:
        print("[ABORTA] no se toca ningun fichero")
        return 1
    if all(e == "aplicada" for e in estados):
        print(f"[YA-APLICADO] {len(EDITS)} ediciones ya presentes {M}")
        return 0
    if any(e == "aplicada" for e in estados):
        print("[ABORTA] mezcla de ediciones aplicadas y pendientes: revisar a mano")
        for i, e in enumerate(estados):
            print(f"  {i:2d} {e:9s} {EDITS[i][0]}")
        return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] {len(EDITS)} ediciones pendientes en {len(textos)} ficheros, anclas unicas")
        return 0
    for p, old, new in EDITS:
        textos[p] = textos[p].replace(old, new, 1)
    for p, _, new in EDITS:
        if textos[p].count(new) != 1:
            print(f"[ABORTA] tras aplicar, {p} no contiene la edicion exactamente una vez")
            return 1
    for p, t in textos.items():
        tmp = p + ".d299tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(t)
        os.replace(tmp, p)
    print(f"[APLICADO] {len(EDITS)} ediciones en {len(textos)} ficheros {M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
