#!/usr/bin/env python3
# d317_p8c_emecas.py — paso 8 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): emecas levanta todas las VMs (Zeek y Wazuh incluidas) y emecas+++ gana
# su Acto IV (adapters desde cero + mitre-check con scripts/mitre_veredicto.sh, que se crea). Requiere 8b.
# Uso:  python3 d317_p8c_emecas.py --check <raiz_repo>
#       python3 d317_p8c_emecas.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Makefile'
SHA_PREVIO = '61c6ff18f3a2bba31f817d00c98645a72eccd4bad5637932e6f8ef58ca2bf4d3'
SHA_FINAL = '472f73246823b16bb19808221916f793dcaba3ec878778549652bc29313371f0'
CAMBIOS = [('\tvagrant up defender client suricata etcd\n', '\t@# [EMECAS-TODO-D317] destroy -f borra todas las VMs: se levantan todas (Zeek y Wazuh incluidas; Acto IV de emecas+++)\n\tvagrant up defender client suricata zeek wazuh etcd\n', 1), ('emecas+++: emecas++\n\t@echo ""\n\t@echo "╔════════════════════════════════════════════════════════════╗"\n\t@echo "║  ✅ EMECAS+++ PASSED — circuito bronce->Kuzu verificado    ║"\n\t@echo "║  (test_bronze_to_kuzu_circuit, dentro de test-all)          ║"\n\t@echo "║  Eslabon 1+ (Landing Zone) anadira Actos propios aqui       ║"\n\t@echo "╚════════════════════════════════════════════════════════════╝"\n', '# [EMECAS-TODO-D317] Acto IV (río abajo, ADR-058): los tres adapters recompilados desde cero y probados (no se usan\n# binarios de VMs que ya no existen), pipeline arrancado y MITRE -> grafo con veredicto (scripts/mitre_veredicto.sh).\n.PHONY: mitre-check\nmitre-check:\n\t@$(MAKE) --no-print-directory pipeline-start > /tmp/argus_mitre_check_start.txt 2>&1 || { tail -n 20 /tmp/argus_mitre_check_start.txt; echo "[MITRE-VEREDICTO] FALLA: pipeline-start"; exit 1; }\n\t@if grep -E \'^[[:space:]]*❌.*STOPPED\' /tmp/argus_mitre_check_start.txt; then echo "[MITRE-VEREDICTO] FALLA: componente STOPPED"; exit 1; fi\n\t@bash scripts/mitre_veredicto.sh\n\nemecas+++: emecas++\n\t@echo ""\n\t@echo "══ Acto IV — río abajo: adapters desde cero y MITRE -> grafo con veredicto ══"\n\t$(MAKE) suricata-adapter-test\n\t$(MAKE) zeek-adapter-test\n\t$(MAKE) wazuh-adapter-test\n\t$(MAKE) mitre-check\n\t@echo ""\n\t@echo "╔════════════════════════════════════════════════════════════╗"\n\t@echo "║  ✅ EMECAS+++ PASSED — Acto IV: aRGus, Suricata y Zeek     ║"\n\t@echo "║  hasta el grafo, invariante 0, flujos corroborados > 0     ║"\n\t@echo "╚════════════════════════════════════════════════════════════╝"\n', 1)]
NUEVOS = {'scripts/mitre_veredicto.sh': '#!/usr/bin/env bash\n# mitre_veredicto.sh — DAY317 [MITRE-VEREDICTO-D317]: corre scripts/mitre_start.sh (nmap del client por aRGus, Suricata y\n# Zeek hasta el grafo) y da un veredicto PASA/FALLA para EMECAS+++ (Acto IV): mitre_start.sh rc 0; los tres sensores con\n# eventos en el grafo; invariante (CORRELATES_FLOW entre community_id distintos) = 0; flujos corroborados cross-sensor > 0.\n# Uso (Mac, raíz del repo):  bash scripts/mitre_veredicto.sh            (corre mitre_start.sh y evalúa su salida)\n#                            bash scripts/mitre_veredicto.sh --solo F    (evalúa una salida ya guardada)\n# La salida completa queda en logs/lab/mitre-veredicto-<fecha>.txt.\nset -u\nexport LC_ALL=C\nTAG=MITRE-VEREDICTO\nif [ "${1:-}" = "--solo" ]; then\n  F=${2:?fichero con la salida de mitre_start.sh}; RC=0\n  [ -f "$F" ] || { echo "[$TAG] FALLA: no existe $F"; exit 1; }\nelse\n  [ -f Vagrantfile ] && [ -d .git ] || { echo "[$TAG] FALLA: no estoy en la raíz del repo"; exit 1; }\n  mkdir -p logs/lab; F=logs/lab/mitre-veredicto-$(date -u +%Y%m%dT%H%M%SZ).txt\n  bash scripts/mitre_start.sh > "$F" 2>&1; RC=$?\n  echo "[$TAG] salida de mitre_start.sh en $F (rc=$RC)"\nfi\n# Formato de kuzu_query (medido DAY317): «sensor|n» por fila; los recuentos sueltos, un número solo en su línea.\ntr -d \'\\r\' < "$F" | awk -v rc="$RC" -v tag="$TAG" \'\n  /^-- sensores en el grafo --/        { s = "sens"; next }\n  /^-- invariante/                     { s = "inv";  next }\n  /^-- flujos corroborados/            { s = "corr"; next }\n  /^\\([0-9]+ filas\\)/                  { s = ""; next }\n  s == "sens" && /^[a-z_-]+\\|[0-9]+$/  { split($0, a, "|"); n[a[1]] = a[2] + 0; next }\n  s == "inv"  && /^[0-9]+$/            { inv = $0 + 0; vi = 1; next }\n  s == "corr" && /^[0-9]+$/            { corr = $0 + 0; vc = 1; next }\n  END {\n    ok = 1\n    c = (rc == 0); printf "  %s  mitre_start.sh rc=%d\\n", (c ? "OK   " : "FALLA"), rc; ok = ok && c\n    split("argus suricata zeek", ss, " ")\n    for (i = 1; i <= 3; i++) { v = n[ss[i]] + 0; c = (v > 0); printf "  %s  %s: eventos en el grafo > 0 (%d)\\n", (c ? "OK   " : "FALLA"), ss[i], v; ok = ok && c }\n    c = (vi && inv == 0); printf "  %s  invariante = 0 (%s)\\n", (c ? "OK   " : "FALLA"), (vi ? inv : "sin dato"); ok = ok && c\n    c = (vc && corr > 0); printf "  %s  flujos corroborados cross-sensor > 0 (%s)\\n", (c ? "OK   " : "FALLA"), (vc ? corr : "sin dato"); ok = ok && c\n    printf "[%s] VEREDICTO %s\\n", tag, (ok ? "PASA" : "FALLA")\n    exit (ok ? 0 : 1)\n  }\'\n'}   # {ruta: contenido} que se crean (0755)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    if not os.path.isfile(p(RUTA)):
        print('FALLA: no existe %s; no se toca nada.' % RUTA); return 1
    b = open(p(RUTA), 'rb').read()
    nuevos_ya = all(os.path.isfile(p(r)) and open(p(r), 'rb').read() == c.encode() for r, c in NUEVOS.items())
    if sha(b) == SHA_FINAL and nuevos_ya:
        print('YA APLICADO: no se toca nada.'); return 0
    if sha(b) != SHA_PREVIO:
        print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (RUTA, sha(b)[:16])); return 1
    for r in NUEVOS:
        if os.path.exists(p(r)):
            print('FALLA: %s ya existe; no se toca nada.' % r); return 1
    t = b.decode('utf-8')
    for i, (v, n, k) in enumerate(CAMBIOS, 1):
        if t.count(v) != k:
            print('FALLA: cambio %d: %d apariciones (se exigen %d); no se toca nada.' % (i, t.count(v), k)); return 1
        t = t.replace(v, n)
    nuevo = t.encode('utf-8')
    if sha(nuevo) != SHA_FINAL:
        print('FALLA: el resultado no da el sha256 final; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: %s (%d cambios)%s.' % (RUTA, len(CAMBIOS), ''.join(' + %s nuevo' % r for r in NUEVOS))); return 0
    for r, c in NUEVOS.items():
        tmp = p(r) + '.d317tmp'
        with open(tmp, 'wb') as o: o.write(c.encode('utf-8'))
        os.chmod(tmp, 0o755); os.replace(tmp, p(r)); print('  creado   %s' % r)
    tmp = p(RUTA) + '.d317tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(p(RUTA)).st_mode & 0o7777); os.replace(tmp, p(RUTA))
    print('APLICADO: %s (sha256 %s)%s.' % (RUTA, SHA_FINAL[:16], ''.join(' + %s' % r for r in NUEVOS))); return 0

if __name__ == '__main__':
    sys.exit(main())
