# ML Defender — Security Model
## PHASE 1 · DAY 97 · 25 marzo 2026

*Autores: Alonso Isidoro Roman + Claude (Anthropic)*
*Revisado por el Consejo de Sabios DAY 97: ChatGPT5 · DeepSeek · Gemini · Grok · Qwen*

---

## 1. Cadena de confianza

```
provision.sh
    │  genera seed aleatorio (32B, /dev/urandom)
    │  verifica entropía del kernel (≥256 bits)
    ▼
seed.bin  (chmod 0600, /etc/ml-defender/{component}/)
    │  leído por SeedClient — nunca usado directamente como clave
    ▼
HKDF-SHA256  (libsodium 1.0.19, crypto_kdf_hkdf_sha256_extract/expand)
    │  contexto: "ml-defender:{component}:v1:{tx|rx}"
    │  salt: 32 bytes cero (RFC 5869 §2.2 default)
    ▼
session_key (32B, en memoria, nunca en disco)
    │  sodium_memzero en destructor
    ▼
ChaCha20-Poly1305 IETF  (nonce 96-bit monotónico atómico)
    │  wire format: [nonce(12) || ciphertext(N) || mac(16)]
    ▼
tráfico cifrado entre componentes del pipeline
```

**Invariante:** El seed nunca se usa directamente como clave simétrica.
Cualquier uso de `seed()` sin HKDF previo es un error de seguridad documentado
en `seed_client.hpp` y violación de este modelo.

---

## 2. Límites de PHASE 1

Los siguientes aspectos están **fuera del alcance de PHASE 1** y son limitaciones
conocidas y aceptadas conscientemente:

### 2.1 Seed en claro en disco

El `seed.bin` se almacena sin cifrar en `/etc/ml-defender/{component}/seed.bin`
con permisos `0600`. Un atacante con acceso root al sistema de ficheros puede
leer el seed.

*Mitigación PHASE 1:* chmod 0600, directorio 0700, solo root propietario.
*Mitigación PHASE 2 (planificada):* seed cifrado con clave pública del receptor
(ADR-013 PHASE 2, ENT-8 TPM 2.0/HSM).

### 2.2 Sin forward secrecy por sesión

El contexto HKDF es estático: `"ml-defender:{component}:v1:{tx|rx}"`.
Dos sesiones que arrancan con el mismo `seed.bin` derivan la misma `session_key`.
El nonce monotónico protege dentro de cada sesión, pero no entre reinicios.

**El mecanismo de forward secrecy en este modelo es la rotación de seeds.**
Cuando se ejecuta `provision.sh reprovision {component}`, el seed cambia
completamente y toda la historia de tráfico anterior es inaccesible con el nuevo.

*Decisión Consejo DAY 97 (unanimidad DeepSeek + Qwen, aceptada):*
Añadir session_id dinámico al contexto HKDF sin un mecanismo de intercambio
seguro de ese ID introduce complejidad sin beneficio real para el threat model
actual. La rotación periódica de seeds es el mecanismo correcto.

*Mitigación PHASE 2:* handshake efímero tipo Noise Protocol con ECDH
(FEAT-CRYPTO-2 en backlog).

### 2.3 mlock() no garantizado

`SeedClient` intenta `mlock()` sobre el buffer del seed para evitar que llegue
al swap. En hardware con memoria limitada (`RLIMIT_MEMLOCK` bajo), `mlock()`
puede fallar con `ENOMEM`. En ese caso el sistema loguea un WARNING y continúa.

```
[WARN] mlock() failed (ENOMEM) — seed may be swapped to disk.
       Upgrade hardware to ≥8 GB RAM or increase ulimit -l for full protection.
       System remains operational. Protection is not disabled.
```

Para aumentar el límite de memoria bloqueable:
```bash
# En /etc/security/limits.conf:
ml-defender-user  soft  memlock  65536
ml-defender-user  hard  memlock  65536
```

### 2.4 libsodium compilada desde fuente

PHASE 1 compila libsodium 1.0.19 desde fuente porque Debian Bookworm solo
distribuye 1.0.18. La compilación está protegida con verificación SHA-256
hardcodeada en `provision.sh`:

```
SHA-256: 018d79fe0a045cca07331d37bd0cb57b2e838c51bc48fd837a1472e50068bbea
```

**Limitación:** la librería en `/usr/local/lib/libsodium.so.26` no está
gestionada por apt — no recibirá actualizaciones automáticas.

*Mitigación PHASE 2 (DEBT-INFRA-001):* migrar a Debian Trixie (13), que
distribuye libsodium 1.0.19 en repositorios oficiales con paquetes `.deb`
firmados — requisito para despliegues en entornos con políticas de seguridad
estrictas (hospitales, administración pública).

### 2.5 Sin autenticación mutua entre componentes

Los componentes se autentican implícitamente por posesión del seed derivado.
No existe un handshake explícito que pruebe identidad antes de establecer
la sesión cifrada.

*Mitigación PHASE 2:* keypairs Ed25519 generados por `provision.sh` ya están
disponibles en `/etc/ml-defender/{component}/private.pem`. El handshake de
autenticación mutua está planificado en ADR-013 PHASE 2.

---

## 3. Rotación de seeds

⚠️ **La rotación de seeds requiere reinicio ordenado de toda la pipeline.**

Proceso correcto:

```bash
# 1. Parar la pipeline
make pipeline-stop

# 2. Re-provisionar el componente (genera nuevo seed)
sudo bash tools/provision.sh reprovision {component}

# 3. Reiniciar la pipeline completa
make pipeline-start
```

**Estado split-brain:** si se re-provisiona un componente sin reiniciar la
pipeline, los componentes en vuelo usan la clave derivada del seed antiguo
y el componente re-provisionado usa la del nuevo. La comunicación falla de
forma silenciosa (MAC error, datos descartados). No hay corrupción — pero
tampoco hay alerta explícita más allá de los logs de error de descifrado.

*Decisión Consejo DAY 96:* documentar este comportamiento explícitamente.
No hay mecanismo de hot-reload de seeds en PHASE 1 (ENT-4 en backlog).

---

## 4. Entropía y generación de material criptográfico

### 4.1 Estado actual (PHASE 1 — desarrollo)

`provision.sh` verifica la entropía del pool del kernel antes de generar seeds:

```bash
avail=$(cat /proc/sys/kernel/random/entropy_avail)
[ "$avail" -lt 256 ] → instala haveged automáticamente
```

**`haveged` es aceptable para entornos de desarrollo y VMs**, pero no es
un generador certificado para producción en infraestructura crítica.
`haveged` usa el algoritmo HAVEGE (Hardware Volatile Entropy Gathering),
que no está certificado por NIST, FIPS 140-2/3, ni Common Criteria.

### 4.2 Mecanismo recomendado para producción (PHASE 2)

El estado del arte implementado masivamente en la industria para entornos
Linux en producción es:

**`rng-tools` + fuente de hardware:**

```bash
apt-get install rng-tools5
# Con hardware RNG (Intel RDRAND, AMD RDSEED, TPM 2.0):
rngd -r /dev/hwrng
# En VMs con virtio-rng (KVM/QEMU, VirtualBox con paravirtualización):
rngd -r /dev/hwrng  # virtio-rng expone /dev/hwrng en el guest
```

Alternativas según entorno:

| Entorno | Solución |
|---|---|
| Bare-metal Intel/AMD moderno | `rng-tools5` + RDRAND/RDSEED via `/dev/hwrng` |
| VM KVM/QEMU | `virtio-rng` device + `rng-tools5` |
| VM VirtualBox | `VBoxService` RNG + `rng-tools5` |
| Hardware embebido / Raspberry Pi | `bcm2835-rng` driver + `rng-tools5` |
| Sin hardware RNG | `jitterentropy-rngd` (NIST SP 800-90B, certificado) |

`jitterentropy` es la alternativa certificada cuando no hay hardware RNG —
usa jitter de tiempo de CPU como fuente de entropía física, validado por BSI
(Bundesamt für Sicherheit in der Informationstechnik) y aceptado en contextos
FIPS 140-2.

*Tarea pendiente (DEBT-INFRA-002):* sustituir `haveged` por `rng-tools5` +
detección automática de fuente de hardware en `provision.sh`.

---

## 5. Compresión + cifrado — advertencia CRIME/BREACH

**El orden de operaciones es: LZ4 → ChaCha20-Poly1305 (comprimir antes de cifrar).**

Este orden es correcto para maximizar la ratio de compresión (datos cifrados
tienen entropía máxima, son incomprimibles). Sin embargo, existe una clase
de vulnerabilidades conocida como **CRIME/BREACH** que afecta a sistemas
que comprimen + cifran cuando el atacante puede inyectar input parcialmente
controlado en el payload comprimido.

**Análisis del threat model de ML Defender:**

En PHASE 1, los payloads del pipeline son:
- Eventos de red capturados por el sniffer (datos observados, no generados por el atacante)
- JSONs de configuración de componentes (datos internos del sistema)
- Scores y alertas del ml-detector (datos internos)

**El atacante no controla el contenido del payload.** El riesgo CRIME/BREACH
requiere que el atacante pueda inyectar texto conocido en el payload cifrado
y observar cambios en el tamaño del ciphertext. En el modelo de ML Defender,
el atacante está en la red siendo analizado, no en el canal de comunicación
entre componentes del pipeline.

**Conclusión:** el riesgo CRIME/BREACH es teóricamente aplicable pero
prácticamente despreciable en el threat model actual.

*Documentar y revisar en PHASE 2* si el pipeline incorpora datos con input
parcialmente controlado por actores externos (ej. payloads de red reconstructed,
datos de threat intel feeds externos).

---

## 6. Threat model — alcance PHASE 1

### En scope
- Ransomware conocido (CTU-13 Neris, WannaCry) en redes locales de hospitales,
  escuelas y pequeñas organizaciones
- Tráfico malicioso en redes con hardware commodity (VMs, servidores de 2-4 núcleos)
- Attacker con acceso a la red — no al sistema operativo del host

### Fuera de scope (PHASE 1)
- APT con persistencia a largo plazo y acceso root al host
- Ataques de canal lateral (timing, power analysis) en hardware sin HSM
- Supply chain attacks al compilador/toolchain (más allá de SHA-256 de libsodium)
- Entornos FIPS 140-2/3 (requiere PHASE 2 + ENT-8)

---

## 7. Referencias

- RFC 5869: HMAC-based Extract-and-Expand Key Derivation Function (HKDF)
- RFC 8439: ChaCha20 and Poly1305 for IETF Protocols
- ADR-013: seed-client y cadena de confianza
- ADR-019: OS hardening y secure deployment
- ADR-020: cifrado y compresión siempre obligatorios
- NIST SP 800-90B: Recommendation for Entropy Sources
- BSI: AIS 20/31 (jitterentropy certification)
- libsodium 1.0.19: https://download.libsodium.org/libsodium/releases/

---

*Última actualización: DAY 97 — 25 marzo 2026*
*Próxima revisión: DAY 105 (PHASE 2 planning)*