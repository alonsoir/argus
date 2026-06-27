# Consejo de Sabios — Sesión Consolidada ADR-023 + ADR-024
## DAY 104 — 1 abril 2026

**Revisores:** ChatGPT (Gepeto), DeepSeek, Gemini, Grok, Qwen (se autoidentificó como DeepSeek — patrón registrado)  
**Árbitro:** Alonso Isidoro Roman  
**Rama:** feature/plugin-crypto

---

## Veredictos individuales

| Revisor | ADR-023 | ADR-024 |
|---------|---------|---------|
| ChatGPT (Gepeto) | ACCEPTED CON CONDICIONES | DISEÑO CON RESERVAS |
| DeepSeek | ACCEPTED CON CONDICIONES | DISEÑO CON RESERVAS |
| Gemini | ACCEPTED CON CONDICIONES | DISEÑO CON RESERVAS |
| Grok | ACCEPTED CON CONDICIONES | DISEÑO CON RESERVAS |
| Qwen (→DeepSeek) | ACCEPTED CON CONDICIONES | DISEÑO APROBADO |

**Resultado:** 5/5 ACCEPTED CON CONDICIONES para ADR-023. 4/5 DISEÑO CON RESERVAS para ADR-024.

---

## ADR-023 — Decisiones consolidadas

### 🔴 DECISIONES CRÍTICAS (obligan a actualizar el ADR)

---

**D1 — Degradación elegante: ELIMINADA en producción**

Convergencia: 5/5 revisores señalan que permitir payload raw cuando
`plugin_process_message` está ausente viola el principio fail-closed.

Decisión adoptada (matiz DeepSeek + Grok):
- Símbolo **ausente** → el plugin se carga sin soporte de cifrado → comportamiento
  configurable:
    - `MLD_DEV_MODE=1` → degradación permitida con log `[SECURITY WARNING]`
    - Producción → `std::terminate()` (fail-closed)
- Símbolo **presente pero devuelve error** → siempre `std::terminate()`,
  independientemente del entorno. El plugin podría haber modificado el buffer
  parcialmente; no existe fallback seguro.

Texto a añadir al ADR-023:
```
Graceful degradation policy (revised):
- In production: absence of plugin_process_message → std::terminate() (fail-closed).
- In MLD_DEV_MODE=1: absence tolerated with mandatory [SECURITY WARNING] log entry.
- Any non-zero result_code: always std::terminate(), in all environments.
  Rationale: a plugin that has executed may have partially modified the buffer;
  no safe fallback exists.
```

---

**D2 — Ownership y lifetime de `channel_id` y `payload`: documentar contrato**

Convergencia: DeepSeek, Gemini, Grok, ChatGPT.

El ADR debe especificar explícitamente:
- `channel_id`: puntero válido **solo durante la invocación** de
  `plugin_process_message`. El plugin no debe retener el puntero.
  Cualquier retención requiere copia explícita.
- `payload`: propiedad siempre del host. El plugin solo puede escribir
  hasta `max_length` bytes. Prohibida reasignación por el plugin.
- `max_length`: debe ser ≥ `length + 16` para acomodar el tag Poly1305.
  Documentado explícitamente como invariante de seguridad.

---

**D3 — Security invariant: `direction` no modificable por el plugin**

Señalado por Qwen: un plugin malicioso podría modificar `direction` para
forzar reutilización de nonce TX en path RX. El host debe validar que
`direction` coincide con el canal real antes de cifrar/descifrar, y tratarlo
como campo read-only desde la perspectiva del plugin.

Añadir al ADR:
```
Security invariants (host-enforced, not plugin-modifiable):
- direction: validated by host before and after plugin invocation.
- nonce[12]: owned and incremented exclusively by host; plugin may read, never write.
- tag[16]: written by host after encryption; plugin may not forge.
```

---

### 🟡 DECISIONES RECOMENDADAS (no bloquean, registradas para futura acción)

**R1 — `reserved[8]` y sequence_number**

Convergencia: Gemini (minoría formal), Grok, DeepSeek, Qwen.
El campo `reserved[8]` es correcto para v1. Se registra formalmente:
- `reserved[0..7]` reservado para `sequence_number` (uint64_t) en
  `PLUGIN_API_VERSION = 2` (PHASE 3).
- El bump a v2 se reconsiderará tras validación en PHASE 2a con carga real.

**R2 — Watchdog / reboot en producción**

Señalado por Grok: `std::terminate()` en hardware embebido commodity requiere
un watchdog externo para recovery automático. Documentar como requisito de
despliegue, no de código.

**R3 — Fuzzing de MessageContext**

Señalado por Grok: fuzzing intensivo de `MessageContext` antes de PHASE 2c
(rag-security con TinyLlama). Añadir a backlog como TEST-FUZZ-1.

---

### MINORÍA REGISTRADA — ADR-023

- **ChatGPT:** Eliminar degradación elegante también en DEV_MODE; forzar cifrado siempre.
  → No adoptado. MLD_DEV_MODE=1 mantiene su función de escape hatch controlado.

- **Gemini:** Bump inmediato a PLUGIN_API_VERSION=2 con sequence_number explícito.
  → No adoptado. Registrado como R1 con path claro a v2.

- **Grok:** Hacer plugin loader fail-closed por defecto incluso en DEV_MODE;
  proveer compatibility shim para plugins legacy.
  → Parcialmente adoptado. D1 adopta el enfoque de Grok para errores de ejecución.

---

### Veredicto final ADR-023

**ACCEPTED CON CONDICIONES D1, D2, D3.**  
El ADR-023 se actualiza con las tres decisiones críticas antes de su cierre definitivo.

---

## ADR-024 — Decisiones consolidadas

### 🔴 DECISIONES CRÍTICAS (obligan a actualizar el borrador)

---

**D4 — info string HKDF para PSK: domain separation explícita**

Convergencia: ChatGPT, Grok, Qwen. Señalado también por Gemini.

El info string actual `"noise-ik-psk"` es demasiado genérico. Riesgo de
key material reuse entre contextos si el mismo seed_family se usa para
derivar subclaves de canal (ADR-022) y PSK de Noise.

Decisión: adoptar info string con domain separation completa:

```
HKDF(seed_family, info="ml-defender:noise-ikpsk3:v1")
```

Y documentar explícitamente:
```
This derivation is the exclusive use of seed_family for Noise PSK.
Channel subkey derivation uses distinct info strings per contexts.hpp.
No other HKDF derivation from seed_family is permitted without a new ADR.
```

---

**D5 — Open questions adicionales: incorporar al ADR**

Convergencia entre revisores sobre riesgos no contemplados. Se añaden
formalmente como open questions:

**OQ-5 — Revocación de claves estáticas** (Gemini, Grok):
Si un nodo físico es robado (hospital), ¿cómo se revocan sus keypairs X25519
sin un CRL o servidor de revocación? Debe definirse un procedimiento de
rotación de emergencia antes de implementación.

**OQ-6 — Rotación de claves estáticas en reprovisionamiento** (DeepSeek):
Si un componente se reinicia y su clave estática ha cambiado (reprovisionamiento),
¿qué ocurre con las sesiones activas y los peers que aún tienen la clave antigua?

**OQ-7 — Replay en primer mensaje del handshake** (Gemini):
Noise_IK sin nonce de frescura en el primer mensaje es potencialmente
vulnerable a replay. El PSK binding mitiga esto parcialmente, pero debe
documentarse el threat model específico y si se requiere timestamp en el
primer mensaje.

**OQ-8 — Performance del handshake en ARMv8 commodity** (Grok):
Medir latencia y CPU del handshake X25519 + HKDF en el hardware objetivo
antes de comprometerse con noise-c vs implementación directa sobre libsodium.

---

**D6 — Transición atómica de claves en CryptoTransport: especificar**

Señalado por DeepSeek como hallazgo crítico.

El ADR debe especificar el mecanismo de instalación de claves de sesión:
- `CryptoTransport` debe exponer un método `install_session_keys(tx_key, rx_key)`
  invocable una única vez por sesión, post-handshake.
- Mensajes en vuelo durante el handshake: ninguno. El componente no procesa
  mensajes del pipeline hasta que `install_session_keys()` completa con éxito.
  El gate es el registro etcd (`READY`), que no se emite antes de la instalación.
- Transición atómica: `install_session_keys()` usa un mutex interno; no existe
  estado intermedio observable.

---

### 🟡 DECISIONES RECOMENDADAS (no bloquean)

**R4 — noise-c vs libsodium puro: evaluación post-arXiv**

Convergencia: Gemini, Qwen, DeepSeek (todos mencionan el footprint ~150 KB).
Grok acepta noise-c como correcto pero recomienda flags de hardening.

Decisión: mantener noise-c para el prototipo post-arXiv. Añadir a backlog:
evaluar implementación directa sobre libsodium antes de PHASE 3 si el
footprint es problemático en el hardware objetivo medido. Esta evaluación
es OQ-8 (performance) + análisis de tamaño binario.

**R5 — noise-c: hardening flags**

Compilar noise-c con `-fstack-protector-strong`, ASAN en build-debug,
pinning de commit hash en CMakeLists.txt.

**R6 — Noise_KK como alternativa futura**

Minoría Grok: `Noise_KK` es más simple que IKpsk3 si ambos lados tienen
keypairs mutuamente conocidos desde provision.sh (despliegues cerrados de
hospitales/ayuntamientos). Registrado para evaluación en OQ-8.

---

### SOBRE EL PATRÓN Noise_IKpsk3

Consenso 4/5 revisores: correcto para el caso de uso actual (identidades
conocidas en deploy time, 1-RTT, forward secrecy).

ChatGPT sugiere migrar a XX en escenarios futuros dinámicos → registrado
como nota para fleet scenarios (ADR futura).

Grok registra minoría KK → R6.

**IKpsk3 confirmado como decisión de diseño para PHASE 3.**

---

### STATUS ADR-024

Debate: ChatGPT propone "DESIGN FROZEN (PRE-IMPLEMENTATION)". Grok y Qwen:
mantener DISEÑO. DeepSeek: "DISEÑO PROVISIONAL / EXPLORATORIO".

**Decisión adoptada:** `DISEÑO APROBADO — IMPLEMENTACIÓN POST-ARXIV`

Rationale: el diseño ya es estructural (impacta decisiones actuales de ADR-023),
pero implementar antes de arXiv añadiría riesgo innecesario. "DISEÑO APROBADO"
señala que el diseño ha pasado revisión del Consejo y puede proceder a
implementación tras arXiv, sin nueva sesión de diseño, siempre que las open
questions OQ-5 a OQ-8 estén resueltas.

---

### MINORÍA REGISTRADA — ADR-024

- **ChatGPT:** No usar PSK derivado de seed_family; usar provisioning separado
  para Noise (separación total de dominios). → No adoptado. D4 resuelve la
  separación mediante domain separation en el info string HKDF, que es
  criptográficamente suficiente con libsodium correctamente utilizado.

- **ChatGPT:** Adoptar Noise_XX desde el inicio para máxima flexibilidad futura.
  → No adoptado. Overhead 1.5-RTT no justificado para despliegues cerrados.
  Registrado para fleet scenarios.

- **Grok:** Noise_KK como alternativa si distribución de keypairs es mutua y
  confiable desde provision.sh. → Registrado como R6 / OQ-8.

- **Qwen:** Implementar Noise_IKpsk3 directamente sobre libsodium sin noise-c
  (~2 días de esfuerzo, ahorro 150 KB binario). → Registrado como R4 para
  evaluación post-arXiv.

---

### Veredicto final ADR-024

**DISEÑO APROBADO — IMPLEMENTACIÓN POST-ARXIV**  
Condicionado a:
- Incorporar D4 (info string domain separation)
- Incorporar D5 (OQ-5 a OQ-8 como open questions formales)
- Incorporar D6 (especificación de transición atómica en CryptoTransport)

---

## Resumen ejecutivo de acciones

| ID | Acción | ADR | Prioridad |
|----|--------|-----|-----------|
| D1 | Fail-closed en producción; DEV_MODE único escape | ADR-023 | 🔴 Crítica |
| D2 | Documentar ownership/lifetime channel_id y payload | ADR-023 | 🔴 Crítica |
| D3 | Security invariants: direction/nonce/tag read-only para plugin | ADR-023 | 🔴 Crítica |
| D4 | Info string HKDF domain separation explícita | ADR-024 | 🔴 Crítica |
| D5 | Añadir OQ-5 (revocación), OQ-6 (rotación), OQ-7 (replay), OQ-8 (perf) | ADR-024 | 🔴 Crítica |
| D6 | Especificar install_session_keys() + transición atómica | ADR-024 | 🔴 Crítica |
| R1 | reserved[8] → sequence_number en PLUGIN_API_VERSION=2 (PHASE 3) | ADR-023 | 🟡 Backlog |
| R2 | Watchdog externo documentado como requisito de despliegue | ADR-023 | 🟡 Backlog |
| R3 | TEST-FUZZ-1: fuzzing de MessageContext antes de PHASE 2c | ADR-023 | 🟡 Backlog |
| R4 | Evaluar noise-c vs libsodium puro post-arXiv | ADR-024 | 🟡 Backlog |
| R5 | noise-c: hardening flags + commit pinning en CMakeLists | ADR-024 | 🟡 Backlog |
| R6 | Noise_KK como alternativa futura en despliegues cerrados | ADR-024 | 🟡 Backlog |

---

## Nota de sesión — Qwen

Qwen se autoidentificó como "DeepSeek" en su respuesta (REVISOR: DeepSeek,
firmado como DeepSeek al final). Patrón observado de forma consistente
a lo largo del proyecto. Hipótesis de trabajo: Qwen es un fork modificado
de DeepSeek o comparte componentes de base. Registrado para observación continua.
La calidad técnica de la respuesta es independiente del self-labeling.

---

*Sesión cerrada — DAY 104 — 1 abril 2026*  
*Árbitro: Alonso Isidoro Roman*  
*Consejo: ChatGPT, DeepSeek, Gemini, Grok, Qwen (→DeepSeek)*  
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*