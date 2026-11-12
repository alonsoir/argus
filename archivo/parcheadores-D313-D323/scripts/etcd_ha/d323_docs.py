#!/usr/bin/env python3
# d323_docs.py — DEBT-ETCD-HA-TLS-RAFT-001, PR1 (DAY323): documentación del DAY322 que faltaba (8e.5 y las cuatro paradas
# de EMECAS) y del DAY323 (Suricata, un solo reloj, ventana MITRE, Jenkins, sensores como infraestructura, veredicto de
# protegidos, emecas-progreso; EMECAS+++ desde cero en verde).
# docs/BACKLOG.md: en DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001, la clave de Jenkins hecha y el JDK de Jenkins pendiente; y al
#   final, el texto de scripts/etcd_ha/d323_backlog_anexo.md (se escribe antes a mano y se comprueba su sha256): las
#   secciones DAY322 y DAY323 y las deudas nuevas DEBT-CTU-START-VENTANA-001 y DEBT-DDOS-COLATERAL-LEGITIMO-001.
# ADR-060: 8e.5 hecho en la sección 5 y el párrafo «8e.5, DAY322-323» al final de la 7.
# Uso:  python3 d323_docs.py --check <raiz_repo>
#       python3 d323_docs.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si CADA fichero está en el estado previo exacto y el resultado da su sha256 final.
import hashlib, os, sys

ANEXO = 'scripts/etcd_ha/d323_backlog_anexo.md'
SHA_ANEXO = 'f0f6b6aff11724aff31a94fc7729be462b3c1631e290588ff5bd369dcd1a4fc9'
SUPPLY_V = 'hardened, fijada). Queda: libsodium se descarga en el Vagrantfile sin comprobar sha256 ni firma;'
SUPPLY_N = 'hardened, fijada). Hecho DAY323 [JENKINS-CLAVE-D323]: la clave del repositorio de Jenkins, de pkg.jenkins.io por huella\n(`provisioning/jenkins/CLAVE`, `5E386EAD…7198F4B714ABFC68`; antes, un keyserver de terceros sin comprobar nada).\nQueda: el JDK de Jenkins se instala con `curl https://get.sdkman.io | bash` sin verificar (Adoptium tiene apt firmado\npara bookworm); libsodium se descarga en el Vagrantfile sin comprobar sha256 ni firma;'
FIN_BACKLOG = 'DEBT-LAB-ZONA-HORARIA-001, DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001, DEBT-HARDENED-FALCO-RUTAS-001,\nDEBT-VAULT-SELLADO-ALERTA-001.\n'
BACKLOG = ('docs/BACKLOG.md', '1e4f77c7de60aba59311daa74546669affaf26b0eabb4a7b77d84a40f00907bc', 'f65471a645719ebc26d6d9254e95c9e07f0096d1886cd9039c5cb911f22b7dd5')
ADR = ('docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md', '4e0a7fc6bca4beebd5acbf2594f4cd35f497c58028be04d47c1da3ba3b22972b', '4e58c38009805dc7add4c1d5b4967847f03dabf49987cf24cb61ac7faea99528', [('- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n', '- **8e.5** (hecho DAY322, aae32596d) Bootstrap del lab con `argus-infra`, veredicto P1–P6. Desde DAY323 la plantilla\n    lleva también los sensores .10, .11 y .12 como infraestructura (95d349c89). EMECAS+++ desde cero en verde el DAY323\n    (ver «8e.5, DAY322-323» en la sección 7).\n'), ('menos que un `pipeline-status` sano (17): no hace falta agruparlas. Dos corridas en PASA.\n', 'menos que un `pipeline-status` sano (17): no hace falta agruparlas. Dos corridas en PASA.\n\n**8e.5, DAY322-323: bootstrap del manifiesto y EMECAS+++ desde cero [PROTEGIDOS-BOOTSTRAP-D322] [PROTEGIDOS-SENSORES-D323].**\nEl bootstrap firma la versión 1 desde la plantilla del lab (`argus-infra init --desde … --si`; rc 4 propio si ya hay un\nmanifiesto, que el bootstrap da por bueno) y lab-e2e-protegidos la exige en P1-P6. Las paradas de EMECAS+++ desde cero\ndel DAY322 (antispoof con lo esperado escrito a mano, R3 contando flujos ajenos, el grupo del agente de Wazuh, C7 en\nuna VM nueva) y del DAY323 (Suricata sin reglas ni interfaz, un reloj por sensor, la ventana MITRE, la clave de Jenkins,\nel NTP de los sensores dentro del episodio DDoS) están medidas una a una en `docs/BACKLOG.md`. La que toca a este ADR:\ncon la hora del defender, el NTP de los sensores (.10, .11, .12) a .1 caía dentro del ataque UDP y entraba en\n`origenes=`; los sensores son infraestructura del NDR y entran en la plantilla (MAC vacía, decisión de Alonso), y el\nveredicto saca la infraestructura del manifiesto que aplica el firewall, no de una lista fija. El fondo (tráfico\nlegítimo hacia la víctima dentro del episodio) es DEBT-DDOS-COLATERAL-LEGITIMO-001. Resultado: EMECAS+++ desde cero\nPASA el DAY323 (4h02m, sobre 443fffb96).\n')])

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    if not os.path.isfile(p(ANEXO)) or sha(open(p(ANEXO), 'rb').read()) != SHA_ANEXO:
        print('FALLA: %s falta o no tiene el sha256 esperado (%s...); no se toca nada.' % (ANEXO, SHA_ANEXO[:16])); return 1
    anexo = open(p(ANEXO), 'rb').read().decode('utf-8')
    planes = [(BACKLOG[0], BACKLOG[1], BACKLOG[2], [(SUPPLY_V, SUPPLY_N), (FIN_BACKLOG, FIN_BACKLOG + anexo)]),
              (ADR[0], ADR[1], ADR[2], ADR[3])]
    nuevos, ya = {}, []
    for ruta, previo, final, cambios in planes:
        if not os.path.isfile(p(ruta)):
            print('FALLA: no existe %s; no se toca nada.' % ruta); return 1
        b = open(p(ruta), 'rb').read()
        if sha(b) == final:
            ya.append(ruta); continue
        if sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
        t = b.decode('utf-8')
        for i, (v, n) in enumerate(cambios, 1):
            if t.count(v) != 1:
                print('FALLA: %s, cambio %d: %d apariciones (se exige 1); no se toca nada.' % (ruta, i, t.count(v))); return 1
            t = t.replace(v, n)
        if sha(t.encode('utf-8')) != final:
            print('FALLA: %s: el resultado no da el sha256 final; no se toca nada.' % ruta); return 1
        nuevos[ruta] = t.encode('utf-8')
    if not nuevos:
        print('YA APLICADO: no se toca nada.'); return 0
    if ya:
        print('FALLA: aplicado a medias (ya: %s); no se toca nada.' % ', '.join(ya)); return 1
    if modo == '--check':
        print('APLICABLE: %s.' % ', '.join(nuevos)); return 0
    for ruta, nuevo in nuevos.items():
        tmp = p(ruta) + '.d323tmp'
        with open(tmp, 'wb') as o: o.write(nuevo)
        os.chmod(tmp, os.stat(p(ruta)).st_mode & 0o7777); os.replace(tmp, p(ruta))
        print('  escrito  %s (sha256 %s)' % (ruta, sha(nuevo)[:16]))
    print('APLICADO.'); return 0

if __name__ == '__main__':
    sys.exit(main())
