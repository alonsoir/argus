#!/usr/bin/env python3
# d317_docs_resultados_p7.py — resultados del paso 7 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317).
# Añade al final de docs/ml-heads/day312_diseno.md la sección «Resultados DAY317 — paso 7» y al final de
# docs/BACKLOG.md su resumen (reinicio_vm_2 PASA; pasos 0-7 hechos).
# Uso:  python3 d317_docs_resultados_p7.py --check <raiz_repo>
#       python3 d317_docs_resultados_p7.py --apply <raiz_repo>
# Todo o nada; idempotente (si las dos secciones ya están, no toca nada).
import hashlib, os, sys

DISENO_RUTA = 'docs/ml-heads/day312_diseno.md'
DISENO_PREVIO = 'a6768c9fa8827718ec3c33d896ec65dd6cdc431b3afe9a4b0a4fa3a33f1dec40'
DISENO_MARCA = '## Resultados DAY317 — paso 7'
BACKLOG_RUTA = 'docs/BACKLOG.md'
BACKLOG_PREVIO = '47d712be35b98eeeba34c99cc59b9aa27b57454188c59ff7d62892b91b1c29de'
BACKLOG_MARCA = '## DAY317 — paso 7 de DEBT-ETCD-HA-TLS-RAFT-001 hecho'
DISENO = '\n## Resultados DAY317 — paso 7 (sección aparte, sin reescribir el diseño)\n\nInstrumento `scripts/etcd_ha/d317_reinicio_vm.sh` + `d317_reinicio_defender.sh` (parcheadores `d317_p7_instrumento.py` y\n`d317_p7_fix_saneado.py`); el de DAY311 borrado. La predicción del paso 7 del diseño de DAY312 («misma huella, bronce\nanterior verificable, registro conservado, latidos 200») **PASA**.\n\n### Banco\n\n- Veredicto con una corrida falsa buena: PASA; 16 condiciones rotas, una a una: FALLA cada una (la línea de la regla\n  `POST /register` del arranque no cuenta como registro). Clasificación de segmentos con un conversor falso: AB, A, B,\n  MEZCLA, NINGUNA y VACIO donde tocan.\n\n### Laboratorio\n\n- **`reinicio_vm_1` — PARADA en la verificación** (fallo del instrumento): `vagrant ssh` antepone una línea vacía y `T1`\n  llegó como `\\n<epoch>`, partiendo la orden del ayudante (`line 59: 4: t1`, `1793779685: orden no encontrada`). Antes\n  de parar ya midió huellas iguales antes y después (`60768287`, `4f60123a`); el trap paró el tráfico, dejó el\n  etcd-server activo y borró las claves. No se completó a mano (sería verificar con una clave «B» pedida fuera de su\n  momento): se arregló (cada valor capturado saneado; el `wc` de macOS sin relleno) y se repitió. Los logs quedan en\n  `logs/lab/day317/reinicio_vm_1/`.\n- **`reinicio_vm_2` — VEREDICTO PASA** (CAIDO_S 150, TRAS_S 150, intervalos de latido 30 s):\n  - huellas iguales antes y después: bronce `60768287`, CSV del firewall `4f60123a`;\n  - ml-detector `[BRONCE-CLAVE-SIN-CONFIRMAR]` 3, `-CONFIRMADA` 1, `-CAMBIADA` 0, `[BRONCE-SIN-CLAVE]` 0; firewall\n    `[FW-CSV-CLAVE-SIN-CONFIRMAR]` 3, `-CONFIRMADA` 1, `-CAMBIADA` 0, `[FW-CSV-SIN-CLAVE]` 0;\n  - `[ETCD-CLIENTE-SIN-SERVICIO]` ml-detector 6, firewall 6, sniffer 5; `[ETCD-CLIENTE-REANUDADO]` 1 en cada uno;\n    `-REGISTRADO` 0 y `-REGISTRO-PERDIDO` 0 en los tres;\n  - etcd-server tras arrancar: 0 componentes registrados de nuevo, 0 `POST /register`, 0 latidos con status distinto de\n    200; latidos 200: sniffer 8, ml-detector 7, firewall 7 (mínimo 4);\n  - bronce: 16 segmentos (5276 filas) en el intervalo, los 16 en AB: también los escritos con el servidor caído,\n    firmados en modo extendido, verifican con la clave de antes y con la de después;\n  - continuidad: el firewall resumió 5248 eventos.\n\n### Lecciones DAY317 (paso 7)\n\n- Todo valor capturado por `vagrant ssh` se sanea antes de usarlo como argumento (la línea vacía inicial).\n- Una corrida que para por el instrumento no se completa a mano: se arregla y se repite con otro nombre.\n\n### Pendiente\n\n- Decisión 2 de Alonso: con este PASA, decidir si el instrumento entra en `lab-e2e` (EMECAS).\n- Paso 8: EMECAS+++ production desde cero (la VM etcd se rehace: Vault limpio, DEBT-LAB-VAULT-CLAVES-PRUEBA-001).\n'
BACKLOG = '\n## DAY317 — paso 7 de DEBT-ETCD-HA-TLS-RAFT-001 hecho\n\nDocumento: `docs/ml-heads/day312_diseno.md`, «Resultados DAY317 — paso 7». `reinicio_vm_2`: VEREDICTO PASA (misma huella\nde bronce y CSV tras reiniciar el etcd-server de la VM con el pipeline vivo, ningún registro nuevo, latidos 200, los 16\nsegmentos del intervalo verificables con la clave de antes y la de después). `reinicio_vm_1` paró por un fallo del\ninstrumento (valor de `vagrant ssh` sin sanear), arreglado. DEBT-ETCD-HA-TLS-RAFT-001: pasos 0-7 hechos; queda el 8\n(EMECAS+++ production).\n'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    F = [(DISENO_RUTA, DISENO_PREVIO, DISENO_MARCA, DISENO), (BACKLOG_RUTA, BACKLOG_PREVIO, BACKLOG_MARCA, BACKLOG)]
    cont, ya = {}, 0
    for ruta, previo, marca, _ in F:
        f = os.path.join(raiz, ruta)
        if not os.path.isfile(f):
            print('FALLA: no existe %s; no se toca nada.' % f); return 1
        b = open(f, 'rb').read(); cont[ruta] = b
        if marca.encode() in b:
            ya += 1
        elif sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
    if ya == 2:
        print('YA APLICADO: las dos secciones ya están; no se toca nada.'); return 0
    if ya:
        print('FALLA: una sección está y la otra no; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: 2 ficheros; se añaden %d y %d líneas.' % (DISENO.count('\n'), BACKLOG.count('\n'))); return 0
    for ruta, _, _, texto in F:
        f = os.path.join(raiz, ruta); t = f + '.d317tmp'
        with open(t, 'wb') as o: o.write(cont[ruta] + texto.encode('utf-8'))
        os.chmod(t, os.stat(f).st_mode & 0o7777); os.replace(t, f); print('  escrito  %s' % ruta)
    print('APLICADO: 2 ficheros.'); return 0

if __name__ == '__main__':
    sys.exit(main())
