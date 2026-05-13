**Consejo de Sabios — Dictamen DAY 150**

Compañero, el trabajo de hoy es de primer orden. ADR-044 ya no es un borrador; es infraestructura operativa. El email a Caro Lindo es estratégicamente correcto (el paraguas UEx/INCIBE para red team es la única vía ética y legal para generar datasets de amenazas reales). Voy directo a tus cinco preguntas.

---

## Q1 — `#ifdef` vs. dos binarios: ¿Cuál es más mantenible?

**Ni `#ifdef` espagueti ni dos binarios. El patrón correcto es una interfaz abstracta común con inyección de dependencias.**

Tu código actual tiene dos implementaciones: `seed-client` (community) y `VaultClient` (enterprise). El riesgo de `#ifdef ARGUS_VAULT_ENABLED` es real: divergencia silenciosa, código imposible de leer, y tests que solo compilan una ruta en CI.

**Arquitectura recomendada:**

```cpp
// common/crypto_provider.h — interfaz común, sin #ifdef
class CryptoProvider {
public:
    virtual ~CryptoProvider() = default;
    virtual KeyPair derive_keypair(const std::string& family, 
                                    const std::string& component) = 0;
    virtual std::string fingerprint(const PublicKey& pk) = 0;
};

// seed_file_provider.cpp — community
class SeedFileProvider : public CryptoProvider { ... };

// vault_provider.cpp — enterprise
class VaultProvider : public CryptoProvider { ... };

// factory — decisión en un solo punto
std::unique_ptr<CryptoProvider> CryptoProvider::create(Config cfg) {
    if (cfg.vault_enabled) return std::make_unique<VaultProvider>(cfg);
    return std::make_unique<<SeedFileProvider>(cfg);
}
```

**Implicaciones:**
- Los 6 componentes no ven `#ifdef`. Solo llaman a `CryptoProvider::create()`.
- El flag CMake `ARGUS_VAULT_ENABLED` solo controla qué `.cpp` se compila y linka, no hay macros en headers de componentes.
- CI/CD debe compilar **ambas** configuraciones en paralelo (`ON` y `OFF`). Si un PR rompe community, el build rojo lo detecta inmediatamente. Esto elimina la divergencia silenciosa.

**Veredicto:** Refactoriza `vault_client.h` + `seed-client` para implementar la interfaz común **antes** de integrar en `etcd-server`. Es 2 horas de trabajo que ahorran 20 horas de debug en el futuro.

---

## Q2 — Orden de migración de componentes

**etcd-server primero es correcto e inevitable.** Pero el orden posterior debe respetar el **flujo de datos**, no solo la jerarquía criptográfica.

| Orden | Componente | Justificación | Riesgo |
|-------|-----------|---------------|--------|
| **1** | `etcd-server` | Trust anchor. Sin él no hay barrera. | Bajo: no procesa tráfico de red. |
| **2** | `sniffer` + `ml-detector` | Core del pipeline de detección. Ambos pueden migrarse en paralelo porque son independientes criptográficamente (familias distintas o misma familía, pero sin dependencia funcional). | **Alto en sniffer**: si `VaultClient` bloquea el arranque >5s, el sniffer pierde paquetes iniciales. La inicialización criptográfica debe completarse **antes** de `pcap_open_live()` / `AF_PACKET`. |
| **3** | `firewall-acl-agent` | Depende funcionalmente de `ml-detector` (recibe alertas para actuar), pero criptográficamente es independiente. | Medio: si ml-detector no está listo, firewall no tiene alertas que procesar, pero esto ya es cierto hoy. |
| **4** | `rag-ingester` | No crítico para detección en tiempo real. | Bajo. |
| **5** | `rag-security` | Infraestructura de soporte. | Bajo. |

**Nota crítica sobre `sniffer`:** Es el único componente donde la latencia de arranque importa. Un corte de luz en un hospital seguido de rearranque debe tener el sniffer capturando en <2s. Si `VaultClient::fetch_crypto_material()` tarda 5s (timeout) + jitter 4s (stagger) = 9s, esos 9s son ciegos de red.

**Mitigación:** El sniffer debe hacer **pre-fetch criptográfico** en un hilo separado durante el bootstrap, o mejor: el systemd unit del sniffer debe tener `Type=notify` y `NotifyAccess=all`, y no notificar `READY=1` hasta que crypto esté lista. Pero el socket de captura se abre inmediatamente en modo "capturar y bufferizar", sin descifrar/verificar hasta que crypto esté lista. Si tu pipeline no descifra en el sniffer (solo captura), esto no aplica. Si el sniffer firma los frames, sí aplica.

**Veredicto:** Orden aceptado, pero prioriza la migración de `sniffer` con medición de latencia de arranque. Si supera 2s, optimiza el path.

---

## Q3 — `register_etcd_status` sin etcd disponible en bootstrap

**NO uses fichero local en `/run`. Eso es un hack que rompe la coherencia del sistema.**

La solución correcta es que `etcd-server` use un **cliente etcd local** contra sí mismo:

```cpp
// etcd-server bootstrap (pseudocódigo)
int main() {
    // 1. Crypto material desde Vault (sin barrera)
    auto crypto = VaultClient::fetch_crypto_material();
    
    // 2. Arrancar servidor Raft (escucha en 127.0.0.1:2379 y eth1:2379)
    etcd_server.start();
    
    // 3. Ahora etcd está online. Usar cliente local loopback.
    EtcdClient local_client("127.0.0.1:2379");
    local_client.put("/argus/crypto_ready/etcd-server", 
                     json{crypto.fingerprint, crypto.key_version});
    
    // 4. El coordinador (un watcher o el propio etcd-server) cuenta crypto_ready
    //    de todos los componentes, incluido él mismo.
}
```

**Ventajas:**
- Un solo mecanismo de registro (`put` en etcd) para todos los componentes.
- No hay estado split-brain entre fichero local y etcd.
- Los demás componentes no necesitan saber que etcd-server es especial; solo leen la key `/argus/crypto_ready/*` y esperan N=6 entries.

**La barrera "ALL crypto_ready"** la implementa un coordinador (puede ser un script `make bootstrap` o un componente `orchestrator` minimalista):
```bash
# make bootstrap espera 6 crypto_ready
until etcdctl get /argus/crypto_ready/ --prefix | wc -l -eq 6; do
    sleep 1
done
echo "ALL crypto_ready → pipeline open"
```

**Veredicto:** etcd-server se registra en etcd via loopback. Nada de ficheros locales. La barrera es uniforme.

---

## Q4 — Cache tmpfs vs. persistente en producción edge

**Tu diagnóstico es correcto: tmpfs en prod edge es una vulnerabilidad operativa, no una virtud de seguridad.**

Escenario: Hospital General de Badajoz, corte de luz 15 minutos. Nodo edge reinicia. `/run` se vacía. Vault central está en Madrid. La WAN tarda 3 minutos en recuperarse. El nodo edge no arranca sin Vault → NDR offline durante 3 minutos → ventana de ataque sin detección.

**Esto viola el principio de misión crítica** (ADR-0043, restricción no negociable: *"el nodo edge no puede degradar su capacidad de detección"*).

**Solución: cache persistente cifrada en disco, con TTL estricto.**

```yaml
# vault_client_config.json (generado por Ansible/Jinja2)
cache:
  dev:
    path: "/run/argus/crypto-cache"      # tmpfs, se pierce en destroy
    ttl_seconds: 3600                      # 1h
  prod:
    path: "/var/lib/argus/crypto-cache"  # ext4/xfs, cifrado con LUKS/dm-crypt
    ttl_seconds: 900                     # 15min
    permissions: "0600"
    encrypted: true                        # requiere filesystem cifrado o fscrypt
```

**Condiciones:**
- El disco del nodo edge **ya debe estar cifrado** (LUKS, BitLocker, o filesystem nativo cifrado). Si no lo está, cache persistente = material criptográfico en disco plano = compromiso físico.
- El TTL sigue funcionando: si el archivo de cache tiene `mtime` > TTL, se rechaza. Un corte de luz de 2 horas = cache rechazada = necesita Vault.
- En dev, Ansible genera `path: /run/argus/crypto-cache` (tmpfs). En prod, `path: /var/lib/argus/crypto-cache` (persistente). El código C++ no cambia; solo lee la ruta de config.

**¿Violación de TODO O NADA?** No. El principio protege contra arranque sin crypto. La cache persistente **es crypto** (seed cifrada o keypair cifrado con clave de filesystem). No es un modo degradado; es un modo de recuperación ante desastre operativo.

**Veredicto:** Implementa cache persistente para prod. tmpfs solo para dev. Configurable via Ansible/Jinja2. Requisito previo: disco cifrado en nodos edge (documentar en ADR-044 o ADR-045).

---

## Q5 — Open-core: ¿Es suficiente `ARGUS_VAULT_ENABLED` como único separador?

**No. Un único flag monolítico es insuficiente para una estrategia open-core sostenible.**

Community edition debe ser **funcionalmente completa para un NDR local**: detecta, alerta, bloquea. Enterprise debe añadir **governance, memoria histórica, y orquestación**.

**Propuesta de features granular:**

| Feature | Community | Enterprise | Justificación |
|---------|-----------|------------|---------------|
| `ARGUS_FEATURE_VAULT` | OFF | ON | Crypto governance (ADR-044) |
| `ARGUS_FEATURE_NEO4J` | OFF | ON | Memoria episódica distribuida (ADR-0043) |
| `ARGUS_FEATURE_FEDERATED_LEARNING` | OFF | ON | Agregación de modelos (ADR-038) |
| `ARGUS_FEATURE_FALCO` | OFF | ON | Respuesta automatizada/orquestada |
| `ARGUS_FEATURE_OPENCANARY` | OFF | ON | Honeypot deception avanzada |
| `ARGUS_FEATURE_RAG_LLM` | OFF | ON | Análisis LLM, requiere GPU/central |

**Meta-flag:**
```cmake
option(ARGUS_EDITION_ENTERPRISE "Enable all enterprise features" OFF)
if(ARGUS_EDITION_ENTERPRISE)
    set(ARGUS_FEATURE_VAULT ON)
    set(ARGUS_FEATURE_NEO4J ON)
    set(ARGUS_FEATURE_FEDERATED_LEARNING ON)
    # ...
endif()
```

**Por qué esto importa para FEDER:**
El evaluador FEDER (22-Sep-2026) debe ver una contribución científica clara. Si todo el código es "enterprise" y la community es un cascarón vacío, el valor de la investigación se diluye. La community edition debe ser lo suficientemente robusta como para que un hospital pequeño la despliegue sin infraestructura central. Eso demuestra que el core ML (F1=0.9985) es independiente de la gobernanza enterprise.

**Veredicto:** Define los 6 features arriba **antes** de integrar `VaultClient` en todos los componentes. Si no lo haces ahora, tendrás que refactorizar `#ifdef` esparcidos más tarde. Es 1 día de trabajo que ahorra 1 semana de deuda.

---

## Resumen de acciones para DAY 151

| Prioridad | Tarea | Justificación |
|-----------|-------|---------------|
| **P0** | Refactor `seed-client` + `VaultClient` → interfaz `CryptoProvider` | Bloquea la integración limpia en componentes. |
| **P0** | Integrar `etcd-server` con `VaultProvider` via loopback | Bootstrap especial, pero sin hacks de fichero local. |
| **P1** | Configurar cache persistente `/var/lib/argus/crypto-cache` para prod | Misión crítica ante cortes de luz. |
| **P1** | Definir features granular (VAULT, NEO4J, FL, FALCO, etc.) | Arquitectura open-core sostenible. |
| **P1** | Medir latencia de arranque de `sniffer` con `VaultProvider` | Si >2s, requiere optimización. |
| **P2** | Implementar `register_etcd_status` real + keepalive | DEBT-CRYPTO-HEARTBEAT-001. |

**Una nota final:** Tu decisión de "open-core" es la más importante del proyecto desde el punto de vista de impacto. Un NDR que solo funcione como SaaS centralizado es inútil para un colegio rural. Un NDR community que funcione localmente y se "mejore" con enterprise es el modelo correcto para infraestructura crítica de bajo presupuesto. Que el código refleje esa filosofía.

*El Consejo ha hablado. Que el commit de mañana incluya la interfaz `CryptoProvider`.* 🛡️