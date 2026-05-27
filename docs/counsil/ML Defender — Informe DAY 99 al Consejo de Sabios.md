# ML Defender — Informe DAY 99 al Consejo de Sabios
## 27 marzo 2026

Estimados co-autores,

DAY 99 ha sido un día de consolidación crítica de la cadena de confianza
criptográfica. Os presentamos lo realizado y solicitamos vuestro feedback.

---

## Lo realizado hoy

### 1. contexts.hpp — Corrección de asimetría HKDF

El bug crítico identificado era que emisor y receptor de cada canal usaban
contextos HKDF distintos, derivando claves distintas y produciendo MAC error
en producción. La solución: un fichero de constantes que garantiza simetría.
```cpp
namespace ml_defender::crypto {
  CTX_SNIFFER_TO_ML  = "ml-defender:sniffer-to-ml-detector:v1"
  CTX_ML_TO_FIREWALL = "ml-defender:ml-detector-to-firewall:v1"
  CTX_ETCD_TX        = "ml-defender:etcd:v1:tx"
  CTX_ETCD_RX        = "ml-defender:etcd:v1:rx"
  CTX_RAG_ARTIFACTS  = "ml-defender:rag-artifacts:v1"
}
```

10 strings hardcodeados reemplazados en 7 componentes.

### 2. TEST-INTEG-1/2/3 — Gates arXiv completados

- INTEG-1: round-trip E2E CTX_SNIFFER_TO_ML simétrico ✅
- INTEG-1b: todos los canales round-trip (5 contextos) ✅
- INTEG-2: JSON→LZ4→encrypt→decrypt→decompress byte-a-byte ✅
- INTEG-3: regresión — contextos asimétricos → MAC failure confirmado ✅

### 3. Fail-closed EventLoader + RAGLogger

Ambos componentes hacen `std::terminate()` en producción si no hay seed.bin.
`MLD_DEV_MODE=1` como único escape en desarrollo.

### 4. test_hmac_integration habilitado

Estaba comentado desde DAY 53 por incompatibilidad con la API actual de
SecretsManager. Reescrito y habilitado: 4 tests, 2/2 en ctest.

**Tests totales: 24/24 ✅ (era 22/22 al inicio del día)**

---

## Decisiones arquitectónicas relevantes

- **No hay FASE 2**: Opción 2 (instance_id en nonce) descartada —
  replay cross-instance, deuda técnica. Se documenta en ADR-022.
- **FASE 3 directamente**: deployment.yml + seed families + Vagrantfile
  multi-VM para el verdadero modo distribuido.
- **Fail-closed es production-ready**: Sin seed.bin, el sistema no arranca.
  Esto es correcto para hospitales, escuelas y PYMEs objetivo.

---

## Preguntas para el Consejo

1. **Sobre contexts.hpp**: ¿Consideráis suficiente el enfoque de constantes
   compartidas para FASE 1 (single instance)? ¿Algún vector de ataque que
   no hayamos contemplado con esta nomenclatura de contextos HKDF?

2. **Sobre fail-closed**: ¿`std::terminate()` es la estrategia correcta o
   preferís una excepción tipada que el main() capture y loguee antes de
   salir? El argumento para `terminate()` es que es más difícil de silenciar
   accidentalmente.

3. **Sobre TEST-INTEG-3 (regresión)**: El test confirma que contextos
   asimétricos producen MAC failure. ¿Debería este test correr también
   en CI como smoke test del pipeline E2E completo, no solo en
   crypto-transport?

4. **Sobre la hoja de ruta arXiv**: Con FASE 1 casi completa (pendiente
   ADR-021/022 y tools/), ¿consideráis que el pipeline está listo para
   la sumisión al arXiv, o hay aspectos de seguridad o rendimiento que
   deberían estar cubiertos primero?

5. **Sobre bare-metal**: El siguiente P1 milestone es stress test en
   bare-metal (sin el bottleneck VirtualBox NIC ~33-38 Mbps). ¿Alguna
   recomendación sobre metodología de benchmarking para que los resultados
   sean reproducibles y publicables?

---

Quedamos a vuestra disposición para el debate.

*DAY 99 — 27 marzo 2026*
*Tests: 24/24 ✅*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*