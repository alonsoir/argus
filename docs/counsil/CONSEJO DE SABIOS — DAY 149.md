# CONSEJO DE SABIOS — DAY 149
## Informe: Arquitectura CI/CD Criptográfica — Jenkins + Vault + common/vault_client

**Fecha:** 12 Mayo 2026  
**Autor:** Alonso Isidoro Román  
**Para:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral  
**ADRs relacionados:** ADR-013, ADR-020, ADR-021, ADR-004  
**Prioridad:** P0 pre-FEDER  

---

## 1. CONTEXTO — QUÉ HEMOS CONSTRUIDO HOY (DAY 149)

Antes de la pregunta principal, el estado del arte tras DAY 149:

- **DEBT-PARQUET-SCHEMA-001 CERRADA:** Schema Arrow v1.0 para ml_detector_events (15 fields) y firewall_acl_events (7 fields). 207,122 filas convertidas. Ratio compresión 11-12x. Roundtrip: 53+1 PASSED. Vault dev mode prototipo K_pseudo + HMAC-SHA256: determinismo OK, aislamiento OK, post-destroy irrecuperable OK.
- **Infraestructura CI/CD:** Ansible + Jinja2 templates para sniffer.json, ml_detector_config.json, rag_logger_config.json. Playbook deploy_configs.yml ejecutado en VM: 9 OK, 3 changed, 0 failed. Jenkinsfile con stage Deploy Configs. Vault + Ansible + Jinja2 + Jenkins en Vagrantfile dev. Vault runtime en Vagrant prod (ADR-039 BSR axiom respetado).
- **Paper:** Abstract v24 "architecturally complementary by design". v3 en arXiv (submit/7576269).
- **Main:** v0.7.2 @ f2e2ebd → 81490fcb (5 PRs mergeados).

---

## 2. DISEÑO NAIVE INICIAL (Alonso, DAY 149, ~09:00)

Durante la sesión de hoy emergió la necesidad de mover la generación de material criptográfico del portátil del founder al pipeline CI/CD. El diseño inicial propuesto fue:

```
Jenkins (origen)
├── Selecciona entropy source del filesystem donde corre
├── Genera seeds distintas por ambiente + componente
├── PUT → Vault(argus/{env}/seeds/{component})
├── Deriva keypairs Ed25519 en memoria
├── Configura JSON de cada componente con vault_path
└── Si falla → ABORT. Todo o nada.

common/vault_client (módulo C++ interno, no plugin)
├── Al arrancar: GET seed desde Vault
├── Deriva keypair Ed25519 en memoria (libsodium)
├── Registra en etcd: "component X online, crypto ready"
└── Si falla → exit(1). ZeroMQ no abre hasta crypto OK.

etcd-server (coordinador de rotación)
├── Verifica topología completa antes de rotar
├── Solicita nueva seed a Jenkins/Vault cuando toca
└── Coordina rollout componente a componente
```

**Principio fundamental confirmado:** TODO O NADA. El pipeline no arranca sin criptografía completa. No existe modo degradado sin crypto.

---

## 3. ANÁLISIS ADVERSARIAL (Claude, DAY 149)

### P0 — Críticos (bloquean FEDER si no se resuelven)

**P0.1 — Jenkins como SPoF criptográfico**  
Jenkins comprometido = todas las seeds de todos los ambientes comprometidas. El problema del portátil del founder se traslada a Jenkins.  
*Mitigación propuesta:* Jenkins solo aporta entropy al proceso. Vault genera la seed internamente con su propio RNG certificado (`vault write sys/tools/random`). Jenkins nunca ve la seed completa — solo dispara el proceso.

**P0.2 — Estado inconsistente ZeroMQ pre-crypto**  
`exit(1)` en el componente no es suficiente si el componente upstream ya abrió el socket y envió mensajes antes de que el downstream completara crypto. El pipeline puede quedar en estado inconsistente.  
*Mitigación propuesta:* etcd como barrera de sincronización pre-arranque. Nadie abre ZeroMQ hasta que etcd confirma `crypto_ready` de TODOS los componentes. El orden de inicialización es: Vault → seed → keypair → etcd register → ZeroMQ open.

**P0.3 — Vault inmem rompe EMECAS**  
Vault dev mode usa backend `inmem`. Cada `vagrant destroy -f` destruye todas las seeds. El EMECAS ritual (`vagrant destroy -f && vagrant up && make bootstrap && make test-all`) destruye la VM y requiere re-provisionar toda la criptografía en cada ciclo. Esto rompe la automatización actual.  
*Mitigación propuesta:* Vault con backend `file` incluso en dev. El EMECAS debe incluir `make provision-crypto` como paso obligatorio después de `vagrant up`.

### P1 — Importantes

**P1.1 — Disponibilidad vs TODO O NADA en infraestructura crítica**  
Si Vault está temporalmente caído cuando un componente necesita reiniciarse (systemd restart, OOM killer), el componente no arranca. En un hospital, un NDR offline durante una ventana de ataque puede ser peor que un NDR con crypto degradada.  
*Tensión de diseño real:* ¿TODO O NADA absoluto vs cache cifrada en tmpfs con TTL?  
*Propuesta:* cache cifrada en tmpfs (no en disco) con TTL configurable. Si tmpfs tiene la seed y Vault está caído, el componente puede arrancar. Si tmpfs también está vacío → TODO O NADA.

**P1.2 — etcd comprometido puede triggear rotación falsa**  
Si etcd es comprometido, el atacante puede disparar una rotación coordinada en el momento de mayor vulnerabilidad, poniendo a todos los componentes en estado de renegociación simultánea — ventana de ataque perfecta. O puede bloquear la rotación indefinidamente.  
*Mitigación:* etcd coordina el timing pero NO tiene acceso a las seeds. Solo dice "es hora". Jenkins/Vault son los únicos que generan y custodian material criptográfico.

**P1.3 — Assert dev≠prod no implementado**  
No hay ningún mecanismo que aserte empíricamente que `seed_dev != seed_prod` antes de almacenarlas en Vault, especialmente si Jenkins corre en el mismo servidor para ambos ambientes.  
*Mitigación:* `provision_crypto.sh` hace assert explícito y falla si seeds son iguales. Trivial de implementar, crítico de tener.

### P2 — Deuda técnica aceptable

**P2.1 — Latencia de arranque:** cada componente hace una llamada HTTP a Vault en el arranque.  
**P2.2 — Ventana de incompatibilidad durante rotación:** durante el rollout, hay un momento en que sniffer tiene clave nueva y ml-detector tiene la vieja. etcd debe serializar el proceso.  
**P2.3 — key_rotation_hours visible en group_vars:** información operacional que un atacante puede usar para timing attacks.

### Resumen

| Problema | Severidad | ¿Bloquea FEDER? |
|---|---|---|
| Jenkins SPoF criptográfico | P0 | No — Vault RNG mitiga |
| Estado inconsistente ZeroMQ | P0 | Sí — necesita barrera etcd |
| Vault inmem rompe EMECAS | P0 | Sí — necesita backend file |
| TODO O NADA vs disponibilidad | P1 | No — decisión de diseño |
| etcd comprometido | P1 | No — etcd no toca seeds |
| Assert dev≠prod | P1 | No — trivial añadir |
| Latencia arranque | P2 | No |
| Ventana rotación parcial | P2 | No |
| key_rotation_hours visible | P2 | No |

---

## 4. ARQUITECTURA PROPUESTA (post-análisis)

```
JENKINS (entropy provider + orquestador)
├── NO genera la seed directamente
├── Llama a Vault API: vault write sys/tools/random bytes=32
├── Vault genera seed con su RNG certificado
├── Jenkins almacena path en JSON de cada componente
├── Assert: seed_dev != seed_prod (fallo = abort pipeline)
└── Si cualquier paso falla → ABORT. Pantalla. Todo o nada.

VAULT (única autoridad criptográfica)
├── argus/dev/seeds/{component}   ← Vault genera, Jenkins dispara
├── argus/prod/seeds/{component}
├── Backend: file (no inmem) incluso en dev
└── Solo Jenkins escribe. Los componentes solo leen.

common/vault_client (módulo C++20 interno, en common/)
├── Al arrancar: GET seed desde Vault
├── Si Vault OK: deriva keypair en memoria (libsodium)
├── Si Vault KO y tmpfs tiene seed con TTL válido: usa cache
├── Si Vault KO y tmpfs vacío: exit(1) inmediato
├── Registra en etcd: "crypto_ready: component_id"
└── ZeroMQ no abre hasta ACK de etcd

etcd-server (coordinador — SIN acceso a seeds)
├── Barrera pre-arranque: espera crypto_ready de TODOS
├── Coordina rotación: verifica topología completa primero
├── Notifica "rotation_pending" a cada componente
├── Espera ACK de TODOS antes de marcar rotation_done
└── Timeout → rollback + alerta. NUNCA rotación parcial.

FLUJO DE ARRANQUE (invariante):
Vault → seed → keypair (memoria) → etcd register crypto_ready
→ etcd confirma ALL crypto_ready → ZeroMQ open
Cualquier fallo → exit(1) + log claro + systemd FailureAction=poweroff
```

**Relación con ADRs existentes:**
- **ADR-013 PHASE 2:** `common/vault_client` reemplaza `seed-client` que leía de disco. Mismo contrato, fuente Vault en lugar de filesystem.
- **ADR-020:** TODO O NADA se fortalece. No existe ruta sin crypto.
- **ADR-021 INVARIANTE-SEED-001:** seed_family compartido en single-node se mantiene. Vault custodia el seed raíz único.
- **ADR-004:** cooldown de rotación (≥ grace_period) sigue aplicando. etcd lo respeta.

---

## 5. ORDEN DE IMPLEMENTACIÓN PROPUESTO

```
DAY 149/150  scripts/jenkins/provision_crypto.sh
├── Vault backend file (no inmem)
├── vault write sys/tools/random → seed por componente
├── Assert seed_dev != seed_prod
└── JSON update con vault_path por componente

DAY 150/151  common/vault_client.{h,cpp}
├── GET seed desde Vault
├── Deriva keypair libsodium en memoria
├── Cache tmpfs con TTL
├── exit(1) si Vault KO y cache vacía
└── etcd register crypto_ready

DAY 151+     Integrar vault_client en cada componente
└── Reemplazar lectura seed.bin de disco

DAY FEDER    etcd rotation coordinator
└── Requiere topología HA completa
```

---

## 6. PREGUNTAS PARA EL CONSEJO

**Q1 — Vault RNG vs entropy externa:**  
¿Es suficiente `vault write sys/tools/random bytes=32` como única fuente de entropy para las seeds de producción, o debemos mezclar entropy externa (getrandom(), RDRAND, TPM) antes de enviarlo a Vault? ¿Qué estándar aplica aquí — NIST SP 800-90A/B/C?

**Q2 — Cache tmpfs: ¿tropieza con TODO O NADA?**  
La cache cifrada en tmpfs con TTL permite que un componente arranque aunque Vault esté temporalmente caído. ¿Esto viola el principio TODO O NADA de ADR-020, o es una extensión razonable del modelo de amenaza dado que tmpfs no sobrevive a un reboot? ¿Hay un modelo de amenaza donde la cache tmpfs sea el vector de ataque?

**Q3 — etcd como barrera pre-arranque: ¿huevo y gallina?**  
etcd-server necesita estar online para que los componentes registren `crypto_ready`. Pero etcd-server también necesita su propio material criptográfico para arrancar. ¿Cómo rompemos este ciclo de dependencia? ¿etcd-server es el único componente que arranca sin barrera etcd, con crypto obtenida directamente de Vault?

**Q4 — Vault backend file en dev: ¿suficiente o necesitamos Vault HA desde el principio?**  
Backend `file` en dev es single-node y sin replicación. Si el fichero se corrompe, se pierden todos los secrets. ¿Es aceptable para dev dado que Jenkins puede re-provisionar? ¿O debemos usar backend `raft` (Vault HA integrado) desde el principio para que dev y prod sean más parecidos?

**Q5 — Rotación coordinada por etcd: ¿cuál es el blast radius mínimo aceptable?**  
Durante la rotación, hay una ventana donde sniffer tiene clave nueva y ml-detector tiene la vieja. ADR-004 define cooldown = grace_period para HMAC keys. ¿El mismo modelo aplica a las ChaCha20 seeds? ¿O la rotación de seeds debe ser atómica (todos o ninguno en el mismo instante), aceptando una micro-ventana de pipeline offline?

**Q6 — `provision_crypto.sh` en Jenkinsfile: ¿stage separado o integrado en bootstrap?**  
¿Debe `provision_crypto.sh` ser un stage independiente en el Jenkinsfile ("Provision Crypto") que puede fallar y detener el pipeline, o debe integrarse en `make bootstrap` como paso obligatorio? La ventaja del stage separado es visibilidad; la del bootstrap integrado es atomicidad.

**Q7 — Seed families (ADR-021) y Vault: ¿paths separados por familia o por componente?**  
ADR-021 define familias de canal (family_A: sniffer↔ml-detector, family_B: ml-detector↔firewall, etc.). En Vault, ¿almacenamos una seed por familia (`argus/dev/families/family_A`) o una seed por componente (`argus/dev/seeds/sniffer`)? La primera respeta el modelo de familias y minimiza el blast radius de un componente comprometido. La segunda es más simple. ¿Cuál recomendáis para la fase FEDER?

---

## 7. LO QUE HAREMOS MAÑANA (DAY 150)

1. Procesar feedback del Consejo sobre Q1-Q7
2. Actualizar ADR-013 con la arquitectura Vault (PHASE 3)
3. Crear ADR-044: CI/CD Crypto Pipeline (Jenkins + Vault + vault_client)
4. Implementar `scripts/jenkins/provision_crypto.sh` (P0.3: Vault backend file)
5. Cerrar DEBT-PARQUET-TIMESTAMP-NS-001 si hay tiempo (firewall-acl-agent ns)

---

## 8. AGRADECIMIENTO

Este diseño emerge directamente de la experiencia operacional de Alonso en Ericsson con pipelines CI/CD de telecomunicaciones, adaptada al modelo de amenaza de infraestructura crítica de aRGus NDR. La pregunta "¿cuál es el blast radius si Jenkins es comprometido?" es la pregunta correcta que cualquier arquitecto de seguridad haría. El Consejo tiene ahora todos los elementos para mejorarla.

