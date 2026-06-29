**CONSEJO DE SABIOS — RESPUESTAS TÉCNICAS — DAY 150**
*Expertise en sistemas distribuidos de alto rendimiento, C++20 y arquitectura open-core — para aRGus NDR*

---

## 🎯 VEREDICTO GLOBAL

**DIRECCIÓN APROBADA CON REFINAMIENTOS** ✅

La implementación de ADR-044 es sólida, operable y alineada con los principios de soberanía y determinismo. Las preguntas Q1-Q5 tocan puntos críticos de mantenibilidad, bootstrap y modelo de negocio. Respuestas concisas abajo.

---

## 🔍 RESPUESTAS A PREGUNTAS DEL CONSEJO

### **Q1 — Compilación condicional vs dos binarios**

**Respuesta corta**: ✅ **`#ifdef ARGUS_VAULT_ENABLED` en mismo código fuente**, con disciplina estricta.

**Fundamentación**:
| Criterio | `#ifdef` único binario | Dos binarios separados |
|----------|----------------------|----------------------|
| **Mantenibilidad** | ✅ Un solo codebase, CI único, tests únicos | ❌ Duplicación de lógica, riesgo de divergencia |
| **Auditabilidad** | ✅ Diff claro entre community/enterprise | ❌ Requiere comparar dos repos o branches |
| **Build time** | ⚠️ Compila código no usado (minimizable con LTO) | ✅ Solo compila lo necesario |
| **Riesgo de "divergencia silenciosa"** | ✅ Mitigable con `static_assert` y tests que validan ambos paths | ❌ Alto: es fácil que enterprise diverja sin que community se beneficie |

**Disciplina requerida para `#ifdef` seguro**:
```cpp
// common/crypto_interface.h — contrato único
class ICryptoProvider {
public:
    virtual CryptoMaterial fetch() = 0;
    virtual ~ICryptoProvider() = default;
};

// community/seed_client.cpp
#ifdef ARGUS_VAULT_ENABLED
class VaultCryptoProvider : public ICryptoProvider { /* ... */ };
#else
class SeedFileCryptoProvider : public ICryptoProvider { /* ... */ };
#endif

// factory: único punto de decisión
std::unique_ptr<ICryptoProvider> create_crypto_provider(const Config& cfg) {
#ifdef ARGUS_VAULT_ENABLED
    return std::make_unique<VaultCryptoProvider>(cfg.vault_config);
#else
    return std::make_unique<SeedFileCryptoProvider>(cfg.seed_path);
#endif
}
```

**Regla de oro**: Ninguna lógica de negocio (detección, firewall, ML) depende directamente de `#ifdef`. Solo la capa de provisión criptográfica.

**Conclusión**: Mismo binario, flag CMake. Documentar en `docs/OPEN_CORE.md` que `ARGUS_VAULT_ENABLED` es el **único** punto de separación funcional.

---

### **Q2 — Orden de migración de componentes**

**Respuesta corta**: 🎯 **Propuesta correcta, con una precisión**: `etcd-server` primero, luego **paralelizar** sniffer/ml-detector/firewall (familia A+B), finalmente rag-ingester/security (familia C).

**Justificación de dependencias**:
```
etcd-server (bootstrap especial)
       ↓
sniffer ↔ ml-detector ↔ firewall-acl-agent  ← familia A+B, alta interdependencia
       ↓
rag-ingester ↔ rag-security                  ← familia C, menor criticidad operativa
```

**Riesgo mitigado**: Migrar sniffer/ml-detector/firewall en paralelo asegura que si hay un bug en `VaultClient`, se detecta en los tres componentes críticos antes de tocar RAG (que es "nice-to-have" para FEDER).

**Recomendación operativa**:
```bash
# Script de migración escalonada
./migrate-to-vault.sh --component etcd-server --env dev  # Día 1
./migrate-to-vault.sh --components sniffer,ml-detector,firewall --env dev  # Día 2 (paralelo)
./migrate-to-vault.sh --components rag-ingester,rag-security --env dev  # Día 3
```

**Conclusión**: Orden propuesto es óptimo. Añadir parallelismo en familia A+B para acelerar validación.

---

### **Q3 — `register_etcd_status` sin etcd disponible en bootstrap**

**Respuesta corta**: ✅ **Fichero local + "self-registration deferred"**.

**Patrón recomendado**:
```cpp
// etcd-server bootstrap flow
if (is_bootstrap_mode) {
    // 1. Obtener seed de Vault (sin barrera)
    auto seed = VaultClient::fetch_crypto_material(cfg);
    
    // 2. Derivar keypair en memoria
    auto keypair = derive_keypair(seed, "etcd", "bootstrap");
    
    // 3. Escribir estado en fichero local (NO en etcd aún)
    write_local_crypto_status("/run/argus/etcd-crypto-status.json", {
        .component = "etcd-server",
        .crypto_ready = true,
        .key_fingerprint = sha256(keypair.public_key),
        .timestamp = utc_epoch_ns()
    });
    
    // 4. Arrancar servidor etcd con keypair cargado
    start_etcd_server(keypair);
    
    // 5. POST-arranque: registrar en sí mismo (ahora etcd está online)
    if (etcd_client::is_local_server_ready()) {
        etcd_client::register_crypto_status("etcd-server", ...);  // ahora sí, en etcd
        std::remove("/run/argus/etcd-crypto-status.json");  // limpiar fichero temporal
    }
}
```

**Ventajas**:
- No hay dependencia circular: etcd no necesita etcd para arrancar.
- Los demás componentes pueden leer el fichero local como fallback si etcd aún no está disponible (graceful degradation).
- Una vez etcd online, el estado se migra a etcd y el fichero se limpia (single source of truth).

**Conclusión**: Fichero local temporal + migración post-arranque. Documentar en ADR-044 §D5.

---

### **Q4 — Cache tmpfs y `vagrant destroy` vs producción edge**

**Respuesta corta**: 🎯 **Cache persistente en producción, tmpfs en dev**.

**Estrategia dual**:
```yaml
# group_vars/all.yml
crypto_cache:
  dev:
    path: "/run/argus/crypto-cache"  # tmpfs, se pierde en reboot/destroy
    ttl_seconds: 3600  # 1h
  prod:
    path: "/etc/ml-defender/{{ component }}/crypto-cache"  # persistente, cifrado
    ttl_seconds: 259200  # 72h
    encryption: "AES-256-GCM con clave derivada de TPM si disponible"
    permissions: 0600
```

**Implementación en `vault_client.cpp`**:
```cpp
std::string get_cache_path(const VaultConfig& cfg) {
#ifdef NDEBUG  // production build
    return cfg.prod_cache_path;  // persistente, cifrado
#else
    return cfg.dev_cache_path;   # tmpfs, sin cifrado adicional
#endif
}
```

**Modelo de amenaza para cache persistente**:
| Escenario | Mitigación |
|-----------|-----------|
| Atacante con acceso root al nodo | ❌ Juego perdido (ya tiene todo) |
| Atacante con acceso físico al disco | ✅ Cache cifrado con clave derivada de TPM/HSM (si disponible) |
| Reboot legítimo | ✅ Cache persistente permite arranque sin Vault disponible |
| `vagrant destroy` en dev | ✅ tmpfs se borra → EMECAS fuerza re-provisionado |

**Conclusión**: Cache persistente cifrado en prod, tmpfs en dev. Documentar en ADR-044 §D4.

---

### **Q5 — open-core: ¿`ARGUS_VAULT_ENABLED` es suficiente separador?**

**Respuesta corta**: ✅ **Sí, para FEDER**. Post-FEDER, evaluar separar **actuation** (Falco) y **graph analytics** (Neo4j) como enterprise adicional.

**Matriz de funcionalidades**:
| Funcionalidad | Community (seed-client) | Enterprise (VaultClient) | Justificación |
|--------------|------------------------|-------------------------|--------------|
| Detección ML (F1=0.9985) | ✅ Igual | ✅ Igual | Core científico, no debe variar |
| Firewall ACL actuation | ✅ Básico (DROP/ALLOW) | ✅ Avanzado (Falco integration) | Falco requiere governance criptográfico avanzado |
| Telemetría local (SQLite) | ✅ Igual | ✅ Igual | Soberanía de datos, no depende de Vault |
| Consolidación Neo4j central | ❌ No incluye | ✅ Incluye | Neo4j es infraestructura centralizada, no edge |
| OpenCanary honeypot | ❌ No incluye | ✅ Incluye | Honeypots requieren gestión centralizada de identidades |
| Rotación criptográfica automática | ❌ Manual | ✅ Automática coordinada | Valor enterprise: reducción de carga operacional |

**Regla de diseño open-core**:
> *"Todo lo que afecta a la precisión de detección (F1, recall, latency) debe ser idéntico en community y enterprise. La separación debe estar en governance, operabilidad y escalabilidad, no en capacidad de detección."*

**Conclusión**: `ARGUS_VAULT_ENABLED` es suficiente para FEDER. Documentar roadmap post-FEDER en `docs/OPEN_CORE.md` con la matriz arriba.

---

## 📋 RESUMEN DE DECISIONES PARA IMPLEMENTACIÓN

| Pregunta | Decisión | Acción inmediata |
|----------|----------|-----------------|
| Q1 | `#ifdef` único binario | Añadir `static_assert` y tests que validan ambos paths |
| Q2 | Orden propuesto + paralelismo A+B | Crear script `migrate-to-vault.sh` escalonado |
| Q3 | Fichero local + migración post-arranque | Implementar `write_local_crypto_status()` en etcd-server |
| Q4 | Cache persistente cifrado en prod | Actualizar `vault_client.cpp` con `#ifdef NDEBUG` para paths |
| Q5 | `ARGUS_VAULT_ENABLED` suficiente para FEDER | Crear `docs/OPEN_CORE.md` con matriz de funcionalidades |

---

## 🚀 PRÓXIMOS PASOS (DAY 151)

1. **Integrar `etcd-server` con `VaultClient`** (P0)
    - Implementar patrón fichero local + migración post-arranque (Q3)
    - Tests: validar ambos paths (`ARGUS_VAULT_ENABLED=ON/OFF`)

2. **Cerrar DEBT-CRYPTO-HEARTBEAT-001** (P1)
    - Implementar `register_etcd_status()` real con lease TTL=10s
    - Keepalive cada 5s, alerta tras 3 fallos consecutivos

3. **Ansible Jinja2 para 4 componentes** (P1)
    - Regla: JSONs originales intocables, generar `*.dev.json` / `*.prod.json`
    - Validar que `ARGUS_VAULT_ENABLED` se inyecta correctamente en cada config

4. **Documentar open-core** (P2)
    - Crear `docs/OPEN_CORE.md` con matriz de funcionalidades y regla de diseño

---

> *"La elegancia de un sistema distribuido no está en su complejidad, sino en cómo oculta su complejidad. Este pipeline no solo distribuye claves: distribuye confianza. Que cada `#ifdef` sea una puerta, no un muro."*

**¿Procedemos a implementar la integración de `etcd-server` con el patrón de fichero local + migración post-arranque?** 🛡️🔐🧠