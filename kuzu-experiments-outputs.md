(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % make correlation-engine-smoke-matrix
╔══════════════════════════════════════════════╗
║  Building seed-client...                     ║
╚══════════════════════════════════════════════╝
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Found nlohmann_json: /usr/share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake (found suitable version "3.11.2", minimum required is "3.9")
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/libs/seed-client/build
[ 12%] Building CXX object CMakeFiles/seed_client.dir/src/seed_client.cpp.o
[ 25%] Linking CXX shared library libseed_client.so
[ 25%] Built target seed_client
[ 37%] Building CXX object CMakeFiles/test_seed_client_traversal.dir/tests/test_seed_client_traversal.cpp.o
[ 50%] Building CXX object CMakeFiles/test_perms_seed.dir/tests/test_perms_seed.cpp.o
[ 62%] Building CXX object CMakeFiles/test_seed_client.dir/tests/test_seed_client.cpp.o
[ 75%] Linking CXX executable test_perms_seed
[ 75%] Built target test_perms_seed
[ 87%] Linking CXX executable test_seed_client_traversal
[ 87%] Built target test_seed_client_traversal
[100%] Linking CXX executable test_seed_client
[100%] Built target test_seed_client
[ 25%] Built target seed_client
[ 50%] Built target test_seed_client
[ 75%] Built target test_perms_seed
[100%] Built target test_seed_client_traversal
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libseed_client.so.1.0.0
-- Up-to-date: /usr/local/lib/libseed_client.so.1
-- Up-to-date: /usr/local/lib/libseed_client.so
-- Up-to-date: /usr/local/include/seed_client
-- Up-to-date: /usr/local/include/seed_client/seed_client.hpp
✅ seed-client instalado

╔════════════════════════════════════════════════════════════╗
║  🔨 Building crypto-transport Library                     ║
╚════════════════════════════════════════════════════════════╝

-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags (from Makefile):
-- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
-- libsodium lib:     /usr/local/lib/libsodium.so
-- libsodium include: /usr/local/include
-- Checking for module 'liblz4'
--   Found liblz4, version 1.9.4
-- libseed_client: /usr/local/lib/libseed_client.so
-- ========================================
-- crypto-transport Tests Configuration
-- ========================================
-- Test framework: Google Test
-- Tests: test_crypto, test_compression, test_integration, test_crypto_transport
-- ========================================
-- ========================================
-- crypto-transport Tests Configuration
-- ========================================
-- Test framework: Google Test
-- Tests: test_crypto, test_compression, test_integration
-- ========================================
-- ========================================
-- crypto-transport Library Configuration
-- ========================================
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags:
-- libsodium:
-- LZ4: 1.9.4
-- ========================================
-- Public Headers:
--   - include/crypto_transport/crypto.hpp
--   - include/crypto_transport/compression.hpp
--   - include/crypto_transport/utils.hpp
--   - include/crypto_transport/crypto_manager.hpp
--   - include/crypto_transport/transport.hpp
--   - include/crypto_transport/contexts.hpp
-- ========================================
-- Install destinations:
--   Library: /usr/local/lib
--   Headers: /usr/local/include/crypto_transport
--
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/crypto-transport/build
[  6%] Building CXX object CMakeFiles/crypto_transport.dir/src/compression.cpp.o
[ 20%] Building CXX object CMakeFiles/crypto_transport.dir/src/transport.cpp.o
[ 26%] Building CXX object CMakeFiles/crypto_transport.dir/src/crypto.cpp.o
[ 26%] Building CXX object CMakeFiles/crypto_transport.dir/src/utils.cpp.o
[ 33%] Linking CXX shared library libcrypto_transport.so
[ 33%] Built target crypto_transport
[ 40%] Building CXX object tests/CMakeFiles/test_integration.dir/test_integration.cpp.o
[ 53%] Building CXX object tests/CMakeFiles/test_crypto.dir/test_crypto.cpp.o
[ 53%] Building CXX object tests/CMakeFiles/test_compression.dir/test_compression.cpp.o
[ 60%] Building CXX object tests/CMakeFiles/test_crypto_transport.dir/test_crypto_transport.cpp.o
[ 66%] Linking CXX executable test_crypto
[ 73%] Linking CXX executable test_compression
[ 73%] Built target test_compression
[ 73%] Built target test_crypto
[ 80%] Building CXX object tests/CMakeFiles/test_integ_contexts.dir/test_integ_contexts.cpp.o
[ 86%] Linking CXX executable test_integration
[ 86%] Built target test_integration
[ 93%] Linking CXX executable test_crypto_transport
/usr/bin/ld: aviso: libsodium.so.26, necesario para ../libcrypto_transport.so.1.0.0, podría entrar en conflicto con libsodium.so.23
[ 93%] Built target test_crypto_transport
[100%] Linking CXX executable test_integ_contexts
/usr/bin/ld: aviso: libsodium.so.26, necesario para ../libcrypto_transport.so.1.0.0, podría entrar en conflicto con libsodium.so.23
[100%] Built target test_integ_contexts
Installing system-wide...
[ 33%] Built target crypto_transport
[ 46%] Built target test_crypto
[ 60%] Built target test_compression
[ 73%] Built target test_integration
[ 86%] Built target test_crypto_transport
[100%] Built target test_integ_contexts
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libcrypto_transport.so.1.0.0
-- Up-to-date: /usr/local/lib/libcrypto_transport.so.1
-- Set runtime path of "/usr/local/lib/libcrypto_transport.so.1.0.0" to ""
-- Up-to-date: /usr/local/lib/libcrypto_transport.so
-- Up-to-date: /usr/local/include/crypto_transport/crypto.hpp
-- Up-to-date: /usr/local/include/crypto_transport/compression.hpp
-- Up-to-date: /usr/local/include/crypto_transport/utils.hpp
-- Up-to-date: /usr/local/include/crypto_transport/crypto_manager.hpp
-- Up-to-date: /usr/local/include/crypto_transport/transport.hpp
-- Up-to-date: /usr/local/include/crypto_transport/contexts.hpp

✅ crypto-transport installed to /usr/local/lib
lrwxrwxrwx 1 root root  24 jun 12 05:33 /usr/local/lib/libcrypto_transport.so -> libcrypto_transport.so.1
lrwxrwxrwx 1 root root  28 jun 12 05:33 /usr/local/lib/libcrypto_transport.so.1 -> libcrypto_transport.so.1.0.0
-rw-r--r-- 1 root root 52K jun 12 09:08 /usr/local/lib/libcrypto_transport.so.1.0.0

╔════════════════════════════════════════════════════════════╗
║  🔨 Building vault-client Library (ADR-044)               ║
╚════════════════════════════════════════════════════════════╝
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
-- Checking for module 'libsodium'
--   Found libsodium, version 1.0.19
-- Found CURL: /usr/lib/x86_64-linux-gnu/libcurl.so (found version "7.88.1")  
-- Found OpenSSL: /usr/lib/x86_64-linux-gnu/libcrypto.so (found version "3.0.20")  
-- Checking for module 'libzmq'
--   Found libzmq, version 4.3.4
-- ╔══════════════════════════════════════════════╗
-- ║  crypto_provider — ADR-044 DAY 151           ║
-- ╠══════════════════════════════════════════════╣
-- ║  Provider: SeedFileProvider (community)      ║
-- ╚══════════════════════════════════════════════╝
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/common/build
[  4%] Building CXX object CMakeFiles/test_wire_protocol.dir/tests/test_wire_protocol.cpp.o
[  4%] Building CXX object CMakeFiles/ntp_utils.dir/ntp_health_check.cpp.o
[  6%] Building CXX object CMakeFiles/test_crypto_deriver.dir/tests/test_crypto_deriver.cpp.o
[  8%] Building CXX object CMakeFiles/vault_client.dir/vault_client.cpp.o
[ 10%] Linking CXX static library libntp_utils.a
[ 10%] Built target ntp_utils
[ 12%] Building CXX object CMakeFiles/test_crypto_deriver.dir/crypto_deriver.cpp.o
[ 14%] Building CXX object CMakeFiles/vault_client.dir/crypto_deriver.cpp.o
[ 16%] Linking CXX executable test_wire_protocol
[ 16%] Built target test_wire_protocol
[ 18%] Building CXX object CMakeFiles/vault_client.dir/etcd_registrar.cpp.o
[ 20%] Building CXX object CMakeFiles/vault_client.dir/vault_transport.cpp.o
[ 22%] Linking CXX executable test_crypto_deriver
[ 24%] Building CXX object CMakeFiles/vault_client.dir/cache_manager.cpp.o
[ 24%] Built target test_crypto_deriver
[ 26%] Linking CXX shared library libvault_client.so
[ 26%] Built target vault_client
[ 28%] Building CXX object CMakeFiles/test_vault_transport.dir/tests/test_vault_transport.cpp.o
[ 30%] Building CXX object CMakeFiles/crypto_provider.dir/crypto_provider.cpp.o
[ 32%] Building CXX object CMakeFiles/test_etcd_registrar.dir/tests/test_etcd_registrar.cpp.o
[ 34%] Building CXX object CMakeFiles/test_vault_client.dir/tests/test_vault_client.cpp.o
[ 36%] Building CXX object CMakeFiles/test_etcd_registrar.dir/etcd_registrar.cpp.o
[ 38%] Building CXX object CMakeFiles/test_vault_transport.dir/vault_transport.cpp.o
[ 40%] Building CXX object CMakeFiles/crypto_provider.dir/seed_file_provider.cpp.o
[ 42%] Linking CXX executable test_vault_client
[ 42%] Built target test_vault_client
[ 44%] Building CXX object CMakeFiles/test_cache_manager.dir/tests/test_cache_manager.cpp.o
[ 46%] Linking CXX executable test_etcd_registrar
[ 46%] Built target test_etcd_registrar
[ 48%] Building CXX object CMakeFiles/test_crypto_epoch_coordinator.dir/tests/test_crypto_epoch_coordinator.cpp.o
[ 51%] Linking CXX executable test_vault_transport
[ 51%] Built target test_vault_transport
[ 53%] Building CXX object CMakeFiles/crypto_provider.dir/autonomy_publisher.cpp.o
[ 55%] Building CXX object CMakeFiles/test_e2e_rotation.dir/tests/test_e2e_rotation.cpp.o
[ 57%] Building CXX object CMakeFiles/test_cache_manager.dir/cache_manager.cpp.o
[ 59%] Building CXX object CMakeFiles/crypto_provider.dir/http_etcd_registrar.cpp.o
[ 61%] Linking CXX executable test_cache_manager
[ 61%] Built target test_cache_manager
[ 63%] Building CXX object CMakeFiles/test_e2e_rotation.dir/crypto_epoch_coordinator.cpp.o
[ 65%] Building CXX object CMakeFiles/test_e2e_rotation.dir/http_etcd_registrar.cpp.o
[ 67%] Building CXX object CMakeFiles/test_crypto_epoch_coordinator.dir/crypto_epoch_coordinator.cpp.o
[ 69%] Building CXX object CMakeFiles/test_crypto_epoch_coordinator.dir/http_etcd_registrar.cpp.o
[ 71%] Building CXX object CMakeFiles/crypto_provider.dir/crypto_epoch_coordinator.cpp.o
[ 73%] Linking CXX shared library libcrypto_provider.so
[ 75%] Linking CXX executable test_e2e_rotation
/usr/bin/ld: aviso: libsodium.so.26, necesario para /usr/local/lib/libcrypto_transport.so, podría entrar en conflicto con libsodium.so.23
[ 75%] Built target test_e2e_rotation
[ 75%] Built target crypto_provider
[ 77%] Building CXX object CMakeFiles/test_crypto_provider_community.dir/tests/test_crypto_provider.cpp.o
[ 79%] Building CXX object CMakeFiles/test_autonomy_publisher.dir/tests/test_autonomy_publisher.cpp.o
[ 81%] Building CXX object CMakeFiles/test_crypto_autonomy.dir/tests/test_crypto_autonomy.cpp.o
[ 83%] Building CXX object CMakeFiles/test_autonomy_publisher.dir/autonomy_publisher.cpp.o
[ 85%] Linking CXX executable test_crypto_provider_community
[ 87%] Linking CXX executable test_crypto_autonomy
[ 87%] Built target test_crypto_autonomy
[ 87%] Built target test_crypto_provider_community
[ 89%] Building CXX object CMakeFiles/test_autonomy_state_writer.dir/tests/test_autonomy_state_writer.cpp.o
[ 91%] Building CXX object CMakeFiles/test_crypto_provider_handle.dir/tests/test_crypto_provider_handle.cpp.o
[ 93%] Linking CXX executable test_autonomy_publisher
[ 93%] Built target test_autonomy_publisher
[ 95%] Linking CXX executable test_crypto_provider_handle
[ 95%] Built target test_crypto_provider_handle
[ 97%] Linking CXX executable test_autonomy_state_writer
[ 97%] Built target test_autonomy_state_writer
[100%] Linking CXX executable test_crypto_epoch_coordinator
[100%] Built target test_crypto_epoch_coordinator
[ 12%] Built target vault_client
[ 24%] Built target crypto_provider
[ 28%] Built target ntp_utils
[ 34%] Built target test_crypto_deriver
[ 40%] Built target test_etcd_registrar
[ 44%] Built target test_vault_client
[ 48%] Built target test_crypto_provider_community
[ 53%] Built target test_crypto_autonomy
[ 59%] Built target test_autonomy_publisher
[ 65%] Built target test_vault_transport
[ 71%] Built target test_cache_manager
[ 75%] Built target test_autonomy_state_writer
[ 79%] Built target test_crypto_provider_handle
[ 83%] Built target test_wire_protocol
[ 91%] Built target test_crypto_epoch_coordinator
[100%] Built target test_e2e_rotation
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libvault_client.so.1.0.0
-- Up-to-date: /usr/local/lib/libvault_client.so.1
-- Up-to-date: /usr/local/lib/libvault_client.so
-- Installing: /usr/local/lib/libcrypto_provider.so.1.0.0
-- Up-to-date: /usr/local/lib/libcrypto_provider.so.1
-- Set runtime path of "/usr/local/lib/libcrypto_provider.so.1.0.0" to ""
-- Up-to-date: /usr/local/lib/libcrypto_provider.so
-- Up-to-date: /usr/local/include/vault_client/vault_client.h
-- Up-to-date: /usr/local/include/vault_client/vault_types.h
-- Up-to-date: /usr/local/include/vault_client/vault_transport.h
-- Up-to-date: /usr/local/include/vault_client/cache_manager.h
-- Up-to-date: /usr/local/include/vault_client/crypto_provider.h
-- Up-to-date: /usr/local/include/vault_client/crypto_provider_handle.hpp
-- Up-to-date: /usr/local/include/vault_client/autonomy_publisher.h
-- Up-to-date: /usr/local/include/vault_client/crypto_autonomy.h
-- Up-to-date: /usr/local/include/vault_client/crypto_deriver.h
-- Up-to-date: /usr/local/include/vault_client/etcd_registrar.h
-- Up-to-date: /usr/local/include/vault_client/http_etcd_registrar.h
-- Up-to-date: /usr/local/include/vault_client/crypto_epoch_coordinator.h
-- Up-to-date: /usr/local/include/vault_client/seed_file_provider.h
-- Up-to-date: /usr/local/include/vault_client/autonomy_state_writer.h
-- Up-to-date: /usr/local/include/vault_client/reason_codes.hpp
-- Up-to-date: /usr/local/include/vault_client/sentinel.hpp
-- Installing: /usr/local/lib/libntp_utils.a
-- Up-to-date: /usr/local/include/vault_client/ntp_health_check.hpp
✅ vault-client instalado en /usr/local/lib
╔════════════════════════════════════════════════════════════╗
║  🔨 Building correlation-engine [ADR-048 F2 scaffold]     ║
╚════════════════════════════════════════════════════════════╝
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
-- Checking for module 'libsodium'
--   Found libsodium, version 1.0.19
-- libsodium: 1.0.19
-- Found OpenSSL: /usr/lib/x86_64-linux-gnu/libcrypto.so (found version "3.0.20")  
-- nlohmann/json: 3.11.2
-- libkuzu: /usr/local/lib/libkuzu.so
-- Performing Test CMAKE_HAVE_LIBC_PTHREAD
-- Performing Test CMAKE_HAVE_LIBC_PTHREAD - Success
-- Found Threads: TRUE  
-- Found GTest: /usr/lib/x86_64-linux-gnu/cmake/GTest/GTestConfig.cmake (found version "1.12.1")  
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/correlation-engine/build
[ 11%] Building CXX object CMakeFiles/correlation_engine.dir/src/kuzu_graph_sink.cpp.o
[ 11%] Building CXX object CMakeFiles/correlation_engine.dir/src/correlation_reader.cpp.o
[ 16%] Building CXX object CMakeFiles/correlation_engine.dir/src/logging_graph_sink.cpp.o
[ 22%] Linking CXX static library libcorrelation_engine.a
[ 22%] Built target correlation_engine
[ 27%] Building CXX object CMakeFiles/test_flow_uid.dir/tests/test_flow_uid.cpp.o
[ 33%] Building CXX object CMakeFiles/correlation_engine_bin.dir/src/main.cpp.o
[ 38%] Building CXX object CMakeFiles/test_graph_sink_loop.dir/tests/test_graph_sink_loop.cpp.o
[ 44%] Building CXX object CMakeFiles/test_correlation_reader.dir/tests/test_correlation_reader.cpp.o
[ 50%] Linking CXX executable test_correlation_reader
[ 50%] Built target test_correlation_reader
[ 55%] Building CXX object CMakeFiles/test_cypher_injection.dir/tests/test_cypher_injection.cpp.o
[ 61%] Linking CXX executable test_graph_sink_loop
[ 66%] Linking CXX executable correlation_engine_bin
[ 72%] Linking CXX executable test_cypher_injection
[ 72%] Built target test_graph_sink_loop
[ 77%] Linking CXX executable test_flow_uid
[ 77%] Built target test_cypher_injection
[ 83%] Building CXX object CMakeFiles/test_kuzu_graph_sink.dir/tests/test_kuzu_graph_sink.cpp.o
[ 88%] Building CXX object CMakeFiles/kuzu_concurrency_smoke.dir/experiments/kuzu_concurrency_smoke.cpp.o
[ 88%] Built target correlation_engine_bin
[ 88%] Built target test_flow_uid
[ 94%] Linking CXX executable kuzu_concurrency_smoke
[ 94%] Built target kuzu_concurrency_smoke
[100%] Linking CXX executable test_kuzu_graph_sink
[100%] Built target test_kuzu_graph_sink
✅ correlation-engine built
── MATRIZ smoke Kuzu (decision fsync / multi-writer) ──
### run1: 1 writer, auto-commit (baseline fsync-por-upsert)
=== KUZU UPSERT SMOKE — ADR-057 Fase 0 (DAY 182) ===
db_path: /tmp/argus_kuzu_smoke.kuzu  (fs NATIVO del guest, NO vboxsf)
config : dur=5s writers=1 batch=1(rows/query) writes_per_read=100 init_nodes=100000 (~100:1)

[C] Monotonia NTP: muestras=2000000 retrocesos=0 max_ns=0 -> monotono en reposo

[B] Lock de fichero (Kuzu: lock de PROCESO):
(b1) 2o PROCESO: RECHAZADO (esperado) (exit=2)
(b2) 2o Database in-process: ABRIO -> footgun (un Database, N Connections)
-> CONFIRMA: lock CROSS-PROCESO. Multi-proceso => servicio in-process unico.

graph inicial: 100000 nodos en 7.69s (UNWIND; prod = COPY FROM)

[A] RIADA UPSERTS: 1 writers (batch=1 rows/query) + 1 reader (ratio 100:1):
UPSERTS commit=819 (164/s)  errores=0
query()-lat escritura: p50=6015866ns p99=8378146ns p999=10432523ns mean=6095991ns (819 queries)
por upsert (amortizado = lat/batch): p50=6015866ns mean=6095991ns
reads          =8 (2/s)  errores=0  ratio_real = 102:1
lat lectura baseline: p50=2380717ns p99=3946046ns
lat lectura carga   : p50=2996341ns p99=6243701ns
contencion          : p50 x1.26  p99 x1.58
upsert real (no insert): nodos==init_nodes (100000==100000) OK
pico de memoria (maxRSS): 631.7 MB

VEREDICTO [A]: upsert consistente; compara UPSERTS/s batch=1 vs batch=K (UNWIND) para la decision Vela.

real    0m13,757s
user    0m10,130s
sys     0m3,313s
### run2: 1 writer, batched (¿muere el fsync?)
=== KUZU UPSERT SMOKE — ADR-057 Fase 0 (DAY 182) ===
db_path: /tmp/argus_kuzu_smoke.kuzu  (fs NATIVO del guest, NO vboxsf)
config : dur=5s writers=1 batch=1000(rows/query) writes_per_read=100 init_nodes=100000 (~100:1)

[C] Monotonia NTP: muestras=2000000 retrocesos=0 max_ns=0 -> monotono en reposo

[B] Lock de fichero (Kuzu: lock de PROCESO):
(b1) 2o PROCESO: RECHAZADO (esperado) (exit=2)
(b2) 2o Database in-process: ABRIO -> footgun (un Database, N Connections)
-> CONFIRMA: lock CROSS-PROCESO. Multi-proceso => servicio in-process unico.

graph inicial: 100000 nodos en 7.19s (UNWIND; prod = COPY FROM)

[A] RIADA UPSERTS: 1 writers (batch=1000 rows/query) + 1 reader (ratio 100:1):
UPSERTS commit=50000 (10000/s)  errores=0
query()-lat escritura: p50=93969611ns p99=117311606ns p999=117311606ns mean=99050493ns (50 queries)
por upsert (amortizado = lat/batch): p50=93970ns mean=99050ns
reads          =49 (10/s)  errores=0  ratio_real = 1020:1
lat lectura baseline: p50=2206503ns p99=3878034ns
lat lectura carga   : p50=2557373ns p99=10806657ns
contencion          : p50 x1.16  p99 x2.79
upsert real (no insert): nodos==init_nodes (100000==100000) OK
pico de memoria (maxRSS): 682.0 MB

VEREDICTO [A]: upsert consistente; compara UPSERTS/s batch=1 vs batch=K (UNWIND) para la decision Vela.

real    0m13,063s
user    0m12,146s
sys     0m1,729s
### run3: 4 writers, batched (¿ayuda multi-writer? Kuzu=1 write-tx)
=== KUZU UPSERT SMOKE — ADR-057 Fase 0 (DAY 182) ===
db_path: /tmp/argus_kuzu_smoke.kuzu  (fs NATIVO del guest, NO vboxsf)
config : dur=5s writers=4 batch=1000(rows/query) writes_per_read=100 init_nodes=100000 (~100:1)

[C] Monotonia NTP: muestras=2000000 retrocesos=0 max_ns=0 -> monotono en reposo

[B] Lock de fichero (Kuzu: lock de PROCESO):
(b1) 2o PROCESO: RECHAZADO (esperado) (exit=2)
(b2) 2o Database in-process: ABRIO -> footgun (un Database, N Connections)
-> CONFIRMA: lock CROSS-PROCESO. Multi-proceso => servicio in-process unico.

graph inicial: 100000 nodos en 6.25s (UNWIND; prod = COPY FROM)

[A] RIADA UPSERTS: 4 writers (batch=1000 rows/query) + 1 reader (ratio 100:1):
UPSERTS commit=69000 (13800/s)  errores=373000
rechazos por conflicto write-tx (ESPERADO con N>1; Kuzu=1 write-tx): 373000  (ejemplo: Cannot start a new write transaction in the system. Only one write transaction at a time is allowed in the system.)
query()-lat escritura: p50=96829170ns p99=284359924ns p999=284359924ns mean=103703704ns (69 queries)
por upsert (amortizado = lat/batch): p50=96829ns mean=103704ns
reads          =66 (13/s)  errores=0  ratio_real = 1045:1
lat lectura baseline: p50=1862081ns p99=3085482ns
lat lectura carga   : p50=2637459ns p99=35088393ns
contencion          : p50 x1.42  p99 x11.37
upsert real (no insert): nodos==init_nodes (100000==100000) OK
pico de memoria (maxRSS): 821.8 MB

VEREDICTO [A]: consistente; multi-writer NO escala (rechazos por single write-tx). UNWIND+1 writer es el patron.

real    0m12,119s
user    0m22,926s
sys     0m2,760s
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % 