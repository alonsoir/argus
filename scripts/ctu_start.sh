#!/usr/bin/env bash
# scripts/ctu_start.sh — DAY 249. 2o traffic driver, HERMANO de mitre_start.sh.
# Downstream IDENTICO (bronce->oro->grafo->veredicto); la UNICA diferencia con
# mitre_start.sh es la fuente de trafico: replay del pcap Neris (CTU-13, escenario 1)
# con tcpreplay @10mbps en vez de `nmap -A`. `make ctu-start` deja el grafo cross-sensor
# de UNA corrida del Neris en Kuzu, cero comandos manuales.
# Requiere: `make pipeline-start` antes (aRGus sniffando eth2) + el pcap en
# /vagrant/datasets/ctu13/ (si falta: `make fetch-neris`, DEBT-DATASETS-FETCH-NOT-AUTOMATED-001).
# NOTA DE DISENO: KUZU y las rutas de oro se dejan IDENTICAS a mitre_start.sh a proposito,
# para que dataset_export.py (que autodetecta el STAMP del ultimo oro de argus) consuma esta
# corrida SIN cambios. El prefijo "mitre-" del nombre de la BD es legado; el STAMP desambigua.
# Se ejecuta en el HOST; trabaja en los guests via vagrant ssh. A. Roman + Claude.
set -uo pipefail
CE="/vagrant/correlation-engine/build"; SCHEMA="/vagrant/correlation-engine/schema/schema.cypher"
LAB="/vagrant/logs/lab"; ADAPTER="/vagrant/suricata-adapter/build-suricata/suricata_adapter"
ZEEKCTL="/opt/zeek/bin/zeekctl"
ZEEK_ADAPTER="/vagrant/zeek-adapter/build-zeek/zeek_adapter"
ZEEK_SPOOL="/opt/zeek/spool/zeek"   # conn.log vivo (confirmado DAY 237)
NERIS="/vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap"   # ruta GUEST (client ve /vagrant)
STAMP="$(date -u +%Y%m%d-%H%M%S)"; KUZU="/vagrant/logs/day234-kuzu/mitre-$STAMP.kuzu"
die(){ echo "X $*" >&2; exit 1; }
echo ""
echo "##################################################################"
echo "#  ALERT  ##  HACK DE DESARROLLO — NO APTO PARA PRODUCCION  ##    #"
echo "#                                                                #"
echo "#  ctu-start saca la clave HMAC con un GET HTTP EN CLARO al       #"
echo "#  etcd-server (curl http://localhost:2379/secrets/ml-detector).  #"
echo "#  Clave de cifrado en TEXTO PLANO por la red, sin TLS ni auth.   #"
echo "#  DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 (P1) +                    #"
echo "#  DEBT-BRONZE-KEY-PROVISIONING-001. Arreglo correcto (NO aqui):  #"
echo "#  converter y componentes DIRECTOS a Vault (auth/TLS/leases);    #"
echo "#  idealmente Jenkins exporta esta env var al crear la clave.     #"
echo "#  Quien mantenga el pipeline: hazlo a tu manera, pero hazlo.     #"
echo "##################################################################"
echo ""

# 1) Clave HMAC del bronce (el hack)   [INVARIANTE]
KEY=$(vagrant ssh defender -c "curl -s http://localhost:2379/secrets/ml-detector | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"key\"])'" 2>/dev/null | tr -d '\r')
[ ${#KEY} -eq 64 ] || die "clave HMAC no es 64 hex (len=${#KEY}). ¿pipeline-start arriba? ¿etcd-server RUNNING?"
echo "OK clave HMAC en mano (64 hex, head ${KEY:0:8}...)"

# 2) Marca T0 y disparo del DRIVER (tcpreplay del Neris: la UNICA seccion que cambia vs mitre_start.sh)
vagrant ssh defender -c "touch $LAB/mitre-t0-$STAMP.marker"
# --- Zeek vivo: deploy ANTES del trafico (conn.log nace ~T0, windowing por construccion) ---
vagrant ssh zeek -c "sudo $ZEEKCTL deploy" || die "zeekctl deploy fallo"
# --- guard: el pcap tiene que estar en su sitio (si no, la deuda de fetch te lo dice claro) ---
vagrant ssh client -c "test -f $NERIS" || die "pcap Neris ausente en $NERIS -> corre 'make fetch-neris' (DEBT-DATASETS-FETCH-NOT-AUTOMATED-001)"
echo "-- Disparo DRIVER (tcpreplay Neris @10mbps, ~45s para 56MB) desde client sobre eth1 --"
vagrant ssh client -c "sudo tcpreplay -i eth1 --mbps=10 --stats=5 $NERIS" || die "tcpreplay fallo"
echo "-- Drenaje 45s --"; sleep 45
# --- Zeek: cosechar conn.log del spool MIENTRAS corre, antes del stop (que lo archiva) ---
vagrant ssh zeek -c "sudo cp $ZEEK_SPOOL/conn.log $LAB/zeek-$STAMP.conn.log && sudo chmod 644 $LAB/zeek-$STAMP.conn.log" || die "no hay conn.log en el spool (zeek no vio trafico en la ventana?)"
vagrant ssh zeek -c "sudo $ZEEKCTL stop"

# 3) Oro de aRGus: bronce de la ventana del ataque (mtime > T0), convertido con la clave real   [INVARIANTE]
vagrant ssh defender -c "cat \$(find /vagrant/logs/correlation -name 'argus-*.csv' -newer $LAB/mitre-t0-$STAMP.marker | sort) > $LAB/argus-$STAMP.bronce.csv"
vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY ./bronze_to_gold_converter $LAB/argus-$STAMP.bronce.csv $LAB/argus-$STAMP.avro $LAB/argus-$STAMP.parquet" | tee /tmp/argus-conv.log
grep -q "descartadas: 0" /tmp/argus-conv.log || die "aRGus: descartadas>0 -> la clave no caso (¿pipeline reiniciado? ¿rotacion?)"

# 4) Oro de Suricata: adapter alert-only sobre el eve.json vivo (clave HMAC real del bronce, la misma que aRGus)   [INVARIANTE]
vagrant ssh suricata -c "sudo cp /var/log/suricata/eve.json $LAB/eve-$STAMP.json && sudo chmod 644 $LAB/eve-$STAMP.json"
vagrant ssh suricata -c "python3 -c \"import json; json.dump({'base_dir':'$LAB','node_id':'cpp_sniffer_v33_day12','input_path':'logs/lab/eve-$STAMP.json','hmac_key_env':'ARGUS_BRONZE_HMAC_KEY_HEX'}, open('$LAB/suri-adapter-$STAMP.json','w'))\""
vagrant ssh suricata -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY $ADAPTER $LAB/suri-adapter-$STAMP.json"
SURI_CSV=$(vagrant ssh suricata -c "ls -t $LAB/suricata-*.csv | head -1" 2>/dev/null | tr -d '\r')
vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY ./bronze_to_gold_converter $SURI_CSV $LAB/suricata-$STAMP.avro $LAB/suricata-$STAMP.parquet" | tee /tmp/suri-conv.log
grep -q "descartadas: 0" /tmp/suri-conv.log || die "suricata: descartes HMAC>0 -> clave real no caso (adapter vs converter)"

# 4b) Oro de Zeek: conn.log de la ventana (ya cosechado) -> adapter (clave real) -> converter   [INVARIANTE]
vagrant ssh zeek -c "python3 -c \"import json; json.dump({'base_dir':'$LAB','node_id':'cpp_sniffer_v33_day12','input_path':'logs/lab/zeek-$STAMP.conn.log','hmac_key_env':'ARGUS_BRONZE_HMAC_KEY_HEX'}, open('$LAB/zeek-adapter-$STAMP.json','w'))\""
vagrant ssh zeek -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY $ZEEK_ADAPTER $LAB/zeek-adapter-$STAMP.json"
ZEEK_CSV=$(vagrant ssh zeek -c "ls -t $LAB/zeek-*.csv | head -1" 2>/dev/null | tr -d '\r')
vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY ./bronze_to_gold_converter $ZEEK_CSV $LAB/zeek-$STAMP.avro $LAB/zeek-$STAMP.parquet" | tee /tmp/zeek-conv.log
grep -q "descartadas: 0" /tmp/zeek-conv.log || die "zeek: descartes HMAC>0 -> clave real no caso"

# 5) Kuzu fresca + carga de los TRES oros + poblador CORRELATES_FLOW   [INVARIANTE]
vagrant ssh defender -c "mkdir -p /vagrant/logs/day234-kuzu"
vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/argus-$STAMP.parquet $KUZU $SCHEMA"
vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/suricata-$STAMP.parquet $KUZU $SCHEMA"
vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/zeek-$STAMP.parquet $KUZU $SCHEMA"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (a:NetworkFlow),(b:NetworkFlow) WHERE a.community_id=b.community_id AND a.flow_uid<b.flow_uid MERGE (a)-[e:CORRELATES_FLOW]->(b) ON CREATE SET e.community_id=a.community_id, e.method='community_id', e.confidence=1.0\""

# 6) Veredicto del dia
echo ""; echo "======== CTU/NERIS -> GRAFO ($STAMP) ========"
echo "-- sensores en el grafo --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (e:TelemetryEvent) RETURN e.source_sensor, count(*)\""
echo "-- invariante (debe ser 0) --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (a:NetworkFlow)-[e:CORRELATES_FLOW]->(b:NetworkFlow) WHERE a.community_id<>b.community_id RETURN count(*)\""
echo "-- flujos corroborados cross-sensor (EL TITULAR) --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (ea:TelemetryEvent)-[:TELEMETRY_ABOUT]->(a:NetworkFlow)-[e:CORRELATES_FLOW]-(b:NetworkFlow)<-[:TELEMETRY_ABOUT]-(eb:TelemetryEvent) WHERE ea.source_sensor<>eb.source_sensor RETURN count(DISTINCT e.community_id)\""
echo "BD: $KUZU"; echo "========================================="