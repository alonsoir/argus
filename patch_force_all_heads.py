#!/usr/bin/env python3
"""
patch_force_all_heads.py  --  DAY271

Cablea el flag debug `force_all_heads` en el ml-detector para MEDIR la grieta B:
correr la cabeza DDoS (level2) con la compuerta de level1 abierta a la fuerza,
sin veto, y observar que dice DDoSDetector::predict sobre los flujos de 1 paquete
del flood CICDDoS2019.

Hace tres cosas, en 3 ficheros:
  1) FLAG        : --force-all-heads (CLI) -> ZMQHandler::set_force_all_heads() -> miembro.
  2) COMPUERTA   : la condicion de la linea 549 pasa a un PREDICADO PURO testeable
                   ZMQHandler::l2_gate_open(force, label, conf, thr). Misma logica,
                   ahora con test unitario (no altera el camino no-forzado).
  3) OBSERVABILIDAD: anade `disp={:.3f}` (source_ip_dispersion, idx 2) al log de
                   features del level2. Es lo que desambigua el confound del pcap
                   de origen unico. Piezas 3 = hunks independientes: si quieres el
                   commit del flag puro, esas dos lineas se stagean aparte.

Modos:
  --check   valida el estado de cada edicion (APPLIED / PENDING / BROKEN) y sale. No escribe.
  --dry     (por defecto) imprime el diff de lo que haria. No escribe.
  --apply   aplica en sitio.

Garantias (estilo Via Appia):
  * IDEMPOTENTE : re-ejecutar no duplica; detecta lo ya aplicado por marcador.
  * ATOMICO     : si UN ancla no casa exactamente una vez, ABORTA sin tocar nada.
  * NO commitea. El compilador y los tests son el arbitro final.

Se ejecuta desde la RAIZ del repo. Rutas relativas a ml-detector/.
"""

import argparse
import difflib
import sys

HPP = "ml-detector/include/zmq_handler.hpp"
CPP = "ml-detector/src/zmq_handler.cpp"
MAIN = "ml-detector/src/main.cpp"

# ---------------------------------------------------------------------------
# Cada edicion: (fichero, nombre, find, replace, marker)
#   - find   : substring UNICO en el fichero (sin espacios de sangria a la
#              izquierda; se casa por contenido, robusto a la indentacion).
#   - marker : substring presente SOLO tras aplicar (para idempotencia).
# El chequeo mira SIEMPRE el marker antes que el find (algunas ediciones
# conservan el find dentro del replace).
# ---------------------------------------------------------------------------

EDITS = []

# --- ZMQHandler.hpp : predicado puro + setter (junto a set_plugin_loader) ---
FIND_A = "void set_plugin_loader(ml_defender::PluginLoader* pl) { plugin_loader_ = pl; }"
INS_A = (
    "\n    // DEBUG DAY271 -- fuerza las cabezas L2 sin veto de level1 (medicion grieta B)"
    "\n    void set_force_all_heads(bool v) { force_all_heads_ = v; }"
)
EDITS.append((HPP, "hpp: predicado l2_gate_open + setter", FIND_A, FIND_A + INS_A,
              "set_force_all_heads(bool v)"))

# --- ZMQHandler.hpp : miembro privado (junto a plugin_loader_) ---
FIND_B = "ml_defender::PluginLoader* plugin_loader_ = nullptr;"
INS_B = (
    "\n    // DEBUG DAY271 -- default false: un pipeline-start normal NUNCA abre la compuerta"
    "\n    bool force_all_heads_ = false;"
)
EDITS.append((HPP, "hpp: miembro force_all_heads_", FIND_B, FIND_B + INS_B,
              "bool force_all_heads_ = false;"))

# --- ZMQHandler.cpp : la compuerta (linea ~549) usa el predicado ---
FIND_C = "if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack) {"
REPL_C = "if (l2_gate_open(force_all_heads_, label_l1, confidence_l1, config_.ml.thresholds.level1_attack)) {"
EDITS.append((CPP, "cpp: compuerta 549 -> l2_gate_open", FIND_C, REPL_C,
              "l2_gate_open(force_all_heads_"))

# --- ZMQHandler.cpp : disp en el format string del log de features ---
FIND_D = 'amp={:.3f}",'
REPL_D = 'amp={:.3f}, disp={:.3f}",'
EDITS.append((CPP, "cpp: log features +disp (fmt)", FIND_D, REPL_D, 'disp={:.3f}",'))

# --- ZMQHandler.cpp : disp en los argumentos del log ---
FIND_E = "ddos_features_vec[0], ddos_features_vec[4], ddos_features_vec[5]);"
REPL_E = "ddos_features_vec[0], ddos_features_vec[4], ddos_features_vec[5], ddos_features_vec[2]);"
EDITS.append((CPP, "cpp: log features +disp (args)", FIND_E, REPL_E,
              "ddos_features_vec[5], ddos_features_vec[2]);"))

# --- ZMQHandler.cpp : ddos_prob en el log del veredicto (linea ~596) ---
# Necesario para B: `probability` es P(clase ganadora); en un NORMAL NO es P(ddos).
# `ddos_prob` = P(ddos) siempre -> es lo que dirime "cabeza ciega" vs "cabeza cerca del umbral".
FIND_J = 'DDoS: class={} ({}), conf={:.4f}",'
REPL_J = 'DDoS: class={} ({}), conf={:.4f}, ddos_prob={:.4f}",'
EDITS.append((CPP, "cpp: log veredicto +ddos_prob (fmt)", FIND_J, REPL_J, 'ddos_prob={:.4f}",'))

FIND_K = "ddos_result.probability);"
REPL_K = "ddos_result.probability, ddos_result.ddos_prob);"
EDITS.append((CPP, "cpp: log veredicto +ddos_prob (args)", FIND_K, REPL_K,
              "ddos_result.probability, ddos_result.ddos_prob);"))

# --- main.cpp : usage (calco de --verbose) ---
FIND_F = r'std::cout << "  --verbose          Enable verbose logging (DEBUG level)\n";'
NEW_F = r'std::cout << "  --force-all-heads  [DEBUG] run all L2 heads regardless of level1\n";'
EDITS.append((MAIN, "main: usage --force-all-heads", FIND_F, FIND_F + "\n    " + NEW_F,
              "run all L2 heads regardless of level1"))

# --- main.cpp : bool local (calco de verbose) ---
FIND_G = "bool verbose = false;"
EDITS.append((MAIN, "main: bool force_all_heads", FIND_G,
              FIND_G + "\n    bool force_all_heads = false;",
              "bool force_all_heads = false;"))

# --- main.cpp : rama de parseo (se antepone a la de --verbose) ---
# Anclar en el CIERRE del bloque --verbose y APENDER la rama nueva detras.
# Asi la insercion queda acotada por lineas distintas (no hay `}` adyacente identico
# que confunda al differ) y el diff se lee limpio.
FIND_H = '            verbose = true;\n        }'
REPL_H = (FIND_H
          + '\n        else if (arg == "--force-all-heads") {'
          + '\n            force_all_heads = true;'
          + '\n        }')
EDITS.append((MAIN, "main: parseo --force-all-heads", FIND_H, REPL_H,
              'arg == "--force-all-heads"'))

# --- main.cpp : llamada al setter DESPUES de construir (espejo del plugin_loader) ---
FIND_I = ");\n\n        zmq_handler.start();"
REPL_I = (");\n\n        zmq_handler.set_force_all_heads(force_all_heads);   // DEBUG DAY271"
          "\n        zmq_handler.start();")
EDITS.append((MAIN, "main: set_force_all_heads() tras construir", FIND_I, REPL_I,
              "set_force_all_heads(force_all_heads)"))


def classify(content, find, marker):
    """Devuelve 'applied' | 'pending' | 'broken'."""
    if marker in content:
        return "applied"
    if content.count(find) == 1:
        return "pending"
    return "broken"


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Patch force_all_heads (DAY271).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="valida estado y sale, no escribe")
    g.add_argument("--apply", action="store_true", help="aplica en sitio")
    g.add_argument("--dry", action="store_true", help="muestra diff (por defecto)")
    args = ap.parse_args()
    mode = "check" if args.check else "apply" if args.apply else "dry"

    # Cargar ficheros una sola vez.
    files = {}
    for path in {e[0] for e in EDITS}:
        c = load(path)
        if c is None:
            print(f"ABORT: no encuentro {path}. Ejecuta desde la raiz del repo.", file=sys.stderr)
            return 2
        files[path] = c

    # 1) Clasificar TODO antes de tocar nada (atomicidad).
    plan = []          # (path, name, find, replace, status)
    broken = False
    print("Estado de las ediciones:")
    for path, name, find, replace, marker in EDITS:
        status = classify(files[path], find, marker)
        plan.append((path, name, find, replace, status))
        tag = {"applied": "APPLIED", "pending": "pending", "broken": "BROKEN"}[status]
        print(f"  [{tag:>7}] {name}")
        if status == "broken":
            broken = True

    if broken:
        print("\nABORT: al menos un ancla no casa exactamente una vez (BROKEN). "
              "No se ha tocado nada.\nPega el fichero afectado o su tramo y ajusto el ancla.",
              file=sys.stderr)
        return 2

    if mode == "check":
        pend = sum(1 for *_, s in plan if s == "pending")
        app = sum(1 for *_, s in plan if s == "applied")
        print(f"\nOK. {app} aplicadas, {pend} pendientes, 0 rotas.")
        return 0

    # 2) Aplicar en memoria (solo las pendientes).
    new_files = dict(files)
    changed = set()
    for path, name, find, replace, status in plan:
        if status != "pending":
            continue
        c = new_files[path]
        assert c.count(find) == 1, f"conteo inesperado en {name}"  # ya validado
        new_files[path] = c.replace(find, replace, 1)
        changed.add(path)

    if not changed:
        print("\nNada que hacer: todo ya aplicado (idempotente).")
        return 0

    # 3) Diff (dry) o escritura (apply).
    for path in sorted(changed):
        diff = difflib.unified_diff(
            files[path].splitlines(keepends=True),
            new_files[path].splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}",
        )
        sys.stdout.writelines(diff)

    if mode == "dry":
        print(f"\n[DRY] {len(changed)} fichero(s) cambiarian. Nada escrito. "
              f"Repite con --apply para aplicar.")
        return 0

    for path in sorted(changed):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_files[path])
    print(f"\n[APPLY] escritos {len(changed)} fichero(s). NO commiteado. "
          f"Compila y corre los tests: el compilador es el arbitro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())