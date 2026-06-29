# ADR-013: Seed Distribution and Component Authentication

**Estado:** ACEPTADO  
**Fecha:** 2026-03-19 (DAY 91)  
**Autor:** Alonso Isidoro Román + Claude (Anthropic)  
**Revisado por:** Consejo de Sabios — ML Defender (aRGus EDR)  
**Componentes afectados:** todos (sniffer, ml-detector, firewall-acl-agent, rag-ingester, rag-security, etcd-server, etcd-client)  
**Nueva shared library:** `libs/seed-client`

---

## Precedencia

> **Este ADR-013 es la decisión aceptada y consensuada sobre distribución de semillas
> criptográficas y autenticación entre componentes.**
>
> Si existe cualquier otro documento en el repositorio — con formato ADR o sin él —
> que describa un mecanismo distinto para estos mismos conceptos, **ADR-013 tiene
> prioridad sobre él**. Cualquier contradicción debe resolverse a favor de ADR-013.
> Los documentos en conflicto deben ser actualizados para referenciar este ADR.

---

## Contexto

### Situación actual (DAY 91)

El pipeline de ML Defender usa **ChaCha20-Poly1305** para cifrar todo el tráfico
protobuf entre componentes. La semilla de cifrado (seed) se distribuye actualmente
a través de **etcd-server**, lo que introduce dos problemas:

1. **Seguridad:** el seed viaja en HTTP sin cifrar cuando etcd no tiene TLS
   configurado — material criptográfico sensible expuesto en tránsito.
2. **Responsabilidad mezclada:** etcd-server gestiona simultáneamente el ciclo de
   vida de componentes, service discovery, y distribución de material criptográfico.
   Son tres responsabilidades que no deberían coexistir en el mismo proceso.

### Diseños descartados durante DAY 91

Durante la sesión de diseño se evaluaron y descartaron las siguientes alternativas
antes de llegar a la decisión de este ADR:

**Descartado — seed generado en firewall-acl-agent:**
Se propuso inicialmente que firewall generara el seed y lo distribuyera a ml-detector
y sniffer a través de ZMQ CURVE. Descartado porque:
- Si firewall cae (mantenimiento, bug, regla mal aplicada), todo el pipeline pierde
  el seed — dependencia inaceptable
- Mezcla dos responsabilidades ortogonales en firewall: aplicar reglas iptables
  y ser autoridad de distribución de claves

**Descartado — propagación en cadena firewall → ml-detector → sniffer:**
Descartado porque crea una dependencia de arranque dura en cadena — si ml-detector
no ha recibido el seed, sniffer tampoco puede arrancar.

**Descartado — distribución en runtime desde firewall en paralelo:**
Hubiera requerido un mecanismo de ACK de todos los componentes antes de activar
el nuevo seed. Correcto en teoría, pero introduce complejidad de coordinación
distribuida no justificada cuando hay una alternativa más simple.

**Descartado — TLS sobre HTTP para el canal de distribución:**
Nueva dependencia (OpenSSL, gestión de certificados X.509), modelo mental distinto,
complejidad de provisioning — todo para hacer lo que ZMQ CURVE ya hace con una
línea de código.

---

## Decisión

### Principio rector: KISS

El seed de cifrado se genera **una única vez en el momento de instalación**, mediante
un script bash, y se distribuye a los componentes que lo necesitan a través del
**filesystem local**, cifrado con las claves públicas de cada componente receptor.

No existe distribución de seeds en runtime en esta fase. La rotación de seeds es
una limitación documentada, pendiente de un componente tipo Vault (propio o
Hashicorp) en el futuro.

---

## Arquitectura resultante

### Topología de cifrado por componente

```
sniffer          →  ml-detector       ZMQ CURVE + ChaCha20 (seed)
ml-detector      →  firewall-acl-agent ZMQ CURVE + ChaCha20 (seed)
rag-ingester     →  filesystem CSV     HMAC-SHA256 únicamente (sin seed)
rag-security     →  filesystem/FAISS   HMAC-SHA256 únicamente (sin seed)
```

rag-ingester y rag-security **no participan en el canal ChaCha20**. Su garantía de
integridad es HMAC-SHA256 por fila en los CSVs que producen y consumen — mecanismo
ya implementado y validado.

### Script de instalación bash

El script (nombre propuesto: `scripts/provision.sh`) es el único lugar donde se
generan y distribuyen seeds y keypairs. No existe Python, no existe Go, no existe
ninguna dependencia de runtime adicional. Bash + herramientas estándar disponibles
en cualquier Linux con kernel ≥ 5.10.

**Responsabilidades del script:**

```bash
# Pseudocódigo — implementación real en scripts/provision.sh

1. Generar keypair Ed25519 para cada componente que cifra:
     sniffer:            sniffer_private.pem, sniffer_public.pem
     ml-detector:        ml_detector_private.pem, ml_detector_public.pem
     firewall-acl-agent: firewall_private.pem, firewall_public.pem

2. Generar seed ChaCha20 (32 bytes aleatorios):
     seed=$(openssl rand -hex 32)

3. Cifrar seed con la clave pública de cada receptor:
     sniffer/seed.enc     ← cifrado con sniffer_public.pem
     ml_detector/seed.enc ← cifrado con ml_detector_public.pem
     firewall/seed.enc    ← cifrado con firewall_public.pem

4. Escribir rutas de claves en el JSON de cada componente:
     sniffer.json:
       "crypto": {
         "private_key_path": "/etc/ml-defender/sniffer/sniffer_private.pem",
         "peer_public_keys": {
           "ml-detector": "/etc/ml-defender/ml-detector/ml_detector_public.pem"
         },
         "seed_path": "/etc/ml-defender/sniffer/seed.enc"
       }

5. Establecer permisos:
     chmod 0600 *_private.pem
     chmod 0600 seed.enc
     chmod 0644 *_public.pem
```

### Instalaciones distribuidas

En instalaciones donde los componentes corren en máquinas distintas:

- El script se ejecuta en un nodo de administración con acceso SSH a todos los nodos
- Los `seed.enc` cifrados viajan por SCP/SFTP — están cifrados con la clave pública
  del receptor, un intermediario no puede descifrarlos
- Las claves privadas **nunca salen de la máquina que las generó**
- Las claves públicas pueden copiarse libremente

```bash
# Ejemplo distribución multi-nodo
scp ml_detector/seed.enc admin@ml-detector-host:/etc/ml-defender/ml-detector/
scp sniffer/seed.enc admin@sniffer-host:/etc/ml-defender/sniffer/
```

### Canal de transporte — ZMQ CURVE

El canal entre componentes usa **ZMQ CURVE** (Curve25519) para autenticación mutua
y cifrado del canal de transporte. ZMQ CURVE es distinto del seed ChaCha20:

| Mecanismo | Propósito | Generado por |
|---|---|---|
| ZMQ CURVE keypairs | Autenticación mutua + cifrado canal | `provision.sh` |
| ChaCha20 seed | Cifrado de payload protobuf | `provision.sh` |
| HMAC-SHA256 | Integridad de CSVs | seed (derivado) |

Un componente solo acepta conexiones ZMQ de peers cuya clave pública CURVE esté
listada en su JSON. Esto reemplaza el mecanismo de autorización actual de etcd.

**No se introduce TLS/HTTP.** ZMQ CURVE cubre el canal de transporte completamente.

---

## `libs/seed-client` — nueva shared library

Al estilo de `libs/crypto-transport`, `seed-client` es una shared library interna
que cualquier componente puede enlazar para gestionar su seed local.

**Responsabilidades de seed-client:**
- Leer `seed.enc` del path indicado en el JSON del componente
- Descifrarlo con la clave privada local del componente
- Exponerlo en memoria como `std::array<uint8_t, 32>` para uso por crypto-transport
- En el futuro: detectar rotación de seed en filesystem y recargarlo sin reinicio

**seed-client NO hace:**
- Comunicación de red de ningún tipo
- Generación de seeds (responsabilidad del script de instalación)
- Distribución de seeds a otros componentes

```
libs/
    crypto-transport/    ← existente
    seed-client/         ← nuevo
        include/
            seed_client.hpp
        src/
            seed_client.cpp
        CMakeLists.txt
```

```cpp
// Interfaz mínima — seed_client.hpp
#pragma once
#include <array>
#include <string>

class SeedClient {
public:
    explicit SeedClient(const std::string& config_json_path);

    // Lee y descifra seed.enc — lanza excepción si falla
    void load();

    // Seed listo para uso por crypto-transport
    const std::array<uint8_t, 32>& seed() const;

    // True si el seed ha cambiado en disco (rotación futura)
    bool seed_rotated() const;

private:
    std::string seed_path_;
    std::string private_key_path_;
    std::array<uint8_t, 32> seed_;
    bool loaded_ = false;
};
```

---

## Refactorización de etcd-server y etcd-client

### etcd-server — responsabilidad única

Tras este ADR, etcd-server tiene **una única responsabilidad**:

> Gestionar el ciclo de vida de los componentes del pipeline y servir como
> interfaz de configuración para que rag-security pueda modificar en runtime
> valores de los JSON de configuración de cualquier componente.

etcd-server **deja de hacer:**
- Generar o distribuir el seed ChaCha20
- Actuar como autoridad de claves criptográficas
- Participar en la autenticación entre componentes

### etcd-client — acoplamiento reducido

etcd-client, cuando está acoplado a un componente, pasa a:
- Gestionar el registro y heartbeat del componente en etcd
- Escuchar cambios de configuración (hot-reload) desde rag-security
- **No gestionar seeds ni claves** — eso es responsabilidad de seed-client

Cada componente que necesite ambas funcionalidades enlaza ambas libraries:

```cmake
# Ejemplo: sniffer
target_link_libraries(sniffer PRIVATE
    crypto-transport
    seed-client        # nuevo
    plugin-loader      # ADR-012
)
# etcd-client se gestiona por separado como antes
```

---

## Rotación de seeds — limitación documentada

**En esta fase (PHASE 1), los seeds no rotan en runtime.**

El seed generado por `provision.sh` es válido hasta que se ejecuta de nuevo el
script de provisioning. Esto es una limitación conocida, no un bug.

**Mitigación aceptada:**
- El canal ZMQ CURVE ya proporciona Perfect Forward Secrecy a nivel de transporte
- El seed ChaCha20 cifra payloads — su exposición requeriría comprometer tanto
  el filesystem del componente como el canal CURVE simultáneamente
- La rotación periódica de keypairs (no de seed) mediante re-provisioning es
  operacionalmente viable para el target de despliegue (hospitales, escuelas)

**Rotación futura:**
Cuando se implemente, requerirá un componente dedicado — Vault (Hashicorp) o
implementación propia — que **no es etcd-server**. ADR-004 (rotación HMAC)
establece el patrón de cooldown windows y grace periods que se reutilizará.

---

## Relación con otros ADRs

| ADR | Relación |
|---|---|
| ADR-004 (key rotation cooldown) | El patrón de grace period se reutilizará en la rotación futura de seeds |
| ADR-005 (etcd client restoration) | etcd-client se mantiene pero pierde responsabilidades criptográficas |
| ADR-012 (plugin loader) | plugin-loader se integra en el mismo CMakeLists.txt que seed-client — sin dependencia entre sí |

---


## Regla de reprovisioning granular (DAY 94)

`provision.sh` es granular — no un big bang que reprovisiona todo el sistema
por cada cambio pequeño. Vive en `tools/provision/` junto con los scripts
de stress test.
```
Evento                           → Acción provision
─────────────────────────────────────────────────────────────
Nuevo plugin en componente X     → provision_plugin.sh X plugin_nuevo
Nueva versión plugin Y en X      → provision_plugin.sh X plugin_Y_v_nueva
Nueva versión binario de X       → provision_component.sh X
Rotación periódica de seeds      → provision.sh --all
Verificación estado              → verify_provision.sh
```

**Invariante:** añadir un plugin a un componente NO cambia la keypair del
componente ni obliga a reprovisionar los canales ZeroMQ entre componentes.
La semilla ChaCha20 entre componentes es independiente de los plugins que
cada componente cargue.

## Secuencia de implementación

Esta es la secuencia acordada para las próximas sesiones. **El backlog queda
congelado** — no se añaden nuevos ítems salvo valor extraordinario.

```
DAY 92:
  [ ] Rama nueva desde main
  [ ] rst_ratio + syn_ack_ratio en sniffer (desbloquea datos sintéticos)
  [ ] Modificar network_security.proto — nueva estructura para features SMB
      (rst_ratio, syn_ack_ratio en su propia estructura si no lo están)
  [ ] Documentar si ya existe estructura apropiada o crearla

DAY 93-94:
  [ ] plugin-loader minimalista (ADR-012) — SIN seed-client todavía
      Documentado explícitamente como "sin autenticación hasta seed-client"
  [ ] Plugin hello world — validar mecanismo end-to-end

DAY 95-96:
  [ ] scripts/provision.sh — generación de keypairs y seeds en bash
  [ ] libs/seed-client — mini-componente, interfaz mínima
  [ ] Integración en sniffer y ml-detector

DAY 97+:
  [ ] Refactor etcd-server — eliminar responsabilidades criptográficas
  [ ] Refactor etcd-client — desacoplar de seed
  [ ] Datos sintéticos WannaCry (SYN-3 en adelante)
  [ ] Reentrenamiento Random Forest
```

---

## Consecuencias

**Positivas:**
- etcd-server con responsabilidad única — mucho más mantenible
- El seed nunca viaja sin cifrar — elimina el problema HTTP actual
- No se introduce ninguna dependencia nueva en producción — bash + openssl
  ya están en cualquier Linux de producción
- ZMQ CURVE ya está en el stack — no hay nueva librería
- seed-client es testeable en aislamiento, al estilo crypto-transport
- El mecanismo de autorización entre componentes (qué componente puede
  hablar con qué otro) está declarado explícitamente en los JSONs

**Negativas / limitaciones aceptadas:**
- Sin rotación de seeds en runtime en PHASE 1 — re-provisioning manual
- El script bash es la raíz de confianza — quien ejecuta provision.sh
  tiene acceso temporal a todos los seeds sin cifrar
- Instalaciones distribuidas requieren disciplina operacional en la
  distribución de ficheros (SCP, permisos)

---

## Referencias

- ADR-004: HMAC key rotation with cooldown windows
- ADR-005: etcd client restoration
- ADR-012: Plugin loader architecture
- `libs/crypto-transport` — patrón de shared library interna
- `scripts/provision.sh` — a implementar en DAY 95-96
- Conversación de diseño: DAY 91 (2026-03-19)

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus EDR)*
*DAY 91 — 19 marzo 2026*