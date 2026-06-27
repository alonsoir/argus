**🏛️ CONSEJO DE SABIOS — DAY 157 — ARGUS NDR**  
**Rama:** `feature/day157-autonomy-state-persistence`  
**Tag anterior:** `v0.9.1-day156`  
**Autor:** Aironman DirtDiver  
**Fecha:** 19/05/2026

---

## **📌 Resumen Ejecutivo**

Cuatro deudas técnicas **P1/P2** cerradas en esta sesión, enfocadas en:

- Persistencia y firma de estados de autonomía.
- Gestión de claves en entornos productivos.
- Reconciliación criptográfica en el pipeline de salud.

**EMECAS pendiente:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`.

---

## **🔧 Deudas Técnicas Cerradas**

### **1. DEBT-AUTONOMY-STATE-PERSISTENCE-001 (P1)**

- **Archivo:** `common/autonomy_state_writer.h` (header-only).
- **Funcionalidad:**
    - Escribe/lee el estado `CryptoAutonomyStateMachine` (firmado Ed25519) en `/var/lib/argus/crypto-autonomy-state.json`.
    - **Escritura atómica:** `write → fsync → rename`.
    - **Lectura fail-safe:**
        - Firma inválida/ausente → **NORMAL**.
        - Estado `AUTONOMOUS` expirado (>24h) → **NORMAL**.
- **Integración:** etcd-server STEP 0c (lectura al arrancar, escritura en transiciones del *health-check loop*).
- **Tests:** 9/9 **RED→GREEN**.

---

### **2. DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 (P1)**

- **Archivo:** `etcd-server/src/main.cpp` (STEP 0).
- **Cambios:**
    - `bootstrap-status.json` ahora **firmado Ed25519**.
    - JSON canónico (claves ordenadas, sin `signature_hex`) → `crypto_sign_detached` → campo `signature_hex` añadido.
    - Escritura atómica: `tmp → rename + fsync`.
    - **Cadena de confianza:** Igual que ADR-025 plugins.
- **Deuda pendiente:** DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 (P2).
    - **Acción:** `check-bootstrap-status.sh` + systemd `ExecStartPost=` para verificar firma **antes** de iniciar dependientes.

---

### **3. DEBT-KEYPAIR-LIFECYCLE-PROD-001 (P1)**

- **Archivo:** `tools/provision.sh` (`generate_keypair()`).
- **Política de 3 niveles:**

  | Entorno                 | Comportamiento                                             |
    | ----------------------- | ---------------------------------------------------------- |
  | `ARGUS_ENV=prod`        | `exit 1` si keypair ausente (NUNCA genera silenciosamente) |
  | `ARGUS_ENV=dev/staging` | Genera normalmente (default)                               |
  | Keypair existente       | `skip` sin cambios (cualquier env)                         |


---

### **4. DEBT-CRYPTO-RECONCILIATION-001 (P2)**

- **Componente:** `AutonomySubscriber`.
- **Arquitectura final:**
    - `last_known_mode_` (`atomic<FirewallAutonomyMode>`) actualizado en:
        - `handle_message()` (ZMQ).
        - Reconciliador.
    - **Sincronización:** `shared_ptr<atomic<FirewallAutonomyMode>>` compartido entre *subscriber* y `poll_callback`.
        - Resuelve *ordering* **sin segundo socket**.
    - **Feature flag:** `use_dedicated_health_channel=false` (MVP).
    - **Backward compat:** Constructor acepta `shared_mode` opcional (`nullptr` = modo legado).
- **Tests:** 8/8 **PASSED** (T7: `last_known_mode()` vía ZMQ, T8: `shared_mode` vía ZMQ).

---

## **❓ Preguntas para el Consejo**

### **1. Persistencia del Estado de Autonomía (DEBT-AUTONOMY-STATE-PERSISTENCE-001)**

- **Vector de ataque:** ¿Hay escenarios no cubiertos en la lectura *fail-safe*?
    - Ejemplo: ¿Un ataque de *replay* con un estado `AUTONOMOUS` válido pero obsoleto?
- **Umbral de expiración:** ¿24h es el tiempo correcto para producción **hospitalaria**?
    - ¿Debería ser configurable por entorno?

---

### **2. Firma de `bootstrap-status.json` (DEBT-BOOTSTRAP-STATUS-SIGNATURE-001)**

- **Problema:** El fichero es **efímero** (se borra tras `g_server->start()`).
    - ¿Tiene sentido que systemd lo verifique en `ExecStartPost=` si **ya no existe** en ese momento?
    - **Alternativa:** ¿Debería el *check* ejecutarse **antes** del `start()` (ej: `ExecStartPre=`)?

---

### **3. Ciclo de Vida de Keypairs (DEBT-KEYPAIR-LIFECYCLE-PROD-001)**

- **Política actual:** `dev/staging` = generación automática; `prod` = keypair preexistente obligatorio.
    - ¿Debería `staging` **también** requerir keypair preexistente?
        - **Riesgo:** Inconsistencia entre entornos si `staging` permite generación silenciosa.

---

### **4. Reconciliación Criptográfica (DEBT-CRYPTO-RECONCILIATION-001)**

- **Escenario crítico:** Si el *publisher* ZMQ (etcd-server) **muere silenciosamente**, el reconciliador devolverá el último modo conocido **indefinidamente**.
    - ¿Es suficiente para **FEDER**?
    - **Propuesta:** ¿Añadir un *timeout* de *staleness* (ej: 5 minutos) para forzar un fallback a `NORMAL`?

---

### **5. Arquitectura General (DAY 157)**

- ¿Existen **inconsistencias** entre las 4 deudas cerradas que deban resolverse antes del *merge* a `main`?
    - Ejemplo: ¿La firma de `bootstrap-status.json` (DEBT-002) debería alinearse con el mecanismo de persistencia de estados (DEBT-001)?

---

## **🔗 Referencias**

- [Repositorio ARGUS](https://github.com/alonsoir/argus)
- [ADR-025: Plugin Trust Chain](https://github.com/alonsoir/argus/blob/main/docs/adr/ADR-025.md)

---

**📢 Nota:** Se solicita respuesta del Consejo antes de proceder con el *merge*. Prioridad: **P1/P2**.