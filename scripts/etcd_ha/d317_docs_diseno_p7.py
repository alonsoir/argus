#!/usr/bin/env python3
# d317_docs_diseno_p7.py — diseño del paso 7 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317), escrito antes del código.
# Añade al final de docs/ml-heads/day312_diseno.md la sección «Diseño del paso 7» y al final de docs/BACKLOG.md su
# resumen (instrumento de reinicio de la VM con veredicto, que sustituye al de DAY311).
# Uso:  python3 d317_docs_diseno_p7.py --check <raiz_repo>
#       python3 d317_docs_diseno_p7.py --apply <raiz_repo>
# Todo o nada; idempotente (si las dos secciones ya están, no toca nada).
import hashlib, os, sys

DISENO_RUTA = 'docs/ml-heads/day312_diseno.md'
DISENO_PREVIO = '1473dcfedc896107cd37ee884e9aaf12359f039ac31858dbd50e56d5a0b0ab1e'
DISENO_MARCA = '## Diseño del paso 7 (reinicio del etcd-server de la VM'
BACKLOG_RUTA = 'docs/BACKLOG.md'
BACKLOG_PREVIO = 'f2ca31c10a0f28b37c0e391cdf12dabc7330d792acfff55d59ce0d521bdd2503'
BACKLOG_MARCA = '## DAY317 — diseño del paso 7 de DEBT-ETCD-HA-TLS-RAFT-001'
DISENO = '\n## Diseño del paso 7 (reinicio del etcd-server de la VM con el pipeline vivo) — DAY317, escrito ANTES de tocar código\n\nObjetivo (predicción del paso 7 del diseño de DAY312): tras reiniciar el etcd-server, misma huella de clave, bronce\nanterior verificable, registro conservado y latidos 200. B1 y B2 midieron ya la huella y el registro conservado; falta\nel bronce anterior verificable y medirlo todo junto con el servicio de la VM.\n\n### Medido para este diseño\n\n- `d311_reinicio_etcd.sh` y `d311_etcd_defender.sh` ya no sirven: miran el 2379 del defender (ahora siempre vacío),\n  piden la clave por HTTP a `127.0.0.1:2379`, leen `/vagrant/logs/lab/etcd-server.log` (ahora el journal de la VM),\n  cuentan `Heartbeat failed` (anterior a B1) y clasifican como MEZCLA un segmento que verifica con las dos claves (lo\n  esperado ahora, si son la misma). Solo se llaman entre ellos.\n- Se reutiliza: la petición por mTLS de `clave_bronce_ml_detector.sh` (E5, identidad del conversor); el conversor\n  `/vagrant/correlation-engine/build/bronze_to_gold_converter` (`ARGUS_BRONZE_HMAC_KEY_HEX`, imprime `filas válidas:\n  N`); el bronce en `/vagrant/logs/correlation/argus-*.csv`; el pcap benigno de los E2E del lab (fuera de git).\n- El etcd-server escribe una línea por petición (`[ETCD←] MÉTODO ruta | status=… | cn=…`, sin relleno) y una por alta en\n  el registro (`[ETCD-REGISTRO] registrado <nombre>`). La regla de autorización `POST /register` también sale al\n  arrancar: no cuenta como registro (lección de DAY316).\n- Etiquetas que existen en el código: ml-detector `[BRONCE-CLAVE-SIN-CONFIRMAR|-CONFIRMADA|-CAMBIADA|-RECUPERADA]` y\n  `[BRONCE-SIN-CLAVE]`; firewall `[FW-CSV-CLAVE-SIN-CONFIRMAR|-CONFIRMADA|-CAMBIADA|-RECUPERADA]` y\n  `[FW-CSV-SIN-CLAVE]`; librería `[ETCD-CLIENTE-SIN-SERVICIO|-REANUDADO|-REGISTRADO|-REGISTRO-PERDIDO]`; firewall\n  `[SOMBRA-DDOS] resumen: ... eventos=N`.\n\n### Decisiones de Alonso (DAY317)\n\n1. El instrumento nuevo sustituye al de DAY311, que se borra (git lo conserva).\n2. Veredicto automático PASA/FALLA, pero primero se mide a mano; después se decide si entra en `lab-e2e` (EMECAS).\n3. La clave del CSV del firewall solo se comprueba por su huella (en el lab el firewall no escribe filas). Se pide por\n   `/secrets/valid/firewall-acl-agent` con la identidad del conversor, que la regla ya permite; no se abre ninguna vía\n   nueva.\n\n### Instrumento\n\n- `scripts/etcd_ha/d317_reinicio_vm.sh` (Mac) y `scripts/etcd_ha/d317_reinicio_defender.sh` (defender). Pasos:\n  comprobaciones (`etcd-vm-check`, pipeline sin `STOPPED`, alias `.51`); marcas de los logs, intervalos de latido de los\n  JSON de los componentes, hora de la VM y claves A (ml-detector y firewall: solo-root fuera de `/vagrant`, por pantalla\n  solo la huella, borradas al final); tráfico benigno a 10 pps; a los 60 s `make etcd-server-stop` y `CAIDO_S` segundos\n  (entero [60, 1800], defecto 150); `make etcd-server-start` (exige quedar sano) y `TRAS_S` segundos ([60, 1800], 150);\n  claves B; fin del tráfico y 40 s de rotación; copia de los logs de los componentes y del journal de la VM (desde el\n  inicio y desde el arranque); verificación de cada segmento con A y con B (clases AB, A, B, NINGUNA, MEZCLA, VACIO).\n- `--veredicto DIR` reevalúa una corrida ya hecha. Trap: para el tráfico, deja el etcd-server activo y borra las claves.\n\n### Veredicto y predicciones (PASA si se cumplen todas)\n\n- Huella A = huella B, en la clave del bronce y en la del CSV.\n- ml-detector: `[BRONCE-CLAVE-SIN-CONFIRMAR]` ≥ 1, `-CONFIRMADA` ≥ 1, `-CAMBIADA` = 0, `[BRONCE-SIN-CLAVE]` = 0.\n- firewall: `[FW-CSV-CLAVE-SIN-CONFIRMAR]` ≥ 1, `-CONFIRMADA` ≥ 1, `-CAMBIADA` = 0, `[FW-CSV-SIN-CLAVE]` = 0.\n- Cada componente: `[ETCD-CLIENTE-SIN-SERVICIO]` ≥ 1, `[ETCD-CLIENTE-REANUDADO]` = 1, `-REGISTRADO` = 0,\n  `-REGISTRO-PERDIDO` = 0.\n- etcd-server tras arrancar: 0 componentes registrados de nuevo, 0 `POST /register`, 0 latidos con status distinto de\n  200, y latidos 200 de cada componente ≥ `TRAS_S / intervalo − 1`.\n- Bronce: ≥ 1 segmento en el intervalo y todos en AB (también los escritos con el servidor caído, firmados en modo\n  extendido).\n- Continuidad: el firewall resume eventos (`eventos` > 0).\n- Banco: el veredicto con una corrida falsa buena da PASA y cada condición rota da FALLA.\n'
BACKLOG = '\n## DAY317 — diseño del paso 7 de DEBT-ETCD-HA-TLS-RAFT-001\n\nDocumento: `docs/ml-heads/day312_diseno.md`, «Diseño del paso 7». Instrumento nuevo\n`scripts/etcd_ha/d317_reinicio_vm.sh` (+ ayudante del defender) que sustituye al de DAY311 (se borra): reinicia el\netcd-server de la VM con el pipeline vivo y tráfico benigno, y da un veredicto PASA/FALLA (misma huella de bronce y CSV,\nningún registro nuevo, latidos 200, todo el bronce del intervalo verificable con la clave de antes y la de después).\nDecisión de Alonso: primero se mide a mano; luego se decide si entra en `lab-e2e`.\n'

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
