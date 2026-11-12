#!/usr/bin/env python3
# d323_sensores_protegidos.py — (DAY323) [PROTEGIDOS-SENSORES-D323]: los sensores del lab (.10 suricata, .11 zeek,
# .12 wazuh) entran en la plantilla del manifiesto de protegidos como infraestructura, con MAC vacía (decisión de Alonso
# DAY323): son máquinas del NDR y nunca se bloquean. Medido DAY323: con la hora del defender ([LAB-NTP-SENSORES-D323]),
# su NTP a .1 durante el ataque UDP entró en el episodio de la cabeza DDoS (origenes=...,.10:1,.11:1,.12:1) y P2 de
# lab-e2e-protegidos falló. El problema de fondo queda como DEBT-DDOS-COLATERAL-LEGITIMO-001. Actualiza las tres
# aserciones de tools/argus-infra/test_argus_infra.py que fijan el contenido de la plantilla.
# Uso:  python3 d323_sensores_protegidos.py --check <raiz_repo>
#       python3 d323_sensores_protegidos.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si CADA fichero está en el estado previo exacto y el resultado da su sha256 final.
import hashlib, os, sys

FICHEROS = {'tools/argus-infra/plantillas/hospital-lab.json': ('052cac1b2669a3eb8b276795f87729731a1a30ee88b94a8f203b1f27c8c0b261', '136ab3734e322284212892d5df42eeedb96d588229cfce1fa14db461be74ad82', [('Valores de LABORATORIO: nunca copiarlos a producción.",', 'Valores de LABORATORIO: nunca copiarlos a producción. [PROTEGIDOS-SENSORES-D323] .10, .11 y .12 son los sensores del lab (suricata, zeek, wazuh): infraestructura del NDR, nunca se bloquean (medido DAY323: con la hora del defender, su NTP a .1 durante el ataque UDP entraba en el episodio de la cabeza DDoS y P2 fallaba). MAC vacía (decisión de Alonso DAY323).",', 1), ('      { "categoria": "infraestructura", "cidr": "192.168.100.20/32", "interfaz": "eth2", "mac": "08:00:27:a2:00:20", "motivo": "VM etcd: etcd, etcd-server, Vault" },\n', '      { "categoria": "infraestructura", "cidr": "192.168.100.20/32", "interfaz": "eth2", "mac": "08:00:27:a2:00:20", "motivo": "VM etcd: etcd, etcd-server, Vault" },\n      { "categoria": "infraestructura", "cidr": "192.168.100.10/32", "interfaz": "eth2", "mac": "", "motivo": "VM suricata: sensor del NDR" },\n      { "categoria": "infraestructura", "cidr": "192.168.100.11/32", "interfaz": "eth2", "mac": "", "motivo": "VM zeek: sensor del NDR" },\n      { "categoria": "infraestructura", "cidr": "192.168.100.12/32", "interfaz": "eth2", "mac": "", "motivo": "VM wazuh: manager del NDR" },\n', 1)]), 'tools/argus-infra/test_argus_infra.py': ('e6f83bf26a7171f99d71e924f4da943ca633862999e4ef50e19d9a57f7826c5d', '03d58a843dfbb6c709b5489babf5993a1a444ab2f4591dcc48674dc20a52a474', [('                         [("infraestructura", "192.168.100.20/32", "eth2"), ("intranet", "192.168.100.61/32", "eth2")])\n', '                         [("infraestructura", "192.168.100.20/32", "eth2"), ("infraestructura", "192.168.100.10/32", "eth2"),\n                          ("infraestructura", "192.168.100.11/32", "eth2"), ("infraestructura", "192.168.100.12/32", "eth2"),\n                          ("intranet", "192.168.100.61/32", "eth2")])\n', 1), ('        self.assertEqual([e["cidr"] for e in plantas["lab-vagrant"]], ["192.168.100.20/32", "192.168.100.61/32"])\n', '        self.assertEqual([e["cidr"] for e in plantas["lab-vagrant"]],\n                         ["192.168.100.20/32", "192.168.100.10/32", "192.168.100.11/32", "192.168.100.12/32",\n                          "192.168.100.61/32"])\n', 1), ('        self.assertEqual(len(p["plantas"]["lab-vagrant"]), 2)\n', '        self.assertEqual(len(p["plantas"]["lab-vagrant"]), 5)   # .20 + los sensores .10 .11 .12 [PROTEGIDOS-SENSORES-D323] + .61\n', 1)])}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
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
