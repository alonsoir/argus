#!/usr/bin/env bash
# scripts/mitre_start.sh — DAY 234. Automatiza el camino MITRE -> grafo de DAY 233.
# `make mitre-start` deja aristas cross-sensor (aRGus<->Suricata) en Kuzu con datos
# DEL DIA, cero comandos manuales. Requiere `make pipeline-start` antes.
# Se ejecuta en el HOST; trabaja en los guests via vagrant ssh. A. Roman + Claude.
set -uo pipefail
# NOT A SECRET — clave de juguete de test, DAY 227. La clave real se saca en runtime por curl.
TOY_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" # gitleaks:allow # pragma: allowlist secret
CE="/vagrant/correlation-engine/build"; SCHEMA="/vagrant/correlation-engine/schema/schema.cypher"
LAB="/vagrant/logs/lab"; ADAPTER="/vagrant/suricata-adapter/build-suricata/suricata_adapter"
ZEEKCTL="/opt/zeek/bin/zeekctl"
# <CONFIRMAR> nombre/ruta del binario del adapter (espejo de suricata_adapter):
ZEEK_ADAPTER="/vagrant/zeek-adapter/build-zeek/zeek_adapter"
ZEEK_SPOOL="/opt/zeek/spool/zeek"   # conn.log vivo (confirmado DAY 237)
STAMP="$(date -u +%Y%m%d-%H%M%S)"; KUZU="/vagrant/logs/day234-kuzu/mitre-$STAMP.kuzu"
die(){ echo "X $*" >&2; exit 1; }

echo ""
echo "##################################################################"
echo "#  ALERT  ##  HACK DE DESARROLLO — NO APTO PARA PRODUCCION  ##    #"
echo "#                                                                #"
echo "#  mitre-start saca la clave HMAC con un GET HTTP EN CLARO al     #"
echo "#  etcd-server (curl http://localhost:2379/secrets/ml-detector).  #"
echo "#  Clave de cifrado en TEXTO PLANO por la red, sin TLS ni auth.   #"
echo "#  DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 (P1) +                    #"
echo "#  DEBT-BRONZE-KEY-PROVISIONING-001. Arreglo correcto (NO aqui):  #"
echo "#  converter y componentes DIRECTOS a Vault (auth/TLS/leases);    #"
echo "#  idealmente Jenkins exporta esta env var al crear la clave.     #"
echo "#  Quien mantenga el pipeline: hazlo a tu manera, pero hazlo.     #"
echo "##################################################################"
echo ""

# 1) Clave HMAC del bronce (el hack)
KEY=$(vagrant ssh defender -c "curl -s http://localhost:2379/secrets/ml-detector | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"key\"])'" 2>/dev/null | tr -d '\r')
[ ${#KEY} -eq 64 ] || die "clave HMAC no es 64 hex (len=${#KEY}). ¿pipeline-start arriba? ¿etcd-server RUNNING?"
echo "OK clave HMAC en mano (64 hex, head ${KEY:0:8}...)"

# 2) Marca T0 y disparo MITRE (nmap -A: el que hace reaccionar a los DOS sensores)
vagrant ssh defender -c "touch $LAB/mitre-t0-$STAMP.marker"
# --- Zeek vivo: deploy ANTES del nmap (conn.log nace ~T0, windowing por construccion) ---
vagrant ssh zeek -c "sudo $ZEEKCTL deploy" || die "zeekctl deploy fallo"
echo "-- Disparo MITRE (nmap -A) desde client contra defender --"
vagrant ssh client -c "sudo nmap -A 192.168.100.1" || die "nmap fallo"
echo "-- Drenaje 45s --"; sleep 45
# --- Zeek: cosechar conn.log del spool MIENTRAS corre, antes del stop (que lo archiva) ---
vagrant ssh zeek -c "sudo cp $ZEEK_SPOOL/conn.log $LAB/zeek-$STAMP.conn.log && sudo chmod 644 $LAB/zeek-$STAMP.conn.log" || die "no hay conn.log en el spool (zeek no vio trafico en la ventana?)"
vagrant ssh zeek -c "sudo $ZEEKCTL stop"

# 3) Oro de aRGus: bronce de la ventana del ataque (mtime > T0), convertido con la clave real
vagrant ssh defender -c "cat \$(find /vagrant/logs/correlation -name 'argus-*.csv' -newer $LAB/mitre-t0-$STAMP.marker | sort) > $LAB/argus-$STAMP.bronce.csv"
vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY ./bronze_to_gold_converter $LAB/argus-$STAMP.bronce.csv $LAB/argus-$STAMP.avro $LAB/argus-$STAMP.parquet" | tee /tmp/argus-conv.log
grep -q "descartadas: 0" /tmp/argus-conv.log || die "aRGus: descartadas>0 -> la clave no caso (¿pipeline reiniciado? ¿rotacion?)"

# 4) Oro de Suricata: adapter alert-only sobre el eve.json vivo (clave de juguete, el loader no verifica HMAC)
vagrant ssh suricata -c "sudo cp /var/log/suricata/eve.json $LAB/eve-$STAMP.json && sudo chmod 644 $LAB/eve-$STAMP.json"
vagrant ssh suricata -c "python3 -c \"import json; json.dump({'base_dir':'$LAB','node_id':'cpp_sniffer_v33_day12','input_path':'logs/lab/eve-$STAMP.json','hmac_key_env':'ARGUS_BRONZE_HMAC_KEY_HEX'}, open('$LAB/suri-adapter-$STAMP.json','w'))\""
vagrant ssh suricata -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$TOY_KEY $ADAPTER $LAB/suri-adapter-$STAMP.json"
SURI_CSV=$(vagrant ssh suricata -c "ls -t $LAB/suricata-*.csv | head -1" 2>/dev/null | tr -d '\r')
vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$TOY_KEY ./bronze_to_gold_converter $SURI_CSV $LAB/suricata-$STAMP.avro $LAB/suricata-$STAMP.parquet"


# 4b) Oro de Zeek: conn.log de la ventana (ya cosechado) -> adapter (toy key inline) -> converter
vagrant ssh zeek -c "python3 -c \"import json; json.dump({'base_dir':'$LAB','node_id':'cpp_sniffer_v33_day12','input_path':'logs/lab/zeek-$STAMP.conn.log','hmac_key_env':'ARGUS_BRONZE_HMAC_KEY_HEX'}, open('$LAB/zeek-adapter-$STAMP.json','w'))\""
vagrant ssh zeek -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$TOY_KEY $ZEEK_ADAPTER $LAB/zeek-adapter-$STAMP.json"
ZEEK_CSV=$(vagrant ssh zeek -c "ls -t $LAB/zeek-*.csv | head -1" 2>/dev/null | tr -d '\r')
vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$TOY_KEY ./bronze_to_gold_converter $ZEEK_CSV $LAB/zeek-$STAMP.avro $LAB/zeek-$STAMP.parquet"
# 5) Kuzu fresca + carga de los dos oros + poblador CORRELATES_FLOW
vagrant ssh defender -c "mkdir -p /vagrant/logs/day234-kuzu"
vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/argus-$STAMP.parquet $KUZU $SCHEMA"
vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/suricata-$STAMP.parquet $KUZU $SCHEMA"
vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/zeek-$STAMP.parquet $KUZU $SCHEMA"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (a:NetworkFlow),(b:NetworkFlow) WHERE a.community_id=b.community_id AND a.flow_uid<b.flow_uid MERGE (a)-[e:CORRELATES_FLOW]->(b) ON CREATE SET e.community_id=a.community_id, e.method='community_id', e.confidence=1.0\""

# 6) Veredicto del dia
echo ""; echo "======== MITRE -> GRAFO ($STAMP) ========"
echo "-- sensores en el grafo --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (e:TelemetryEvent) RETURN e.source_sensor, count(*)\""
echo "-- invariante (debe ser 0) --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (a:NetworkFlow)-[e:CORRELATES_FLOW]->(b:NetworkFlow) WHERE a.community_id<>b.community_id RETURN count(*)\""
echo "-- flujos corroborados cross-sensor (EL TITULAR) --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (ea:TelemetryEvent)-[:TELEMETRY_ABOUT]->(a:NetworkFlow)-[e:CORRELATES_FLOW]-(b:NetworkFlow)<-[:TELEMETRY_ABOUT]-(eb:TelemetryEvent) WHERE ea.source_sensor<>eb.source_sensor RETURN count(DISTINCT e.community_id)\""
echo "BD: $KUZU"; echo "========================================="