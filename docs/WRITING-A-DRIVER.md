# Escribir un driver de ataque para aRGus

`aRGus` genera un dataset **en función de un traffic driver**: un script que mete
tráfico en la red vigilada. El pipeline aguas abajo (bronce → oro → grafo →
veredicto) es **invariante**; lo único que cambia entre un dataset y otro es el
tráfico que provoca el driver.

Dos drivers de referencia en `scripts/`:

- `mitre_start.sh` — dispara `nmap -A` (escaneo activo). `make mitre-start`.
- `ctu_start.sh` — replay del pcap Neris CTU-13 con `tcpreplay`. `make ctu-start`.

Son **idénticos salvo una línea**: la que dispara el tráfico. Esa línea es el
**SEAM**, y es lo único que tú escribes.

## El contrato en una frase

> Pon tráfico en `ml_defender_gateway_lan` (192.168.100.0/24), entre T0 y el
> final del drenaje, donde las tres lentes lo vean. El harness lo captura por
> `mtime > T0` y es agnóstico de la fuente.

Topología (no la configuras, la usas):

- `client` inyecta desde `eth1` → 192.168.100.50
- aRGus sniffa `eth2` PRE-NAT en `defender` → 192.168.100.1
- `suricata` en `eth1` → .10 · `zeek` en `eth1` → .11

Si tu tráfico no cae en esa LAN (p.ej. lo lanzas hacia Internet post-NAT), las
lentes no lo ven y tu dataset saldrá vacío. No es un bug del pipeline: es el
contrato.

## Pasos

1. Copia la plantilla:
cp scripts/custom_start.sh.template scripts/mi_driver.sh
2. Edita **solo** el bloque `>>> SEAM <<<`. Todo lo demás está marcado
   `# INVARIANTE — NO TOCAR`. Pon ahí tu disparo de tráfico y borra el `die` que
   trae la plantilla (está para que falle ruidoso si no lo editas). Ejemplos:
vagrant ssh client -c "sudo nmap -sV 192.168.100.1" || die "nmap fallo"
vagrant ssh client -c "sudo tcpreplay -i eth1 --mbps=10 /vagrant/datasets/ctu13/tu.pcap" || die "tcpreplay fallo"
Si tu herramienta necesita un prerequisito (un fichero, un binario), añade un
   guard justo antes:
vagrant ssh client -c "test -f /vagrant/datasets/tu.pcap" || die "falta el pcap"
3. Arranca el entorno y corre tu driver:
make up && make bootstrap # 5 VMs + pipeline arriba (una vez)
make custom-start DRIVER=scripts/mi_driver.sh
4. Valida que produjo artefactos:
make validate-driver
Comprueba los tres oros del STAMP de tu corrida y que la BD Kuzu tiene filas.

## Qué hace el invariante por ti

No tocas nada de esto, pero conviene saber qué corre:

1. Saca la clave HMAC del bronce del etcd-server (hack de desarrollo, ver abajo).
2. Marca T0 (`touch mitre-t0-$STAMP.marker`) y arma Zeek (`zeekctl deploy`)
   **antes** del tráfico.
3. **[tu SEAM]** dispara el tráfico.
4. Drena 45s, cosecha el `conn.log` de Zeek, para Zeek.
5. Construye los tres oros (aRGus por ventana `mtime>T0`, Suricata del `eve.json`,
   Zeek del `conn.log`), cada uno sellado con HMAC; si algún converter descarta
   filas, aborta.
6. Carga los tres oros en una BD Kuzu fresca y puebla la arista `CORRELATES_FLOW`
   por `community_id`.
7. Imprime el veredicto: sensores en el grafo, invariante (=0), y flujos
   corroborados cross-sensor.

## Consideraciones

- **Bloqueante vs asíncrono.** `nmap` y `tcpreplay` bloquean hasta terminar, así
  que el `sleep 45` posterior drena lo que quede en vuelo. Si tu herramienta es
  asíncrona (lanza y vuelve), ajusta ese drenaje en la plantilla.
- **Timing de replay.** Un replay a `--mbps=10` reescribe los inter-arrival: las
  features **temporales** del dataset son artefacto del reloj de replay; las
  **espaciales/5-tupla** son fieles. Decláralo en tu data card.
- **Volumen ≠ detección.** Que otra lente *vea* un flujo no es que lo *alerte*.
  El veredicto cuenta co-visibilidad, no detecciones corroboradas.

## Seguridad

El invariante saca la clave HMAC con un `GET` HTTP en claro al etcd-server. Es un
**hack de desarrollo, no apto para producción**
(`DEBT-HMAC-KEY-INSECURE-TRANSPORT-001`). El arreglo correcto es que los
componentes lean la clave directamente de Vault (auth/TLS/leases). Si mantienes
el pipeline: hazlo a tu manera, pero hazlo.

## Contribuir

Se esperan PRs con drivers nuevos en `scripts/`. Un driver = una plantilla
rellenada + su entrada en la data card. El harness no cambia.
