Buena idea. El Consejo necesita pronunciarse sobre ADR-045 antes de que toquemos FASE 2. El prompt debe ser preciso y sin ambigüedades para que los 8 modelos razonen sobre lo mismo.

---

**Prompt para el Consejo de Sabios — ADR-045 CryptoEpoch Coordination:**

---

Soy el PI de aRGus NDR (arXiv:2604.04952), un sistema NDR C++20 para infraestructura crítica. Necesito vuestra revisión técnica para ADR-045 antes de implementar FASE 2 del ciclo de vida criptográfico enterprise.

**Contexto:**

El sistema tiene 6 componentes comunicados via ZeroMQ con claves derivadas de un seed compartido (HKDF-SHA256, ADR-013). El provider de material criptográfico es `ICryptoProvider` con dos implementaciones: `SeedFileProvider` (community) y `VaultProvider` (enterprise, HashiCorp Vault). Acabamos de implementar `CryptoProviderHandle` — wrapper RCU con `std::atomic<shared_ptr<ICryptoProvider>>` que permite swap atómico del provider sin downtime (FASE 1 cerrada).

**El problema de FASE 2 — CryptoEpoch:**

Cuando se rota el keypair (nueva época criptográfica), todos los componentes deben transicionar **simultáneamente**. Si sniffer rota a época N+1 pero firewall sigue en época N → canal ZMQ muerto (split-brain criptográfico). Necesitamos coordinación.

**Propuesta ADR-045 v1 para revisión:**

```
Entidad coordinadora: etcd-server publica CryptoEpoch en etcd:
  /argus/crypto/epoch   → { epoch_id: uint64, seed_hash: hex, not_before: ISO8601 }

Flujo de rotación:
  1. Vault genera nuevo seed → etcd-server escribe nueva época con not_before=T+grace
  2. Cada componente watch /argus/crypto/epoch via etcd subscriber
  3. En T+grace: todos llaman handle.reload(CryptoProvider::create(new_cfg))
  4. Ventana dual-key ZMQ (FASE 3): aceptar época N y N+1 durante grace period

Grace period: configurable, default 30s
Coordinación de reloads: best-effort (no 2PC — demasiado complejo)
Fallo parcial: componente que no rota → canal ZMQ muerto → autonomy trigger
```

**Preguntas específicas al Consejo:**

1. ¿`not_before` en etcd es suficiente como coordinación o necesitamos un mecanismo más fuerte (ej: ack explícito de cada componente)?

2. ¿El grace period de 30s es razonable para 6 componentes en el mismo nodo, o debería ser configurable por componente?

3. ¿Quién debe ser el **único escritor** de `/argus/crypto/epoch`? ¿etcd-server o un proceso externo (Jenkins/Vault agent)?

4. ¿Cómo detectar y recuperar el split-brain si un componente falla durante la transición? ¿Autonomy state machine existente es suficiente o necesita un estado nuevo `EPOCH_TRANSITION`?

5. ¿La ventana dual-key ZMQ (aceptar N y N+1) es implementable sin cambios en el protocolo wire actual (LZ4 + LE uint32_t), o requiere añadir `epoch_id` al header binario?

Razonad de forma independiente. Si disentís en algún punto, defended vuestra posición con argumentos técnicos concretos. El PI es el árbitro final.

---

¿Lo lanzas así o quieres ajustar algo antes de mandarlo?
