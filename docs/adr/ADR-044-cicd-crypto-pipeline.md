# ── 2. ADR-044 ─────────────────────────────────────────────────────
adr044 = '''# ADR-044 — CI/CD Crypto Pipeline: Jenkins + Vault + common/vault_client

**Estado:** ACEPTADO
**Fecha:** 12 Mayo 2026 (DAY 149)
**Autor:** Alonso Isidoro Román
**Consejo:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral (8/8)
**Relacionado:** ADR-013 (seed-client PHASE 3), ADR-020 (TODO O NADA),
ADR-021 (seed families), ADR-004 (key rotation cooldown)

---

## Contexto

La criptografía de identidad de los componentes se generaba en el portátil
del founder mediante `tools/provision.sh`. Esto viola el principio de
separación entre developer y operaciones, introduce un SPoF humano en la
cadena de confianza, y no escala al modelo de despliegue FEDER donde el
servidor de CI/CD es el origen de todo el material criptográfico.

Este ADR formaliza ADR-013 PHASE 3: el pipeline Jenkins es el nuevo origen
de la entropy, Vault es la única autoridad de custodia, y common/vault_client
es el módulo C++20 que cada componente usa para obtener su material en runtime.

---

## Decisión

### Principio rector: TODO O NADA

**El pipeline no arranca sin criptografía completa y verificada.**
No existe modo degradado sin crypto. No existe override de runtime.

### Actores y responsabilidades

```
JENKINS (entropy provider + orquestador)
├── NO genera la seed directamente
├── Llama vault write sys/tools/random → Vault genera con su CSPRNG
├── Assert: seed_dev != seed_prod (fallo → abort pipeline)
├── Actualiza paths Vault en JSON de cada componente vía Ansible
└── Si cualquier paso falla → ABORT. Log en pantalla. TODO O NADA.

VAULT (única autoridad criptográfica)
├── Genera seeds con su CSPRNG (NIST SP 800-90A)
├── Estructura de paths por familia (ADR-021):
│   argus/{env}/families/family_A/seed  ← sniffer↔ml-detector
│   argus/{env}/families/family_B/seed  ← ml-detector↔firewall
│   argus/{env}/families/family_C/seed  ← firewall↔rag
│   argus/{env}/components/etcd/seed    ← etcd bootstrap especial
├── Backend: file (dev/FEDER), raft (prod post-FEDER)
└── Solo Jenkins escribe. Componentes solo leen.

common/vault_client (C++20, en common/)
├── Al arrancar: GET seed de Vault con timeout 5s
├── Si Vault OK: deriva keypair libsodium en memoria (mlock)
├── Si Vault KO y tmpfs TTL válido: usa cache con log WARN
├── Si Vault KO y cache vacía: exit(1) inmediato
├── Jitter startup: component_index * 500ms + rand(0-1000ms)
├── Registra en etcd: {component, crypto_ready, key_version,
│                      family, fingerprint, timestamp}
└── Heartbeat periódico a etcd post-crypto_ready

etcd-server (coordinador — SIN acceso a seeds)
├── EXCEPCIÓN BOOTSTRAP: arranca sin barrera etcd, seed directa de Vault
├── Barrera pre-arranque: espera crypto_ready de TODOS los componentes
├── Pipeline open: ZeroMQ no se abre hasta broadcast pipeline_open
├── Coordina rotación manual (FEDER): make rotate-crypto
└── Timeout barrera: 5 min → alert + abort
```

### Flujo de arranque invariante

```
1. Vault online (backend file con unseal automático en dev)
2. etcd-server: Vault → seed → keypair (mlock) → self crypto_ready
3. [jitter] sniffer, ml-detector, firewall, rag-ingester, rag-security:
   Vault → seed → keypair (mlock) → etcd register crypto_ready
4. etcd: ALL crypto_ready confirmed → broadcast pipeline_open
5. Componentes: reciben pipeline_open → ZeroMQ open
CUALQUIER FALLO → exit(1) + log claro + systemd FailureAction=poweroff
```

### Cache tmpfs (extensión razonable de ADR-020)

La cache no viola TODO O NADA porque tmpfs no sobrevive reboot.
Permite disponibilidad operacional ante caídas transitorias de Vault.

```
Vault OK → seed fresca → deriva keypair → actualiza cache tmpfs (TTL)
Vault KO + cache TTL válido → deriva keypair desde cache → log WARN
Vault KO + cache expirada → exit(1) → systemd FailureAction=poweroff
```

TTL: 1h dev, 15min prod. Permisos 0700. mlock sobre material derivado.
Registro en etcd: "started_with_cache: true" para auditoría.

### Rotación (FEDER: manual orquestada)

```
make rotate-crypto
  1. etcd notifica rotation_pending a todos
  2. Componentes drenan colas con seed vieja
  3. etcd confirma all_drained
  4. Micro-ventana offline (~segundos)
  5. Jenkins genera nueva seed en Vault
  6. Componentes obtienen nueva seed (tmpfs cache + Vault refresh)
  7. etcd marca rotation_done → pipeline_open con nueva seed
```

Rotación automática continua: post-FEDER.

---

## Implementación

### Orden de desarrollo

```
DAY 150  scripts/jenkins/provision_crypto.sh
         ├── Vault backend file
         ├── vault write sys/tools/random por familia
         ├── assert seed_dev != seed_prod
         └── Jenkinsfile stage Provision Crypto

DAY 151  common/vault_client.{h,cpp}
         ├── GET seed + timeout 5s
         ├── deriva keypair libsodium mlock
         ├── cache tmpfs TTL
         └── etcd register crypto_ready + heartbeat

DAY 152+ Integrar vault_client en 6 componentes
         └── Reemplazar lectura seed.bin de disco (ADR-013 PHASE 1→3)

DAY FEDER etcd rotation coordinator + make rotate-crypto
```

### Estructura Vault

```
argus/
├── dev/
│   ├── families/
│   │   ├── family_A/seed    # ChaCha20 seed sniffer↔ml-detector
│   │   ├── family_B/seed    # ChaCha20 seed ml-detector↔firewall
│   │   └── family_C/seed    # ChaCha20 seed firewall↔rag
│   └── components/
│       └── etcd/seed        # etcd bootstrap seed (no family)
└── prod/ (misma estructura)
```

---

## Deudas registradas

- DEBT-VAULT-ENTROPY-MIXING-001: mezcla entropy externa para prod (P2)
- DEBT-VAULT-HA-001: Vault HA raft para producción real (P1)
- DEBT-CRYPTO-STAMPEDE-001: jitter startup en vault_client (P1)
- DEBT-CRYPTO-AUDIT-FINGERPRINT-001: fingerprint en etcd (P1)
- DEBT-CRYPTO-HEARTBEAT-001: heartbeat periódico etcd (P1)

---

## Consecuencias

**Positivas:**
- Material criptográfico nunca en el portátil del founder
- Vault es la única autoridad — blast radius contenido por familias
- Disponibilidad operacional ante caídas transitorias de Vault
- Pipeline Jenkins auditable y reproducible
- ADR-021 seed families respetado en estructura Vault

**Negativas / limitaciones:**
- Complejidad operacional emergente (advertida por Consejo)
- Rotación automática: post-FEDER
- Sin HSM/TPM en hardware FEDER inicial

---

*Co-authored-by: Consejo de Sabios (8/8 — DAY 149)*
*Alonso Isidoro Román — DAY 149 — 12 Mayo 2026*
'''
open('docs/adr/ADR-044-cicd-crypto-pipeline.md', 'w').write(adr044)
print("docs/adr/ADR-044-cicd-crypto-pipeline.md creado")