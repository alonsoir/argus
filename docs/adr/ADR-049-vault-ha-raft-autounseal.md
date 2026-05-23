# ADR-049 — Vault HA con Raft nativo y roadmap auto-unseal

- **Estado:** En preparación (implementación post-FEDER)
- **Fecha:** 2026-05-23
- **Autor:** Alonso Isidoro Román
- **Revisores:** Consejo de Sabios (pendiente votación formal)
- **Referencias:** ADR-047 (resiliencia en capas), ADR-048 (etcd HA)

---

## Contexto

Vault actualmente corre en modo single-node. Es un SPOF conocido y aceptado transitoriamente, con Falco + cron como resiliencia de primera línea mientras el HA no esté implementado (ver ADR-047).

Adicionalmente, el unseal de Vault en producción es una operación crítica. Tras cualquier reinicio, Vault arranca en estado sellado y requiere unseal antes de poder servir secretos. En single-node con reinicio frecuente, el unseal manual es un cuello de botella operacional. En HA con Raft, los reinicios de nodos individuales son raros, pero el mecanismo de unseal sigue siendo relevante para arranques del cluster completo.

---

## Decisión

### Vault HA con Raft integrado

Vault soporta Raft como storage backend nativo desde la versión 1.4, eliminando la dependencia de Consul o cualquier otro sistema de coordinación externo.

**Cluster de 3 nodos Vault** con Raft integrado. El modelo es análogo al de ADR-048 para etcd: mismo algoritmo, mismas propiedades de consistencia fuerte, misma tolerancia a 1 fallo con quórum de 2 de 3.

**Sin Consul.** Consul añadiría un tercer sistema de coordinación distribuida a un entorno donde ya tenemos etcd con Raft. Con Vault Raft integrado, Consul es innecesario.

### Unseal — decisión por fases

#### Fase FEDER: Shamir distribuido (manual, seguro, soberano)

Vault genera un conjunto de key shares mediante el algoritmo de Shamir Secret Sharing. El threshold mínimo de shares para reconstruir la master key se distribuye entre personas con roles distintos en la organización.

Con HA Raft, el unseal manual solo es necesario en reinicios completos del cluster, que deben ser eventos excepcionales. Los reinicios de nodos individuales son gestionados por el quórum.

**Ventajas para el scope FEDER:**
- Gratis, sin dependencias externas
- Soberanía total — ningún proveedor externo tiene acceso a las claves
- Demostrable en una demo sin hardware adicional
- Cumple ENS, GDPR, NIS2 sin argumentación adicional

#### Fase post-FEDER: YubiHSM2 para auto-unseal

Vault soporta auto-unseal mediante PKCS#11, que YubiHSM2 implementa nativamente.

**YubiHSM2:**
- Hardware físico dedicado a operaciones criptográficas
- Las claves nunca salen del dispositivo en texto plano
- FIPS 140-2 Level 3
- Coste aproximado: 650€
- La raíz de confianza está en hardware físico que el hospital posee y controla físicamente

**Por qué no Cloud KMS:**
Cloud KMS (AWS KMS, Google Cloud KMS, Azure Key Vault) delega la raíz de confianza al proveedor. Técnicamente, el proveedor podría acceder o revocar la capacidad de unseal. Esto es un riesgo regulatorio y político inaceptable para infraestructura crítica hospitalaria bajo regulación española y europea (ENS, NIS2, GDPR). aRGus se posiciona como solución de soberanía digital europea — Cloud KMS contradice ese posicionamiento.

**Argumento comercial del YubiHSM2:**
"La clave criptográfica maestra de su sistema vive en hardware certificado FIPS 140-2 en una caja fuerte en sus propias instalaciones. Ningún proveedor externo tiene acceso a ella." Este argumento vale más que el coste del dispositivo en una reunión con el responsable TI de un hospital o con un auditor ENS.

**Custodia del YubiHSM2:**
El dispositivo debe almacenarse en condiciones de seguridad física adecuadas al entorno del cliente. En un servidor dedicado con acceso físico controlado. El dispositivo es la raíz de confianza física del sistema.

---

## Lo que NO se usa

**Sin ZooKeeper.** Vault Raft integrado no requiere coordinación externa.

**Sin Consul.** Innecesario con Vault Raft como storage backend.

**Sin Cloud KMS.** Incompatible con el posicionamiento de soberanía digital de aRGus.

---

## Vault sealed vs Vault stopped — distinción operacional

Son estados con semántica diferente que requieren respuesta diferente:

| Estado | Causa típica | Recuperación | Notificación |
|--------|-------------|--------------|--------------|
| Vault stopped | Caída de proceso, reinicio de nodo | Automática via Falco+cron, luego unseal | Discord: "Vault caído, recuperando" |
| Vault sealed | Detección de intrusión, unseal keys comprometidas, operación manual deliberada | Manual con key shares Shamir | Discord: "Vault sellado — requiere unseal manual. Posible incidente de seguridad." |

Un Vault sellado no se recupera automáticamente. Requiere intervención humana con las key shares físicas. Esta distinción debe estar implementada en las reglas Falco y en el sistema de notificación Discord para que el administrador sepa exactamente qué acción tomar.

---

## Deudas técnicas relacionadas

| Deuda | Prioridad | Descripción |
|-------|-----------|-------------|
| DEBT-VAULT-AUTOUNSEAL-001 | Post-FEDER | Implementar auto-unseal con YubiHSM2 via PKCS#11 |
| DEBT-ALERTING-VAULT-001 | P2 | Migrar credenciales Discord/Telegram a Vault (actualmente en Jinja2 con valores naive) |

---

## Estado transitorio hasta implementación

Mientras el HA no esté implementado, la resiliencia de Vault se basa en:

1. **Falco** monitorizando el proceso Vault
2. **cron** intentando recuperación automática ante caída detectada (idempotente)
3. **Discord** notificando al administrador si las capas anteriores no resuelven el fallo

En caso de Vault sellado, Falco debe distinguir el estado sealed del stopped y notificar de forma diferenciada. Esto es un requisito de implementación para las reglas Falco de DAY 161.

---

## Consecuencias

- La decisión de usar Vault Raft (no Consul) está comprometida desde este ADR.
- La decisión de usar YubiHSM2 para auto-unseal post-FEDER está comprometida desde este ADR — elimina el debate futuro sobre Cloud KMS.
- Las pruebas de caos de DAY 161 se ejecutan sobre Vault single-node transitorio y establecen la línea base de comportamiento.
- Las reglas Falco deben distinguir Vault stopped de Vault sealed desde el principio — no es un refinamiento posterior.
- El posicionamiento comercial de soberanía digital de aRGus queda reforzado por esta decisión: ningún secreto del hospital depende de infraestructura de terceros.
