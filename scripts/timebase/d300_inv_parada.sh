#!/usr/bin/env bash
# DAY300: inventario para el patcher de parada ordenada (solo lectura, git grep).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "ring_consumer.hpp: bandera, cvs, intervalos"
git grep -n -e "should_stop_" -e "_cv_" -e "stats_interval_seconds_" -e "RANSOMWARE_EXTRACTION_INTERVAL_SEC" -e "#include <condition_variable>" -- sniffer/include/ring_consumer.hpp
sec "shutdown_ransomware_detection"
git grep -n -A 25 "void RingBufferConsumer::shutdown_ransomware_detection" -- sniffer/src/userspace/ring_consumer.cpp
sec "initialize_ransomware_detection"
git grep -n -A 22 "bool RingBufferConsumer::initialize_ransomware_detection" -- sniffer/src/userspace/ring_consumer.cpp
sec "linea 1683 (ransomware_enabled_ = false) con contexto"
git grep -n -B 15 -A 3 "^    ransomware_enabled_ = false;" -- sniffer/src/userspace/ring_consumer.cpp
sec "ransomware_feature_processor.hpp: miembros"
git grep -n -e "running_" -e "extraction_interval_seconds_" -e "std::thread" -e "#include" -e "RansomwareFeatureProcessor(" -- sniffer/include/ransomware_feature_processor.hpp
sec "bucle de extraccion"
git grep -n -B 6 -A 6 "sleep_for(std::chrono::seconds(extraction_interval_seconds_))" -- sniffer/src/userspace/ransomware_feature_processor.cpp
sec "clase EtcdClient del sniffer (propia o la libreria?)"
git grep -n "class EtcdClient" -- sniffer etcd-client
sec "etcd_client.cpp: includes"
git grep -n "#include" -- etcd-client/src/etcd_client.cpp
sec "etcd_client.cpp: miembros del heartbeat"
git grep -n -B 3 -A 6 "std::atomic<bool> heartbeat_running_" -- etcd-client/src/etcd_client.cpp
sec "etcd_client.cpp: parada del heartbeat"
git grep -n -B 6 -A 10 "if (heartbeat_running_.exchange(false))" -- etcd-client/src/etcd_client.cpp
sec "config_manager.cpp: lectura de monitoring"
git grep -n -B 4 -A 12 "monitoring.stats_interval_seconds =" -- sniffer/src/userspace/config_manager.cpp
sec "config_manager.cpp: patron [CONFIG-DEFAULT] existente"
git grep -n "CONFIG-DEFAULT" -- sniffer/src/userspace/config_manager.cpp
sec "sniffer.json: bloque monitoring"
git grep -n -B 4 -A 6 "\"stats_interval_seconds\"" -- sniffer/config/sniffer.json
