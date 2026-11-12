#!/usr/bin/env python3
# d323_mitre_ventana.py — DEBT-ETCD-HA-TLS-RAFT-001, PR1 (DAY323) [MITRE-VENTANA-D323]: mitre-check con una sola ventana
# [T0, T1] (reloj del defender) para los tres sensores, Zeek a prueba de rotación y ningún paso en silencio.
# Antes de este parcheador se escriben a mano (cat) y se verifican: scripts/mitre_ventana.py, scripts/mitre_zeek_cosecha.sh,
# scripts/test_mitre_ventana.sh (nuevos) y scripts/mitre_start.sh (entero). Este parcheador comprueba sus sha256 y cambia
# scripts/mitre_veredicto.sh (exige filas del ataque por sensor) y el Makefile (target test-mitre-ventana; mitre-check lo
# pasa primero). Requiere d323_reloj_lab.py aplicado (commit 6387cfd75).
# Uso:  python3 d323_mitre_ventana.py --check <raiz_repo>
#       python3 d323_mitre_ventana.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si CADA fichero está en el estado previo exacto y el resultado da su sha256 final.
import hashlib, os, sys

REQUISITOS = {'scripts/mitre_ventana.py': '2b3c50d3d4ff7aff6fa38198b928a736f70486d2c3f7791107dee69bf572c1b3', 'scripts/mitre_zeek_cosecha.sh': '3eeab2d47509449f64452d4c5bcf863a810a0903838ce87412e8a8fe2f1590ca', 'scripts/test_mitre_ventana.sh': 'a17bb7a9b4a2b3bf186942999a68d1b44fc1dbeed54388939bd1722a02c043fd', 'scripts/mitre_start.sh': '1da081d4c35802975d61d69a4fe1377ec107fe905caee67f53ec5bce62140d99'}   # {ruta: sha256} que deben estar ya en su sitio
FICHEROS = {'scripts/mitre_veredicto.sh': ('4d4bdeeba294c9e096c7833b0620410cc428c08cd0ba4ace92e3d79cfc45a411', '7f19fc3681460afa42f30aa83043ca791e9e7528ef33ccb70aa32969b638154f', [('# La salida completa queda en logs/lab/mitre-veredicto-<fecha>.txt.\n', '# La salida completa queda en logs/lab/mitre-veredicto-<fecha>.txt.\n# [MITRE-VENTANA-D323] además, cada sensor debe tener filas del ataque (atacante <-> víctima) en la ventana [T0, T1]\n# de la corrida: líneas «[MITRE-VENTANA] sensor=S ... ataque=K» de mitre_start.sh. Medido DAY323: con «eventos > 0»\n# pasaban Suricata con alertas de otro día y Zeek con solo etcd y NTP.\n', 1), ('  s == "sens" && /^[a-z_-]+\\|[0-9]+$/  { split($0, a, "|"); n[a[1]] = a[2] + 0; next }\n', '  /^\\[MITRE-VENTANA\\] sensor=/         { sn = ""; ak = -1\n                                         for (i = 2; i <= NF; i++) { split($i, kv, "=")\n                                           if (kv[1] == "sensor") sn = kv[2]; else if (kv[1] == "ataque") ak = kv[2] + 0 }\n                                         if (sn != "") { at[sn] = ak; va[sn] = 1 }; next }\n  s == "sens" && /^[a-z_-]+\\|[0-9]+$/  { split($0, a, "|"); n[a[1]] = a[2] + 0; next }\n', 1), ('    for (i = 1; i <= 3; i++) { v = n[ss[i]] + 0; c = (v > 0); printf "  %s  %s: eventos en el grafo > 0 (%d)\\n", (c ? "OK   " : "FALLA"), ss[i], v; ok = ok && c }\n', '    for (i = 1; i <= 3; i++) { v = n[ss[i]] + 0; c = (v > 0); printf "  %s  %s: eventos en el grafo > 0 (%d)\\n", (c ? "OK   " : "FALLA"), ss[i], v; ok = ok && c }\n    for (i = 1; i <= 3; i++) { c = (va[ss[i]] && at[ss[i]] > 0); printf "  %s  %s: filas del ataque en la ventana > 0 (%s)\\n", (c ? "OK   " : "FALLA"), ss[i], (va[ss[i]] ? at[ss[i]] : "sin dato"); ok = ok && c }\n', 1)]), 'Makefile': ('9bd4a553df24e837d904185c4fccbf3e08bad32dd15b805db171e372d45f996b', '5c9460d5f4a51554512a9a7a96e3cd1cb0b66c68d408bf718afdfd9ba434991d', [('# [EMECAS-TODO-D317] Acto IV (río abajo, ADR-058)', '# [MITRE-VENTANA-D323] tests de scripts/mitre_ventana.py y scripts/mitre_zeek_cosecha.sh con datos fabricados a partir\n# de lo medido DAY323 (rotación de Zeek de las 10:00, eve.json de dos corridas, archivado de zeekctl en segundo plano,\n# .gz cortado). Se lanza en la VM zeek (GNU date); no toca Zeek. mitre-check lo pasa antes de la corrida.\n.PHONY: test-mitre-ventana\ntest-mitre-ventana:\n\t@vagrant ssh zeek -c "bash /vagrant/scripts/test_mitre_ventana.sh"\n\n# [EMECAS-TODO-D317] Acto IV (río abajo, ADR-058)', 1), ('mitre-check:\n\t@# [LAB-NTP-SENSORES-D323] un solo reloj:', 'mitre-check:\n\t@echo "[MITRE-CHECK] $$(date \'+%T\') tests de la ventana y de la cosecha de Zeek (log: /tmp/argus_mitre_check_tests.txt)"\n\t@$(MAKE) --no-print-directory test-mitre-ventana > /tmp/argus_mitre_check_tests.txt 2>&1 || { tail -n 20 /tmp/argus_mitre_check_tests.txt; echo "[MITRE-VEREDICTO] FALLA: test-mitre-ventana"; exit 1; }\n\t@# [LAB-NTP-SENSORES-D323] un solo reloj:', 1)])}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    for ruta, esperado in REQUISITOS.items():
        if not os.path.isfile(p(ruta)) or sha(open(p(ruta), 'rb').read()) != esperado:
            print('FALLA: %s falta o no tiene el sha256 esperado (%s...); no se toca nada.' % (ruta, esperado[:16])); return 1
        if modo == '--apply' and ruta.endswith(('.py', '.sh')) and not os.access(p(ruta), os.X_OK) and ruta != 'scripts/mitre_start.sh':
            os.chmod(p(ruta), 0o755); print('  chmod 755 %s' % ruta)
    nuevos, ya = {}, []
    for ruta, (previo, final, cambios) in FICHEROS.items():
        if not os.path.isfile(p(ruta)):
            print('FALLA: no existe %s; no se toca nada.' % ruta); return 1
        b = open(p(ruta), 'rb').read()
        if sha(b) == final:
            ya.append(ruta); continue
        if sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
        t = b.decode('utf-8')
        for i, (v, n, k) in enumerate(cambios, 1):
            if t.count(v) != k:
                print('FALLA: %s, cambio %d: %d apariciones (se exigen %d); no se toca nada.' % (ruta, i, t.count(v), k)); return 1
            t = t.replace(v, n)
        if sha(t.encode('utf-8')) != final:
            print('FALLA: %s: el resultado no da el sha256 final; no se toca nada.' % ruta); return 1
        nuevos[ruta] = t.encode('utf-8')
    if not nuevos:
        print('YA APLICADO: no se toca nada.'); return 0
    if ya:
        print('FALLA: aplicado a medias (ya: %s); no se toca nada.' % ', '.join(ya)); return 1
    if modo == '--check':
        print('APLICABLE: %s.' % ', '.join('%s (%d cambios)' % (r, len(FICHEROS[r][2])) for r in nuevos)); return 0
    for ruta, nuevo in nuevos.items():
        tmp = p(ruta) + '.d323tmp'
        with open(tmp, 'wb') as o: o.write(nuevo)
        os.chmod(tmp, os.stat(p(ruta)).st_mode & 0o7777); os.replace(tmp, p(ruta))
        print('  escrito  %s (sha256 %s)' % (ruta, FICHEROS[ruta][1][:16]))
    print('APLICADO.'); return 0

if __name__ == '__main__':
    sys.exit(main())
