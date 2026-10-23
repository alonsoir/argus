#!/usr/bin/env python3
# DAY305 — [HEADS-SWITCH-D305] ml_detector_config.json: valores de LABORATORIO de los interruptores de cabeza
# (decision DAY300: mientras se trabaja DDoS, todo lo que no sea ddos_v2 apagado). ddos_v2 no se toca (sigue ON).
# Cada bloque de cabeza recibe un "_doc" con formato, defecto y efecto. Valida TODO antes de escribir NADA:
# cada ancla exactamente 1 vez, marca ausente, y el JSON resultante parsea y tiene los valores esperados.
# Uso, raiz del repo:  python3 d305_mld_json.py --check | --apply
import json, sys

MARK = "[HEADS-SWITCH-D305]"
JS = "ml-detector/config/ml_detector_config.json"
COMUN = ("enabled: true|false; si falta o no es booleano se usa true con [CONFIG-DEFAULT] y el ml-detector arranca "
         "igual. El estado EFECTIVO sale en el log con [HEADS] al arrancar y en cada informe de estadisticas. "
         "Valor de LABORATORIO (DAY300: mientras se trabaja DDoS, todo lo que no sea ddos_v2 apagado).")
DOCS = {
    "level1": ("    ", "level1 (ONNX, 23 rasgos). Apagada: ni rasgos ni inferencia level1, no se publica su prediccion "
               "ni su veredicto, ml_score=0. Ademas ddos_v1/ransomware/traffic/internal dejan de evaluarse (corren "
               "solo tras level1=ATTACK, salvo FORCE_ALL_HEADS). "),
    "ddos": ("      ", "DDoS v1 (9 rasgos, detras de level1). Sustituida por ml.ddos_v2; se retira en su propia rama "
             "(DEBT-DDOS-V1-RETIRE-001). "),
    "ransomware": ("      ", "ransomware (detras de level1). Sin certificar. "),
    "web": ("      ", "traffic, Internet vs interno (detras de level1; nombre historico 'web'). Sin certificar. "),
    "internal": ("      ", "internal, movimiento lateral y exfiltracion (detras de traffic). Sin certificar. "),
}

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_mld_json.py --check | --apply")
    t = open(JS, encoding="utf-8").read()
    if MARK in t:
        die(f"{JS} ya contiene {MARK}")
    json.loads(t)  # el de partida debe ser JSON valido
    n = t
    for blk, (ind, txt) in DOCS.items():
        old = f'"{blk}": {{\n{ind}  "enabled": true,\n'
        c = n.count(old)
        if c != 1:
            die(f'bloque "{blk}": el ancla aparece {c} veces (se esperaba 1)')
        doc = json.dumps(f"{MARK} {txt}{COMUN}", ensure_ascii=False)
        n = n.replace(old, f'"{blk}": {{\n{ind}  "_doc": {doc},\n{ind}  "enabled": false,\n', 1)
    try:
        j = json.loads(n)
    except json.JSONDecodeError as e:
        die(f"el JSON resultante no parsea: {e}")
    ml = j["ml"]
    got = {
        "ml.level1.enabled": ml["level1"]["enabled"],
        "ml.level2.ddos.enabled": ml["level2"]["ddos"]["enabled"],
        "ml.level2.ransomware.enabled": ml["level2"]["ransomware"]["enabled"],
        "ml.level3.web.enabled": ml["level3"]["web"]["enabled"],
        "ml.level3.internal.enabled": ml["level3"]["internal"]["enabled"],
        "ml.ddos_v2.enabled": ml["ddos_v2"]["enabled"],
    }
    want = {k: False for k in got}
    want["ml.ddos_v2.enabled"] = True
    if got != want:
        die(f"valores resultantes inesperados: {got}")
    if n.count(MARK) != 5:
        die(f"{n.count(MARK)} marcas (se esperaban 5)")
    print("OK: 5 bloques de cabeza -> enabled=false con _doc; ml.ddos_v2.enabled sigue true; JSON valido")
    for k, v in got.items():
        print(f"   {k} = {str(v).lower()}")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    with open(JS, "w", encoding="utf-8") as fh:
        fh.write(n)
    print("--apply: escrito")

if __name__ == "__main__":
    main()
