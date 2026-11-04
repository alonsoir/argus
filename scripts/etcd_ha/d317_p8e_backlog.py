#!/usr/bin/env python3
# DAY317 paso 8e (documentacion): anade al final de docs/BACKLOG.md los resultados del EMECAS+++ del DAY317,
# la deuda DEBT-FW-MANIFIESTO-PROTEGIDOS-001 (ADR-060) y las deudas y lecciones nuevas.
# Uso: python3 d317_p8e_backlog.py --check <raiz> | --apply <raiz>
# Todo o nada, idempotente (marca [MANIFIESTO-PROTEGIDOS-D317]); imprime sha256 previo y final.
import hashlib
import os
import sys

MARCA = "[MANIFIESTO-PROTEGIDOS-D317]"
REL = "docs/BACKLOG.md"
ADR = "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md"

BLOQUE = """

---

## DAY317 — Resultado del EMECAS+++ y DEBT-FW-MANIFIESTO-PROTEGIDOS-001 """ + MARCA + """

### Resultado del EMECAS+++ (paso 8), miércoles 2026-11-04
`make emecas+++ PROFILE=production`: 2 h 20 min, **FALLA** en `lab-e2e-protegidos`, criterio P2. Todo lo anterior
pasó: test-all, firewall e2e/perf, test-e2e-synthetic, los tres reinicios (R1-R3 PASA en antes, ordenada y kill9),
P1, P3, P4 y P5. El Acto IV no llegó a correr (`err_to_row` del adapter de Suricata sigue sin medir desde cero).

```
[VEREDICTO] FALLA P2 episodio: FIN=1 (esperado 1), origenes=192.168.100.50:10780,192.168.100.20:3
```

Medido: 192.168.100.20 es la VM etcd; el episodio es UDP (`proto=17`); la VM etcd sincroniza con chrony contra el
defender (`server 192.168.100.1`, poll 64 s); 207 s de episodio / 64 s = 3 peticiones NTP de cliente que `ddos_v2`
marcó junto con la reflexión NTP. El HTTPS del etcd-server (TCP) es normal. Con la mitigación real (hoy en sombra) la
VM etcd quedaría una hora en el blacklist: **DoS autoinfligido del plano de control**. P2 hizo bien su trabajo y no se
relaja. Diseño y decisiones: `""" + ADR + """`.

### DEBT-FW-MANIFIESTO-PROTEGIDOS-001 — ABIERTA, BLOQUEANTE para el merge de PR1 (decisión de Alonso DAY317)
Entra en esta PR: EMECAS no deja pasar sin ella y no se debilita EMECAS por haber hecho su trabajo.
Un manifiesto firmado (Ed25519, clave privada en Vault transit por hospital, pública compilada en el firewall) por
despliegue, con categorías `infraestructura`, `intranet`, `dmz`, `externos_criticos`; sustituye a `ddos_protegidos` de
cada `firewall.json`. Entradas estrechas `{cidr, interfaz, mac?, motivo}`, límites de prefijo por categoría desde la
plantilla de despliegue (`infraestructura` solo /32 y /128). Versión monótona, deshacer firmado, candado (la mitigación
real exige manifiesto verificado), último verificado en memoria y aviso periódico, comprobación continua kernel ↔
manifiesto, alertas de spoofing por interfaz y MAC, Falco, Wazuh y audit de Vault. `argus-infra` solo en la máquina
del admin.
Pasos: 8e.1 firewall · 8e.2 Vault transit · 8e.3 `argus-infra` y rutas del etcd-server · 8e.4 vigilancia ·
8e.5 bootstrap del lab, veredicto P1-P6 y EMECAS+++.
**Test de cierre:** EMECAS+++ PROFILE=production rc 0 con `lab-e2e-protegidos` P1-P6 PASA, .20 aprovisionado en
`infraestructura` por `argus-infra` en el bootstrap, y los tests de 8e.1 (firma, versión, despliegue, límites,
caché, candado) en verde.

### Limitación del laboratorio (decisión de Alonso DAY317)
`argus-infra` vive en la VM etcd: no hay RAM para una VM admin y Vault solo escucha en 127.0.0.1. En producción la
máquina admin la fija la plantilla de despliegue de Jenkins. Escrito también en el `_doc` correspondiente.

### Medido DAY317: la whitelist exime de TODO bloqueo de aRGus
`iptables_wrapper.cpp`: `--match-set <whitelist> src ... RETURN` antes del blacklist. Un origen protegido no queda
exento solo de la cabeza DDoS, sino de todo bloqueo. Razón de más para que la lista sea un manifiesto firmado.

### DEBT-DDOS-V2-NTP-CLIENTE-001 — ABIERTA (nueva DAY317)
`ddos_v2_fact_rf@day293-f3d6b261` marca con p1 >= 0,96 una petición NTP de cliente legítima (48 bytes,
`.20:<p> -> .1:123`) que cae dentro de un episodio de reflexión NTP contra la misma víctima. Defecto del modelo; el
manifiesto evita el daño, no lo corrige. Destino: `diag/ml-heads`.
**Test de cierre:** con el modelo corregido, una corrida de `lab-e2e-protegidos` SIN .20 en el manifiesto da `origenes=` solo .50.

### DEBT-FW-DOS-PERSONAS-001 — ABIERTA, no bloqueante (nueva DAY317)
Regla de dos personas para firmar el manifiesto (Vault control groups). No ahora: muchos hospitales no tendrán dos
administradores. Campo futuro en la plantilla, desactivado por defecto.

### Hipótesis sin medir (Alonso DAY317): el DDoS autoinfligido, primo malvado del DoS autoinfligido
En un despliegue distribuido real, el tráfico legítimo del propio aRGus (N componentes reconectando a la vez al
etcd-server tras una caída, latidos alineados, muchos clientes NTP contra el mismo servidor de hora) podría parecer un
DDoS contra un nodo del plano de control. Se mide en PR2 (3 nodos). Sin predicción todavía: no adelantarse.

### Pendiente de decidir: eve.json de Suricata (medido DAY317)
Los dos avisos `json ilegible` del adapter de Suricata (líneas 9393 y 20447 de `/var/log/suricata/eve.json`) son
huellas de apagados bruscos de la VM (arranques del 1, 2 y 3 de noviembre sin `shutdown` en `last -x`): un registro
cortado con otro pegado, y 3024 bytes `\\0` de asignación diferida de ext4. El adapter hizo lo correcto (Error, no
Skip; `err_to_row=2`; 0 descartadas en la conversión). Opciones propuestas, a decidir por Alonso: (c) `mitre_start` y
`ctu_start` dan al adapter solo lo escrito desde T0 (tamaño en bytes en T0 y `tail -c +N`; si el fichero encoge, se
lee entero y se avisa) y (b) `err_to_row=0` obligatorio; opcional, las dos líneas reales (recortadas) como casos de
`test_to_row`.

### Lecciones DAY317
EMECAS debe levantar la topología de producción, no un subconjunto: con solo defender y client no existía .20 y P2
pasaba. El fallo no estaba en el código de ninguna pieza, sino en la topología. El DoS autoinfligido no solo viene de
que alguien escriba en la lista protegida: también de que falte algo en ella. Antes de afirmar una causa, mirar el
protocolo del episodio (la primera hipótesis, el HTTPS del etcd-server, cayó con `proto=17`).
"""


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d317_p8e_backlog.py --check|--apply <raiz>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    p = os.path.join(raiz, REL)
    if not os.path.isfile(p):
        print("[FALLA] no existe " + p)
        return 1
    if not os.path.isfile(os.path.join(raiz, ADR)):
        print("[FALLA] falta " + ADR + " (copialo antes: el BACKLOG lo cita)")
        return 1
    with open(p, "r", encoding="utf-8") as f:
        txt = f.read()
    print("[INFO] sha256 previo  " + sha(p))
    if MARCA in txt:
        print("[OK] ya aplicado (marca presente); nada que hacer")
        return 0
    if modo == "--check":
        print("[OK] se puede aplicar: se anaden " + str(BLOQUE.count("\n")) + " lineas al final de " + REL)
        return 0
    tmp = p + ".d317tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(txt.rstrip("\n") + BLOQUE)
    os.replace(tmp, p)
    print("[OK] aplicado")
    print("[INFO] sha256 final   " + sha(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
