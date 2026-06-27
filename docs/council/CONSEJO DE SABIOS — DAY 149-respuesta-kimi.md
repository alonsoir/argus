**Consejo de Sabios — Dictamen DAY 149**

Compañero, este documento es un trabajo de arquitectura de primer orden. Has trasladado correctamente el problema del portátil del founder a un modelo de amenaza distribuido, y el análisis adversarial es quirúrgico. Voy directo a tus siete preguntas.

---

## Q1 — Vault RNG vs. entropy externa

**`vault write sys/tools/random bytes=32` es suficiente.** Vault ya implementa un CSPRNG que cumple NIST SP 800-90A (CTR_DRBG o Hash_DRBG, dependiendo de la versión) y se alimenta de `/dev/urandom`, `getrandom(2)`, y fuentes del kernel. Mezclar entropy externa manualmente (RDRAND, TPM) antes de enviarla a Vault es **cargo cult cryptography**: no aumentas la entropía real si Vault ya hce el mixing correcto.

**Excepción:** Si tu modelo de amenaza incluye un adversario que controla el kernel del host de Vault, entonces necesitas un HSM o TPM como fuente de entropy independiente del SO. Para FEDER, asume que el host de Vault es trusted. Si más adelante escalas a SOC 2 Type II o ENS, entonces sí, añade HSM.

**Veredicto:** Usa `sys/tools/random`. No compliques.

---

## Q2 — Cache tmpfs: ¿violación de TODO O NADA?

**No viola ADR-020. Es una extensión razonable.**

El principio TODO O NADA protege contra:
- Arranque sin crypto (evitado: tmpfs tiene la seed).
- Persistencia de material criptográfico en disco (evitado: tmpfs es volátil).
- Degradación silenciosa (evitado: el componente logea explícitamente "Vault unreachable, using tmpfs cache TTL=X").

**Modelo de amenaza del vector tmpfs:** Un atacante con root en el nodo puede leer `/proc/{pid}/mem` de todos modos, con o sin tmpfs. La cache tmpfs no expande la superficie de ataque más allá de "compromiso total del nodo". Si el atacante tiene root, ya ganó; la cache no empeora nada.

**Condición:** La cache debe estar en `tmpfs` con `mode=0700`, no en `/tmp` compartido. Y el TTL debe ser corto: 1h para dev, 15min para prod.

---

## Q3 — etcd huevo y gallina

**etcd-server es el primer mover y arranca sin barrera etcd.**

El ciclo de dependencia se rompe así:

```
etcd-server:
  1. Lee su seed directamente de Vault (no via etcd, obviamente)
  2. Deriva su keypair
  3. Abre su listener Raft
  4. Ahora es "coordinador disponible"

Resto de componentes:
  1. Esperan a que etcd-server responda a health checks
  2. Obtienen seed de Vault (o tmpfs cache)
  3. Registran crypto_ready en etcd
  4. Esperan ALL crypto_ready
  5. Abren ZeroMQ
```

**Nota:** etcd-server no necesita `vault_client` como tal; necesita un bootstrap mínimo que lea un `etcd_seed` de Vault via HTTPS directo. Esto puede ser un script `etcd-crypto-bootstrap.sh` que corre antes del binario etcd, escribe la seed en tmpfs, y el binario etcd la lee desde ahí.

---

## Q4 — Vault backend file en dev

**Sí, es suficiente. No uses raft en dev.**

La paridad dev/prod es un ideal, no un mandamiento. El backend `file` en dev tiene ventajas operativas innegables:
- Arranque instantáneo.
- Sin complejidad de cluster.
- Fácil de destruir y recrear (EMECAS).

**Mitigación de corrupción:** `make bootstrap` debe incluir `vault operator init` + unseal automático con `VAULT_LOCAL_CONFIG`. Si el fichero se corrompe, `vagrant destroy -f && vagrant up` lo reconstruye en 90 segundos. Eso es aceptable para dev.

**Para prod:** Sí, `raft` o `consul` backend. Pero eso es post-FEDER.

---

## Q5 — Blast radius mínimo en rotación de seeds

**Las seeds de cifrado de canal (ChaCha20) NO deben rotar con el modelo "cooldown" de ADR-004.**

Las claves HMAC (ADR-004) son para pseudonimización: puedes tener dos versiones válidas porque los datos antiguos siguen siendo verificables. Las seeds de cifrado de canal son para comunicación en tiempo real: **no puedes tener dos claves válidas simultáneamente** sin que el receptor no sepa cuál usar.

**Modelo correcto para seeds de canal:**

| Fase | Estado |
|------|--------|
| T0 | Seed vN activa en todos los componentes |
| T1 | etcd notifica "rotation_scheduled" |
| T2 | Todos los componentes drenan colas en vN |
| T3 | etcd confirma "all drained" |
| T4 | **Pipeline offline micro-ventana** (~segundos) |
| T5 | Seed vN+1 activa atómicamente en todos |
| T6 | Pipeline online |

Para FEDER, la solución más simple es: **la rotación de seeds requiere ventana de mantenimiento programada.** No es automática ni continua. Es un `make rotate-crypto` que orquesta el apagado ordenado, rotación, y rearranque. Eso elimina la ventana de incompatibilidad.

**Veredicto:** No implementes rotación automática de seeds para FEDER. Implementa rotación manual orquestada.

---

## Q6 — `provision_crypto.sh`: stage separado o integrado

**Stage separado en Jenkinsfile: "Provision Crypto".**

La visibilidad es más importante que la atomicidad en este caso. Si `provision_crypto` falla, quieres que el dashboard de Jenkins muestre un stage rojo con nombre explícito, no un `make bootstrap` genérico que falló en paso 47 de 89.

**Pipeline sugerido:**
```groovy
stage('Provision Crypto') {
    steps {
        sh 'scripts/jenkins/provision_crypto.sh'
    }
}
stage('Bootstrap') {
    steps {
        sh 'make bootstrap'
    }
}
stage('Test All') {
    steps {
        sh 'make test-all'
    }
}
```

Si Provision Crypto falla, los stages siguientes no ejecutan (TODO O NADA). La atomicidad está preservada por el pipeline, no por un script monolítico.

---

## Q7 — Seed families: ¿paths por familia o por componente?

**Por familia (`argus/dev/families/family_A`).** Esto es arquitectónicamente correcto y de seguridad superior.

Razones:
1. **ADR-021** define familias como unidad de aislamiento criptográfico. Viol esa abstracción almacenando por componente.
2. **Blast radius:** Si `sniffer` es comprometido y las seeds están por componente, el atacante obtiene solo la seed de `sniffer`. Pero `sniffer` necesita la seed de `family_A` para hablar con `ml-detector`. Si almacenas por componente, necesitas duplicar la seed de la familia en cada componente, o tener un mapping componente→familia que complica el código.
3. **Simplicidad operativa:** `vault read argus/dev/families/family_A/seed` es un contrato limpio. El componente sabe su familia por configuración estática (`family: "family_A"`), no necesita lógica de lookup.

**Estructura de Vault propuesta:**
```
argus/
  dev/
    families/
      family_A/
        seed        ← ChaCha20 seed para sniffer↔ml-detector
        rotation_at ← metadata
      family_B/
        seed        ← ChaCha20 seed para ml-detector↔firewall
    global/
      ca_cert
      wrapping_key
```

---

## Resumen de acciones para DAY 150

| Prioridad | Tarea | Justificación |
|-----------|-------|---------------|
| **P0** | Implementar barrera etcd pre-arranque (P0.2) | Sin esto, el pipeline puede arrancar en estado inconsistente. Es el único P0 real que queda. |
| **P0** | `provision_crypto.sh` con Vault backend file | Desbloquea EMECAS. |
| **P1** | `common/vault_client` con tmpfs cache + TTL | Disponibilidad operativa en infraestructura crítica. |
| **P1** | Definir paths Vault por familia (Q7) | Contrato limpio, seguro, compatible con ADR-021. |
| **P2** | Assert `seed_dev != seed_prod` | Trivial, pero hazlo. |
| **P2** | Rotación manual orquestada (no automática) | Para FEDER, la simpleza vence a la sofisticación. |

---

**Una nota final sobre el documento:** Tu análisis de P1.1 (disponibilidad vs. TODO O NADA) es el mejor ejemplo de tensión de diseño que he visto en este proyecto. La cache tmpfs es la respuesta correcta. No dejes que la pureza del principio mate la utilidad del sistema en un hospital a las 3 AM.

*El Consejo aprueba la dirección. Que el commit de mañana incluya la barrera etcd.* 🛡️