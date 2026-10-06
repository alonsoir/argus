#!/usr/bin/env python3
"""DAY289 [WINSTATS-CACHE-D289] — una sola pasada por la ventana de 30 s por evento en el sniffer.
Los 9 extractores de ventana de MLDefenderExtractor llamaban cada uno a get_window_stats (O(eventos en
ventana), 4 inserts por evento en unordered_set locales). Ahora comparten un WindowStats calculado una vez
dentro de populate_ml_defender_features. Fuera de populate, sin caché (igual que antes).
Única diferencia semántica: los 9 comparten un mismo 'now' en vez de 9 separados por microsegundos.
Uso: --check | --apply. Atómico e idempotente. No compila ni commitea."""
import os, sys
from pathlib import Path

MARCA = "[WINSTATS-CACHE-D289]"
HPP = Path("/vagrant/sniffer/include/ml_defender_features.hpp")
CPP = Path("/vagrant/sniffer/src/userspace/ml_defender_features.cpp")
MODO = sys.argv[1] if len(sys.argv) > 1 else "--check"
if MODO not in ("--check", "--apply"):
    sys.exit("uso: --check | --apply")

h, c = HPP.read_text(), CPP.read_text()
en_h, en_c = MARCA in h, MARCA in c
if en_h and en_c:
    print("YA APLICADO"); sys.exit(0)
if en_h or en_c:
    sys.exit(f"PARAR: marca solo en {'hpp' if en_h else 'cpp'}; estado inconsistente, no se toca nada")

def unico(texto, ancla, n=1, donde=""):
    k = texto.count(ancla)
    if k != n:
        sys.exit(f"PARAR: ancla en {donde} aparece {k} veces (se esperaban {n}):\n{ancla}")

# --- hpp: miembros privados
A_H = "\nprivate:\n"
unico(h, A_H, 1, "hpp")
N_H = A_H + (
    "    // " + MARCA + " Una sola pasada por la ventana de 30 s por evento: los 9 extractores\n"
    "    // de ventana comparten el WindowStats calculado al entrar en populate_ml_defender_features.\n"
    "    // Fuera de populate (llamadas sueltas a los extract_* públicos) no hay caché: se calcula como antes.\n"
    "    WindowStats window_stats_30s() const;\n"
    "    mutable WindowStats window_cache_{};\n"
    "    mutable bool window_cache_active_ = false;\n"
    "    mutable bool window_cache_valid_ = false;\n\n")
h2 = h.replace(A_H, N_H)

# --- cpp: 9 bloques de ventana -> ayudante
A_BLOQUE = ("    auto now = TimeWindowAggregator::get_current_time_ns();\n"
            "    auto start = now - 30'000'000'000ULL;\n"
            "    auto stats = aggregator_->get_window_stats(start, now);\n")
unico(c, A_BLOQUE, 9, "cpp (bloques de ventana)")
c2 = c.replace(A_BLOQUE, "    auto stats = window_stats_30s();  // " + MARCA + "\n")

# --- cpp: ayudante + guardián antes de populate, y guardián al entrar en populate
A_POP = ("void MLDefenderExtractor::populate_ml_defender_features(\n"
         "        const FlowStatistics& flow,\n"
         "        ::protobuf::NetworkSecurityEvent& proto_event) const {\n")
unico(c2, A_POP, 1, "cpp (populate)")
AYUDANTE = (
    "// " + MARCA + " WindowStats de los últimos 30 s, una vez por evento dentro de populate.\n"
    "WindowStats MLDefenderExtractor::window_stats_30s() const {\n"
    "    if (window_cache_active_ && window_cache_valid_) return window_cache_;\n"
    "    const auto now = TimeWindowAggregator::get_current_time_ns();\n"
    "    WindowStats ws = aggregator_->get_window_stats(now - 30'000'000'000ULL, now);\n"
    "    if (window_cache_active_) {\n"
    "        window_cache_ = ws;\n"
    "        window_cache_valid_ = true;\n"
    "    }\n"
    "    return ws;\n"
    "}\n\n"
    "namespace {\n"
    "// " + MARCA + " Activa la caché durante un populate y la apaga al salir (también ante excepción).\n"
    "struct WindowCacheScope {\n"
    "    bool& active;\n"
    "    bool& valid;\n"
    "    WindowCacheScope(bool& a, bool& v) : active(a), valid(v) { active = true; valid = false; }\n"
    "    ~WindowCacheScope() { active = false; valid = false; }\n"
    "    WindowCacheScope(const WindowCacheScope&) = delete;\n"
    "    WindowCacheScope& operator=(const WindowCacheScope&) = delete;\n"
    "};\n"
    "}  // namespace\n\n")
c3 = c2.replace(A_POP, AYUDANTE + A_POP +
                "    WindowCacheScope cache_scope(window_cache_active_, window_cache_valid_);  // " + MARCA + "\n")

if MODO == "--check":
    print("CHECK OK: hpp 1 inserción; cpp 9 bloques sustituidos + ayudante + guardián en populate")
    sys.exit(0)

for ruta, texto in ((HPP, h2), (CPP, c3)):
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(texto)
for ruta in (HPP, CPP):
    os.replace(ruta.with_suffix(ruta.suffix + ".tmp"), ruta)
print("APLICADO")
