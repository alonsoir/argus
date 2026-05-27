Mis respuestas:

---

**Q1 — Compilación condicional vs dos binarios**

`#ifdef ARGUS_VAULT_ENABLED` es la opción correcta. Dos binarios separados crean divergencia silenciosa garantizada — cualquier fix en la ruta común hay que aplicarlo dos veces, y tarde o temprano uno se queda atrás. El riesgo del `#ifdef` es real pero manejable: la disciplina es que el flag solo afecta al **punto de entrada de crypto**, no se dispersa por todo el código. `VaultClient` y `seed-client` son intercambiables en la misma interfaz — si en el futuro duele, extraes una clase base `CryptoProvider` y ambas implementaciones heredan. Pero no lo hagas antes de necesitarlo.

**Q2 — Orden de migración**

`etcd-server` primero es correcto por ser el bootstrap especial. Después el orden natural es: `sniffer` (más aislado, no depende de otros componentes para arrancar), luego `ml-detector`, `firewall-acl-agent`, `rag-ingester`, `rag-security`. El criterio es: primero los que tienen menos dependencias de otros componentes en el momento del arranque. `rag-security` al final porque depende de que el resto del pipeline esté operativo.

**Q3 — `register_etcd_status` en bootstrap**

Sí, fichero local es la solución correcta. La ruta propuesta `/run/argus/etcd-crypto-status.json` es buena para dev, pero en producción edge ese fichero desaparece en reinicio. Mi propuesta: `/etc/ml-defender/etcd-server/crypto-status.json` con permisos 0644 — persistente, legible por otros componentes si necesitan consultarlo antes de que etcd esté listo, y consistente con la estructura de paths que ya usa el proyecto. etcd escribe ahí su propio estado; los demás componentes escriben en etcd normalmente.

**Q4 — Cache tmpfs y `vagrant destroy`**

Cache persistente en producción es imprescindible. La distinción correcta es:

- `dev`: `/run/argus/crypto-cache/` — tmpfs, se pierde en destroy, correcto para EMECAS
- `prod`: `/etc/ml-defender/{component}/crypto-cache/` — persistente, permisos 0600, propiedad de `argus:argus`

El `VaultClientConfig` ya tiene `cache_dir` como campo configurable — solo hay que que Ansible/Jinja2 inyecte el path correcto según el ambiente. No requiere cambios en el código C++, solo en la configuración desplegada. DEBT-CRYPTO-CACHE-PERSIST-001 para registrarlo.

**Q5 — Separador open-core**

`ARGUS_VAULT_ENABLED` es necesario pero no suficiente como único separador. Mi propuesta de línea de separación:

- **Community**: `seed-client`, pipeline C++20 completo, AppArmor, Falco reglas básicas, `argus-network-isolate`
- **Enterprise**: `ARGUS_VAULT_ENABLED` (Vault), `ARGUS_NEO4J_ENABLED` (graph visualization), `ARGUS_OPENCANARY_ENABLED` (honeypot/deception), `ARGUS_FALCO_ADVANCED_ENABLED` (actuation layer, JA3/JA4, forensic chain Ed25519)

Falco básico va en community porque es defensa. Falco actuation/deception es enterprise porque requiere infraestructura adicional y tiene implicaciones legales (admisibilidad forense). Neo4j y OpenCanary claramente enterprise — requieren servidor central con recursos significativos. El argumento FEDER se fortalece: la convocatoria financia el desarrollo enterprise sobre una base community ya publicada en arXiv.

---

Cuando tengas el feedback consolidado del resto del Consejo, integramos y actualizamos la documentación.