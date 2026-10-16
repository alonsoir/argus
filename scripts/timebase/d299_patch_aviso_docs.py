#!/usr/bin/env python3
"""DAY299: aviso del sniffer con el agregador apagado + documentacion del punto 1 (guia, _doc, MANIFEST,
BACKLOG). Uso: --check | --apply (desde la raiz del repo). Atomico: todo o nada."""
import os
import sys

M = "[DDOS-AGG-AVISO-D299]"
MAIN = "sniffer/src/userspace/main.cpp"
JSONF = "sniffer/config/sniffer.json"
GUIA = "docs/operaciones/GUIA_OPERACIONES.md"
MANIF = "scripts/dataset_lab/MANIFEST.md"
BACK = "docs/BACKLOG.md"

EDITS = []   # (fichero, ancla, nuevo)
APPENDS = []  # (fichero, texto al final)

EDITS.append((MAIN,
    "                static_cast<uint64_t>(static_cast<double>(pe.arranque_ventanas) * pe.interval_ms * 1.0e6));\n"
    "        }\n",
    "                static_cast<uint64_t>(static_cast<double>(pe.arranque_ventanas) * pe.interval_ms * 1.0e6));\n"
    "        } else {  // " + M + " el admin lo ve en el arranque, no por ausencia de lineas\n"
    "            std::cerr << \"[DDOS-ARRANQUE] AVISO agregador del kernel desactivado \"\n"
    "                         \"(kernel_space.ddos_kernel_agg_enabled=false): la cabeza DDoS no recibira el estado \"\n"
    "                         \"de las victimas y el ml-detector avisara [DDOS-V2-ANOMALIA]. Guia: \"\n"
    "                         \"docs/operaciones/GUIA_OPERACIONES.md seccion DDOS-V2-ANOMALIA\" << std::endl;\n"
    "        }\n"))

EDITS.append((JSONF,
    "La linea [DDOS-ARRANQUE] primera foto de cada arranque mide el valor real para calibrarlo en cada instalacion.",
    "La linea [DDOS-ARRANQUE] primera foto de cada arranque mide el valor real para calibrarlo en cada instalacion; "
    "su N cuenta eventos del sniffer sin foto, fast alerts incluidas (a 300 pps unos 2 por paquete: 648 medidos DAY299). "
    "Con el agregador apagado (ddos_kernel_agg_enabled=false) no hay plazo y el sniffer escribe [DDOS-ARRANQUE] AVISO " + M + "."))

EDITS.append((GUIA,
    "   - Síntoma: no hay ninguna línea `[DDOS-ARRANQUE]`.\n",
    "   - Síntoma: `sniffer.log` dice `[DDOS-ARRANQUE] AVISO agregador del kernel desactivado`.\n"))

APPENDS.append((GUIA, """
---

## DDOS-ARRANQUE

Líneas de `sniffer.log` sobre el arranque de la cabeza DDoS.

- `[DDOS-ARRANQUE] primera foto del agregador a X ms del arranque (Y ventanas ...); eventos sellados FRIO sin foto: N`.
  Informativa, una por arranque. X es lo que tarda el agregador del kernel en dar su primera tasa (en el
  laboratorio, ~1,0 s). Durante ese tiempo la cabeza DDoS no puede ver un ataque: es la ceguera física de
  arranque, que ninguna configuración elimina. N cuenta los eventos del sniffer de ese intervalo, fast alerts
  incluidas (a 300 pps, unos 2 por paquete). Si X se acerca a `ddos_victim_arranque_ventanas` ×
  `ddos_kernel_agg_interval_ms`, subir `ddos_victim_arranque_ventanas`.
- `[DDOS-ARRANQUE] AVISO agregador del kernel desactivado ...`. La configuración apaga el agregador: ver
  DDOS-V2-ANOMALIA, punto 1.
- `[DDOS-ARRANQUE] ERROR sin foto del agregador tras el plazo de arranque ...`. Ver DDOS-V2-ANOMALIA, punto 4.
"""))

APPENDS.append((MANIF, """
## Techo de los pcaps disjuntos de un solo origen (DAY299) """ + M + """

`gen_disjunto.py` solo varía el puerto de destino dentro de cada clase {origen, puerto de origen, destino}:
unas 64 000 tuplas por clase. Con `ntp_reflex_10k_lab.pcap` caben 6 vueltas (63 000 paquetes, ~210 s a
300 pps); con 180 000 aborta en la vuelta 6 ("sin puertos libres"). Para que una corrida fría solape con el
arranque del sniffer se usa `RETRASO_S` en `lab_frio.sh`, no un pcap más largo.
"""))

APPENDS.append((BACK, """
## 🆕 Entradas DAY299 """ + M + """

### DEBT-DDOS-ESTADO-ARRANQUE-001 — ✅ RESUELTA DAY299 (código b05f880c, medida e586aa31)
- Causa medida: sin foto del agregador (have_snapshot=false; la baseline no se publica) el evento salía sin
  victim_state, y además el consumidor del anillo arranca ANTES que el lector (main.cpp). El diagnóstico de
  DAY298 (window_ms==0) era incorrecto.
- Arreglo: plazo de arranque ddos_victim_arranque_ventanas (sniffer.json, [2,60], defecto 5). Sin foto dentro
  del plazo = FRIO; fuera del plazo o sin lector = sin estado + [DDOS-ARRANQUE] ERROR (sniffer) +
  [DDOS-V2-ANOMALIA] estado_victima_ausente (ml-detector, antes [DDOS-V2] sin_estado). Agregador apagado =
  [DDOS-ARRANQUE] AVISO. Línea [DDOS-ARRANQUE] primera foto por arranque.
- Medido: frío con ataque de 300 pps presente en el arranque: estado_victima_ausente 298 -> 0; primera foto a
  1015-1035 ms; 648 eventos FRIO (fast alerts incluidas); pases = marcados = 51655; DROP solo .50.
  Agregador apagado: 12 avisos, ~3000 por 10 s durante el ataque (~17900 de 18000 paquetes), 0 DROP.
- Nace docs/operaciones/GUIA_OPERACIONES.md: cada aviso al administrador tiene su sección.

### DEBT-DDOS-SNAPSHOT-STALE-001 — ABIERTA
Si el lector muere DESPUÉS de publicar, la foto se queda vieja y se sigue sellando su estado. snapshot_age_ms
viaja en el evento, pero nadie lo vigila. Propuesta: edad máxima en ventanas en el JSON, aviso y estado
desconocido al superarla.

### DEBT-HEADS-VENTANA-BASE-ARRANQUE-001 — ABIERTA (decisión de Alonso DAY299)
Todas las cabezas comparten la unidad de tiempo: una ventana base del pipeline en el JSON, y cada cabeza
expresa sus ventanas y su plazo de arranque como múltiplos. Hoy DDoS = 1 s (lector del kernel) y el
agregador de ransomware = 30 s. El plazo de arranque se generaliza a cada cabeza al certificarla, configurable
y medido.

### DEBT-LAB-FRIO-SOLAPE-001 — ABIERTA (herramienta del laboratorio)
El sniffer arranca entre ~140 y >215 s tras el inicio de pipeline-start (pipeline-start entero: 226-262 s).
Un pcap disjunto de un solo origen tiene un techo de ~64k tuplas (~210 s a 300 pps), así que una corrida fría
sin RETRASO_S puede no solapar (frio_atq300_d299: 0 paquetes del ataque vistos). Mitigado con RETRASO_S en
lab_frio.sh. De fondo: caducidad de flujos (DEBT-SNIFFER-FLOW-EXPIRY-001) o pcaps multiorigen; medir por qué
varía pipeline-start.

### DEBT-CONFIG-KERNEL-STRUCT-DUP-001 — ABIERTA
ddos_kernel_agg_interval_ms está en dos structs (sniffer/include/config_manager.hpp:96 y config_types.h:157).
Medir cuál se usa y unificar.

### Nota DAY299 a DEBT-TIMEBASE-SEQ-DELIVERY-ORDER-001
seq_desorden 6232 / 106867 = 5,8 % a 300 pps (frio_atq300_d299b), en línea con el 5,1 % de DAY298.
"""))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    files = {p for p, _, _ in EDITS} | {p for p, _ in APPENDS}
    t = {}
    for p in files:
        if not os.path.isfile(p):
            print(f"[FALLA] no existe {p}")
            return 1
        t[p] = open(p, encoding="utf-8").read()
    hechos = [new in t[p] for p, _, new in EDITS] + [M in t[p] and txt.strip()[:40] in t[p] for p, txt in APPENDS]
    if all(hechos):
        print("[YA-APLICADO]")
        return 0
    if any(hechos):
        print("[ABORTA] mezcla de aplicado y pendiente:", hechos)
        return 1
    for i, (p, old, _) in enumerate(EDITS):
        n = t[p].count(old)
        if n != 1:
            print(f"[ABORTA] edicion {i} en {p}: ancla {n} veces: {old.splitlines()[0][:90]}")
            return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] {len(EDITS)} ediciones y {len(APPENDS)} anexos pendientes en {len(files)} ficheros")
        return 0
    for p, old, new in EDITS:
        t[p] = t[p].replace(old, new, 1)
    for p, txt in APPENDS:
        t[p] = t[p].rstrip("\n") + "\n" + txt
    for p in files:
        tmp = p + ".d299tmp"
        open(tmp, "w", encoding="utf-8").write(t[p])
        os.replace(tmp, p)
    print(f"[APLICADO] {len(EDITS)} ediciones y {len(APPENDS)} anexos en {len(files)} ficheros {M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
