## 1. Informe para el Consejo de Sabios — DAY 108

---

**Asunto**: DAY 108 — Formalización de provision.sh + ADR-026/027 + Gate PASO 4 verde

Consejo, buenas. Sesión de consolidación hoy — sin features nuevas, pero el proyecto está en su estado más robusto desde el DAY 1. Informe completo.

---

### LO QUE SE HIZO

**PASO 1 — Verificación swap CTX_ETCD_TX/RX (ADR-027)**

Se revirtió el swap en `etcd-server/src/component_registry.cpp` para verificar si era necesario independientemente del fix de `component_config_path` (DAY 107). Resultado: MAC failure confirmado en ml-detector, sniffer y firewall. El swap es correcto y necesario.

Justificación documentada: el servidor es el espejo del cliente. Cliente cifra con `CTX_ETCD_TX`, servidor debe descifrar con esa misma subclave en su `rx_`. Sin el swap, ambos lados usan la misma subclave en la misma dirección — MAC failure garantizado por diseño HKDF.

**PASO 2 — Invariant fail-fast (3 adaptadores)**

Añadido en `ml-detector/src/etcd_client.cpp`, `sniffer/src/userspace/etcd_client.cpp`, `firewall-acl-agent/src/core/etcd_client.cpp`:

```cpp
// INVARIANT (ADR-027): encryption_enabled requiere component_config_path.
if (config_.encryption_enabled && config.component_config_path.empty()) {
    std::terminate(); // FATAL: setear component_config_path en etcd_client::Config
}
```

El bug raíz de DAY 107 (component_config_path vacío → tx_ null → datos en claro → MAC failure) ahora produce `std::terminate()` inmediato en lugar de fallo silencioso.

**PASO 3 — provision.sh formalizado**

Estado anterior: frágil. `vagrant destroy && vagrant up` dejaba el pipeline roto. Fixes aplicados:

- `create_component_dir`: `chmod 700 root:root` → `chmod 755 root:vagrant`
- `generate_seed`: `chmod 600 root:root` → `chmod 640 root:vagrant`
- Seed maestro: `etcd-server/seed.bin` distribuido a los 5 componentes restantes
- Symlinks JSON automáticos: `/etc/ml-defender/*/` → `/vagrant/*/config/*.json`
- libsodium compat: `ln -sf libsodium.so.26 libsodium.so.23` + `ldconfig`
- `install_shared_libs()`: build + install automático de seed-client, crypto-transport, plugin-loader, etcd-client
- libsnappy instalada vía apt (dependencia del sniffer)
- `check_dependencies()`: tmux añadido con auto-install
- libcrypto_transport: rebuild automático si fecha < hoy

**PASO 4 — Gate de calidad**

```
vagrant destroy -f && vagrant up && make pipeline-start && sleep 20 && make pipeline-status
→ 6/6 RUNNING sin intervención manual
```

Dos ciclos de destroy necesarios para llegar aquí (faltaban libsnappy y etcd-client en el primer intento). Gate verde en el segundo ciclo.

**ADR-026 y ADR-027 escritos y commiteados**

- ADR-026: Arquitectura P2P, Distribución de Modelos y Aprendizaje de Flota — formaliza las decisiones del Consejo DAY 104
- ADR-027: CTX_ETCD_TX/RX swap — documenta el principio mirror cliente/servidor

---

### ESTADO ACTUAL

```
Branch: feature/plugin-crypto
Pipeline: 6/6 RUNNING (post vagrant destroy limpio)
provision.sh: reproducible desde cero
PHASE 2b: DESBLOQUEADA
```

---

### PREGUNTAS AL CONSEJO

**Q1 — `std::terminate()` vs excepción en el invariant**

El invariant actual usa `std::terminate()` — fallo ruidoso e irrecuperable. El argumento a favor: un componente que arranca sin cifrado en producción es peor que un componente que no arranca. El argumento en contra: en entornos de desarrollo con `MLD_DEV_MODE=1`, `std::terminate()` hace el debugging más difícil. ¿Debería el invariant respetar `MLD_DEV_MODE` y degradar a `std::cerr` + return false en dev, manteniendo `std::terminate()` solo en prod?

**Q2 — etcd-client en install_shared_libs(): ¿cmake desde cero o precompilado?**

Actualmente `install_shared_libs()` hace `rm -rf build && cmake && make && make install` para etcd-client en cada `vagrant destroy`. Esto funciona pero tarda ~2 min. ¿Merece la pena añadir un mecanismo de caché (tar del build, checksum del source) o es premature optimization para un entorno de desarrollo con destroy infrecuente?

**Q3 — PHASE 2b: plugin_process_message() en rag-ingester**

El patrón es idéntico al de firewall-acl-agent (DAY 105). Gate: TEST-INTEG-4b con MessageContext y result_code=0. ¿Hay algún riesgo específico en rag-ingester que no estaba presente en firewall-acl-agent? El rag-ingester maneja FAISS y CSV dual-pipeline — el plugin se invocaría antes de la ingesta FAISS. ¿Debería el plugin poder modificar el MessageContext antes de que llegue a FAISS, o solo leer y decidir early-return?

**Q4 — rag-security/config no existe tras vagrant destroy**

provision.sh produce `⚠️ Config dir no existe aún: /vagrant/rag-security/config`. El directorio se crea durante `pipeline-start` (el binario lo crea). No es bloqueante hoy, pero el symlink JSON no se crea en provisioning — se crea tarde. ¿La solución correcta es crear el directorio vacío en provision.sh, o dejar que el binario lo gestione y añadir el symlink en `rag-security-start`?

---

*Informe preparado por Alonso Isidoro Román — DAY 108*
*Via Appia Quality: un sistema que no se puede reproducir desde cero no existe.*

