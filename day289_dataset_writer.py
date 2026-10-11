#!/usr/bin/env python3
# DAY289 — enciende/apaga ddos_dataset_writer.enabled en ml_detector_config.json (edición acotada).
import re, sys, json
from pathlib import Path
F = Path("/vagrant/ml-detector/config/ml_detector_config.json")
MODO = sys.argv[1] if len(sys.argv) > 1 else "estado"
t = F.read_text()
i = t.find('"ddos_dataset_writer"')
if i < 0 or t.count('"ddos_dataset_writer"') != 1:
    sys.exit("PARAR: bloque ddos_dataset_writer ausente o duplicado")
fin = t.find('}', i)
m = re.search(r'"enabled"\s*:\s*(true|false)', t[i:fin])
if not m:
    sys.exit("PARAR: no hay 'enabled' dentro del bloque")
actual = m.group(1)
if MODO == "estado":
    print("ddos_dataset_writer.enabled =", actual); sys.exit(0)
quiero = {"on": "true", "off": "false"}.get(MODO) or sys.exit("uso: on | off | estado")
if actual == quiero:
    print("sin cambios: ya estaba", actual); sys.exit(0)
a, b = i + m.start(1), i + m.end(1)
t2 = t[:a] + quiero + t[b:]
json.loads(t2)  # el JSON sigue siendo válido
F.write_text(t2)
print(f"ddos_dataset_writer.enabled: {actual} -> {quiero}")
