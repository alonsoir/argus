# DAY 159 — Prompt de Continuidad

## Contexto del proyecto
aRGus NDR — pipeline C++20 de seguridad open-source para infraestructura crítica.
Repo: github.com/alonsoir/argus | Paper: arXiv:2604.04952
Rama activa: `feature/day158-alerting-edge-sos` (NO mergeada a main aún)
Tag más reciente en main: `v0.9.2-day157`

## Estado al cierre de DAY 158

### ✅ Resuelto hoy
**DEBT-FIREWALL-HTTPLIB-ODR-001 CERRADA:**
- `alert_client.hpp` (header-only con `httplib.h`) estaba incluido en
  `batch_processor.hpp` como miembro directo `argus::AlertClient alert_client_`
- El firewall también enlaza con `libetcd_client.so` que compila su propia
  instancia de `httplib::ClientImpl` → ODR violation → SIGSEGV al arrancar
- Fix aplicado: `alert_client_` eliminado de `firewall-acl-agent` completamente
- Pipeline: **6/6 RUNNING sin SIGSEGV**

### ❌ TAREA 1 — PRIORITARIA
**DEBT-FIREWALL-CRYPTO-FORMAT-001 — P1:**

El firewall tiene `events_processed=0, events_dropped=N` (100% drop rate).

**Causa exacta:**
`firewall-acl-agent/src/api/zmq_subscriber.cpp` línea 450 usa la ruta antigua:
```cpp
auto key = crypto_transport::hex_to_bytes(config_.crypto_token);
data = crypto_transport::decrypt(data, key);
```
`config_.crypto_token` viene vacío porque `get_encryption_key()` está
**DEPRECATED desde DAY 98** (migración CryptoManager → CryptoTransport, ADR-013).

También `firewall-acl-agent/src/main.cpp` línea 713:
```cpp
zmq_config.crypto_token = etcd_client->get_crypto_seed();
```
Ambos puntos hay que migrar.

**Lo que SÍ funciona:**
- El seed correcto existe en `/etc/ml-defender/firewall-acl-agent/seed.bin`
- Es idéntico al de ml-detector (verificado con `cmp`)
- ml-detector cifra correctamente con CryptoTransport + seed.bin
- El firewall tiene el seed pero no lo usa

**Fix a aplicar:**
Migrar `zmq_subscriber.cpp` y `main.cpp` para usar `CryptoTransport` con
`seed.bin`, igual que hace ml-detector. Mismo patrón ADR-013 PHASE 2 DAY 98-99.

**Primer comando:**
```bash
grep -n "CryptoTransport\|seed\|decrypt\|zmq" ml-detector/src/zmq_handler.cpp | head -30
grep -n "crypto_token\|hex_to_bytes\|decrypt\|CryptoTransport\|seed" \
  firewall-acl-agent/src/api/zmq_subscriber.cpp \
  firewall-acl-agent/src/main.cpp | head -40
```

**Criterio de éxito:**
```
events_processed > 0, events_dropped = 0
```
En `logs/lab/firewall-agent.log` tras arrancar el pipeline.

### ❌ TAREA 2 — Tras fix crypto
**DEBT-EMECAS-E2E-001 — P1 (nueva):**

EMECAS verifica compilación y tests unitarios pero NO verifica que el pipeline
funciona end-to-end. El bug del firewall llevaba desde DAY 98 invisible porque
50/50 tests pasan pero `events_processed=0` nunca se detectó.

**Añadir fase `make test-e2e` al final de EMECAS:**

```
EMECAS actual:
  vagrant destroy → vagrant up → make bootstrap → make test-all

EMECAS propuesto:
  vagrant destroy → vagrant up → make bootstrap → make test-all → make test-e2e
```

**Tests E2E mínimos a implementar:**
```
TEST-E2E-1: sniffer → ml-detector
  → inyectar tráfico sintético (synthetic_sniffer_injector)
  → verificar ml-detector: events_processed > 0

TEST-E2E-2: ml-detector → firewall
  → verificar firewall: events_processed > 0, events_dropped = 0
  → verificar firewall: detections_received > 0

TEST-E2E-3: etcd-server → firewall (AUTONOMY signal)
  → verificar cadena de autonomía E2E

TEST-E2E-4: pipeline completo — drop rate check
  → FALLO si events_processed=0 en cualquier componente receptor
  → FALLO si drop_rate=100% en cualquier canal ZMQ
```

**Prerequisito:** verificar y actualizar `tools/synthetic_sniffer_injector`
para que genere tráfico compatible con el formato actual del pipeline
(puede haber quedado desactualizado desde DAY 98 igual que el firewall).

```bash
# Primer comando para inspeccionar el injector
grep -n "encrypt\|CryptoTransport\|seed\|zmq\|send" \
  tools/synthetic_sniffer_injector.cpp | head -30
```

### ❌ Pendiente (P1, post TAREA 2)
**DEBT-ALERTING-LIBCRYPTO-PROVIDER-001:**
Mover `AlertClient` como implementación opaca dentro de `libcrypto_provider.so`.
Exponer `argus/alerting.h` sin httplib en headers. Prerequisito para que
todos los componentes puedan enviar alertas Discord/Telegram sin ODR.
Hoy solo `etcd-server` puede enviar alertas de forma segura.

### ❌ Pendiente (P2)
**DEBT-ALERTING-VAULT-001:** migrar credenciales Discord/Telegram a Vault.

## Reglas permanentes del proyecto
- EMECAS = `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- macOS: siempre Python3 heredoc (`<< 'PYEOF'`), nunca `sed -i` sin `-e ''`
- Vagrant commands desde macOS siempre sin `-c` recursivo dentro de la VM
- "Via Appia Quality" + "JSON is the law"
- ZMQ publisher `bind()` ANTES de subscriber `connect()`
- NO mergear a main hasta pipeline completamente funcional (E2E verde)

## Orden del día DAY 159
1. Fix DEBT-FIREWALL-CRYPTO-FORMAT-001 → `events_processed > 0`
2. Verificar synthetic_sniffer_injector, actualizar si necesario
3. Implementar `make test-e2e` con los 4 tests mínimos
4. EMECAS completo con test-e2e incluido → todo verde
5. Merge `feature/day158-alerting-edge-sos` → main → tag `v0.9.3-day158`
6. Abrir rama `feature/day159-firewall-crypto-e2e`