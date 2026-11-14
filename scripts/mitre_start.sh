#!/usr/bin/env bash
# scripts/mitre_start.sh — DAY 234. Automatiza el camino MITRE -> grafo de DAY 233.
# `make mitre-start` deja aristas cross-sensor (aRGus<->Suricata) en Kuzu con datos
# DEL DIA, cero comandos manuales. Requiere `make pipeline-start` antes.
# Se ejecuta en el HOST; trabaja en los guests via vagrant ssh. A. Roman + Claude.
# [MITRE-VENTANA-D323] Una sola ventana [T0, T1] con el reloj del defender (el de todo el lab) para los tres sensores:
# cada bronce se filtra a la ventana (scripts/mitre_ventana.py) antes del converter, y se cuentan las filas del ataque
# (ATACANTE <-> VICTIMA) para el veredicto. Zeek se cosecha tras el stop y su archivado, también lo que una rotación
# horaria archivó a mitad de la corrida (scripts/mitre_zeek_cosecha.sh). Ningún paso falla en silencio: adapter,
# converter (sin filas = fallo), loader y consultas comprueban su resultado. Medido DAY323: Suricata sumaba eve.json de
# otras corridas, la rotación de las 10:00 dejó a Zeek en 8 filas de etcd y NTP, y un FATAL del loader acabó en rc 0.
set -uo pipefail
CE="/vagrant/correlation-engine/build"; SCHEMA="/vagrant/correlation-engine/schema/schema.cypher"
LAB="/vagrant/logs/lab"; ADAPTER="/vagrant/suricata-adapter/build-suricata/suricata_adapter"
ZEEKCTL="/opt/zeek/bin/zeekctl"
ZEEK_ADAPTER="/vagrant/zeek-adapter/build-zeek/zeek_adapter"
STAMP="$(date -u +%Y%m%d-%H%M%S)"; KUZU="/vagrant/logs/day234-kuzu/mitre-$STAMP.kuzu"
ATACANTE="192.168.100.50"; VICTIMA="192.168.100.1"   # nmap -A del client (.50) contra el defender (.1)
HLAB="logs/lab"   # el mismo $LAB visto desde el host (este script corre en la raíz del repo)
# Espera máxima al archivado de `zeekctl stop`. Medido DAY323: 121 s para dos ficheros conn (archive-log en serie,
# ~55 s cada uno); 300 s deja margen para una corrida que cruce una rotación. Entero > 0, en segundos.
ZEEK_ARCHIVO_MAX_S="${MITRE_ZEEK_ARCHIVO_MAX_S:-300}"
die(){ echo "X $*" >&2; exit 1; }
[ -f Vagrantfile ] && [ -d "$HLAB" ] || die "hay que lanzarlo desde la raíz del repo (falta Vagrantfile o $HLAB)"
echo "$ZEEK_ARCHIVO_MAX_S" | grep -Eq '^[1-9][0-9]*$' || die "MITRE_ZEEK_ARCHIVO_MAX_S='$ZEEK_ARCHIVO_MAX_S': entero > 0 (segundos)"
echo "[MITRE-VENTANA] MITRE_ZEEK_ARCHIVO_MAX_S=$ZEEK_ARCHIVO_MAX_S s (por defecto 300)"

hora_defender(){ vagrant ssh defender -c "date +%s.%N" 2>/dev/null | tr -d '\r' | grep -E '^[0-9]+\.[0-9]+$' | tail -n 1; }
salida_adapter(){ tr -d '\r' < "$1" | sed -n 's/^ *salida: *//p' | tail -n 1; }
ventana(){ # sensor bronce_entrada bronce_salida (rutas de la VM, en $LAB)
  python3 -I scripts/mitre_ventana.py --sensor "$1" --desde "$T0" --hasta "$T1" --atacante "$ATACANTE" \
    --victima "$VICTIMA" "$HLAB/$(basename "$2")" "$HLAB/$(basename "$3")"
  local rc=$?; [ "$rc" -eq 0 ] || die "$1: el bronce no tiene filas en la ventana [T0, T1] o no se puede leer (rc=$rc)"
}
convertir(){ # sensor bronce_ventana (ruta de la VM)
  vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY ./bronze_to_gold_converter $2 $LAB/$1-$STAMP.avro $LAB/$1-$STAMP.parquet" | tee "/tmp/$1-conv.log" \
    || die "$1: bronze_to_gold_converter rc!=0"
  grep -q "descartadas: 0" "/tmp/$1-conv.log" || die "$1: descartes HMAC>0 -> la clave no casó (adapter vs converter)"
  grep -q "^OK — " "/tmp/$1-conv.log" || die "$1: el converter no escribió el oro (¿Sin filas válidas?)"
}
cargar(){ # sensor
  vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/$1-$STAMP.parquet $KUZU $SCHEMA" | tee "/tmp/$1-kuzu.log" \
    || die "$1: parquet_to_kuzu_loader rc!=0"
  grep -q "materializadas en Kuzu" "/tmp/$1-kuzu.log" || die "$1: el loader no materializó filas en Kuzu"
}

echo ""
echo "##################################################################"
echo "#  ALERT  ##  HACK DE DESARROLLO — NO APTO PARA PRODUCCION  ##    #"
echo "#                                                                #"
echo "#  mitre-start saca la clave HMAC del etcd-server por mTLS con la #"
echo "#  identidad del converter (/secrets/valid/ml-detector) y se la   #"
echo "#  pasa al converter por variable de entorno.                     #"
echo "#  DEBT-BRONZE-KEY-PROVISIONING-001. Arreglo correcto (NO aqui):  #"
echo "#  converter y componentes DIRECTOS a Vault (auth/TLS/leases);    #"
echo "#  idealmente Jenkins exporta esta env var al crear la clave.     #"
echo "#  Quien mantenga el pipeline: hazlo a tu manera, pero hazlo.     #"
echo "##################################################################"
echo ""

# 1) Clave HMAC del bronce (el hack)
# [ETCD-CLIENTE-D316] E5: mTLS con la identidad del converter contra el etcd-server del bloque etcd de ml-detector
KEY=$(vagrant ssh defender -c "sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py ml-detector" 2>/dev/null | tr -d '\r')
[ ${#KEY} -eq 64 ] || die "clave HMAC no es 64 hex (len=${#KEY}). Diagnostico: vagrant ssh defender -c 'sudo python3 -I /vagrant/scripts/bronze_key/clave_bronce.py ml-detector'"
echo "OK clave HMAC en mano (64 hex, head ${KEY:0:8}...)"

# 2) T0 (reloj del defender), disparo MITRE (nmap -A: el que hace reaccionar a los TRES sensores), drenaje y T1
T0=$(hora_defender); [ -n "$T0" ] || die "no hay hora del defender para T0"
echo "[MITRE-VENTANA] T0=$T0 (reloj del defender)"
vagrant ssh defender -c "touch $LAB/mitre-t0-$STAMP.marker" || die "no se pudo crear la marca de T0"
vagrant ssh zeek -c "sudo $ZEEKCTL deploy" || die "zeekctl deploy fallo"
echo "-- Disparo MITRE (nmap -A) desde client ($ATACANTE) contra defender ($VICTIMA) --"
vagrant ssh client -c "sudo nmap -A $VICTIMA" || die "nmap fallo"
echo "-- Drenaje 45s --"; sleep 45
T1=$(hora_defender); [ -n "$T1" ] || die "no hay hora del defender para T1"
echo "[MITRE-VENTANA] T1=$T1 (reloj del defender)"
# --- Zeek: stop, esperar a su archivado y juntar los conn.log de la ventana (también los ya rotados)
vagrant ssh zeek -c "sudo bash /vagrant/scripts/mitre_zeek_cosecha.sh $T0 $T1 $LAB/zeek-$STAMP.conn.log $ZEEK_ARCHIVO_MAX_S" \
  || die "zeek: la cosecha del conn.log falló (ver [MITRE-ZEEK-COSECHA])"

# 3) Oro de aRGus: bronce escrito desde T0 (mtime > marca), filtrado a la ventana, convertido con la clave real
vagrant ssh defender -c "cat \$(find /vagrant/logs/correlation -name 'argus-*.csv' -newer $LAB/mitre-t0-$STAMP.marker | sort) > $LAB/argus-$STAMP.bronce.csv" \
  || die "aRGus: no se pudo juntar el bronce desde T0"
ventana argus "$LAB/argus-$STAMP.bronce.csv" "$LAB/argus-$STAMP.bronce-ventana"
convertir argus "$LAB/argus-$STAMP.bronce-ventana"

# 4) Oro de Suricata: adapter alert-only sobre el eve.json (y el rotado, si lo hay) -> bronce filtrado a la ventana
vagrant ssh suricata -c "sudo sh -c 'cat /var/log/suricata/eve.json.1 /var/log/suricata/eve.json 2>/dev/null > $LAB/eve-$STAMP.json; test -s $LAB/eve-$STAMP.json' && sudo chmod 644 $LAB/eve-$STAMP.json" \
  || die "suricata: no hay eve.json"
vagrant ssh suricata -c "python3 -c \"import json; json.dump({'base_dir':'$LAB','node_id':'cpp_sniffer_v33_day12','input_path':'logs/lab/eve-$STAMP.json','hmac_key_env':'ARGUS_BRONZE_HMAC_KEY_HEX'}, open('$LAB/suri-adapter-$STAMP.json','w'))\"" \
  || die "suricata: no se pudo escribir la configuración del adapter"
vagrant ssh suricata -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY $ADAPTER $LAB/suri-adapter-$STAMP.json" | tee /tmp/suri-adapter.log \
  || die "suricata: el adapter falló"
SURI_CSV=$(salida_adapter /tmp/suri-adapter.log); [ -n "$SURI_CSV" ] || die "suricata: el adapter no dijo su salida"
ventana suricata "$SURI_CSV" "$LAB/suricata-$STAMP.bronce-ventana"
convertir suricata "$LAB/suricata-$STAMP.bronce-ventana"

# 4b) Oro de Zeek: conn.log de la ventana (ya cosechado) -> adapter (clave real) -> bronce filtrado a la ventana
vagrant ssh zeek -c "python3 -c \"import json; json.dump({'base_dir':'$LAB','node_id':'cpp_sniffer_v33_day12','input_path':'logs/lab/zeek-$STAMP.conn.log','hmac_key_env':'ARGUS_BRONZE_HMAC_KEY_HEX'}, open('$LAB/zeek-adapter-$STAMP.json','w'))\"" \
  || die "zeek: no se pudo escribir la configuración del adapter"
vagrant ssh zeek -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$KEY $ZEEK_ADAPTER $LAB/zeek-adapter-$STAMP.json" | tee /tmp/zeek-adapter.log \
  || die "zeek: el adapter falló"
ZEEK_CSV=$(salida_adapter /tmp/zeek-adapter.log); [ -n "$ZEEK_CSV" ] || die "zeek: el adapter no dijo su salida"
ventana zeek "$ZEEK_CSV" "$LAB/zeek-$STAMP.bronce-ventana"
convertir zeek "$LAB/zeek-$STAMP.bronce-ventana"

# 5) Kuzu fresca + carga de los tres oros + poblador CORRELATES_FLOW
vagrant ssh defender -c "mkdir -p /vagrant/logs/day234-kuzu" || die "no se pudo crear el directorio de Kuzu"
cargar argus
cargar suricata
cargar zeek
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (a:NetworkFlow),(b:NetworkFlow) WHERE a.community_id=b.community_id AND a.flow_uid<b.flow_uid MERGE (a)-[e:CORRELATES_FLOW]->(b) ON CREATE SET e.community_id=a.community_id, e.method='community_id', e.confidence=1.0\"" \
  || die "kuzu_query: el poblador CORRELATES_FLOW falló"

# 6) Veredicto del dia
echo ""; echo "======== MITRE -> GRAFO ($STAMP) ========"
echo "-- sensores en el grafo --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (e:TelemetryEvent) RETURN e.source_sensor, count(*)\"" || die "kuzu_query: sensores"
echo "-- invariante (debe ser 0) --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (a:NetworkFlow)-[e:CORRELATES_FLOW]->(b:NetworkFlow) WHERE a.community_id<>b.community_id RETURN count(*)\"" || die "kuzu_query: invariante"
echo "-- flujos corroborados cross-sensor (EL TITULAR) --"
vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \"MATCH (ea:TelemetryEvent)-[:TELEMETRY_ABOUT]->(a:NetworkFlow)-[e:CORRELATES_FLOW]-(b:NetworkFlow)<-[:TELEMETRY_ABOUT]-(eb:TelemetryEvent) WHERE ea.source_sensor<>eb.source_sensor RETURN count(DISTINCT e.community_id)\"" || die "kuzu_query: corroborados"
echo "BD: $KUZU"; echo "========================================="
