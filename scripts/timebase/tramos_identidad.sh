#!/bin/bash
# [TIMEBASE-D296] identidad: sniffer_mld + mld_interno + mld_fw (medias) == media_ms ; cada max de tramo <= max_ms
grep -F 'sniffer_mld_media_ms' /vagrant/logs/lab/firewall-agent.log | tail -n "${1:-6}" | LC_ALL=C awk '
{
  for (i = 1; i <= NF; i++) { split($i, kv, "="); if (kv[2] != "") v[kv[1]] = kv[2] + 0 }
  s = v["sniffer_mld_media_ms"] + v["mld_interno_media_ms"] + v["mld_fw_media_ms"]
  d = s - v["media_ms"]; if (d < 0) d = -d
  okmax = (v["sniffer_mld_max_ms"] <= v["max_ms"] + 1e-3 && v["mld_interno_max_ms"] <= v["max_ms"] + 1e-3 && v["mld_fw_max_ms"] <= v["max_ms"] + 1e-3)
  an = v["sin_time_context"] + v["version"] + v["mono_cero"] + v["boot_id"] + v["futuro"] + v["retraso_otro_boot"] + v["retraso_negativo"] + v["retraso_absurdo"] + v["mld_sin_sello"] + v["mld_orden"]
  printf "n=%d total=%.3f/%.3f  sniffer_mld=%.3f/%.3f  mld_interno=%.3f/%.3f  mld_fw=%.3f/%.3f  (media/max ms)  |suma-total|=%.4f %s  max %s  anomalias=%d\n",
    v["n"], v["media_ms"], v["max_ms"], v["sniffer_mld_media_ms"], v["sniffer_mld_max_ms"], v["mld_interno_media_ms"], v["mld_interno_max_ms"],
    v["mld_fw_media_ms"], v["mld_fw_max_ms"], d, (d < 0.01 ? "OK" : "FALLO"), (okmax ? "OK" : "FALLO"), an
}'
