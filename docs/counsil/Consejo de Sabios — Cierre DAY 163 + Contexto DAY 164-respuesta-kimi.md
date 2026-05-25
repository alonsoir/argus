## Respuestas del Consejo de Sabios — DAY 164

### Q1 — `HttpEtcdRegistrar`: **etcd-cpp-apiv3**

**Razonamiento:** El costo de adopción ya está pagado (`provision.sh` lo instala). Reimplementar cliente etcd sobre `cpp-httplib` introduce deuda de protocolo (manejo de leases, retransmisión gRPC, serialización protobuf) que no aporta valor diferencial a vuestro proyecto. En infraestructura crítica, **usar una librería probada es más simple operacionalmente que mantener un cliente HTTP casero**. El "modelo de threading gRPC" es un costo aceptable: etcd-cpp-apiv3 v0.15.3 usa `grpc::CompletionQueue` que se integra limpiamente con un hilo de eventos dedicado o con el loop existente si usáis `AsyncWatch`.

**Recomendación:** etcd-cpp-apiv3. No dupliquéis trabajo que la dependencia ya resuelve.

---

### Q2 — Watch de etcd: **gRPC watch nativo**

**Razonamiento:** Con 6 componentes y grace period de 10s, el polling cada 1s introduce latencia media de 500ms y carga innecesaria (6 req/s constantes vs. conexiones persistentes inactivas). Un gRPC watch push-based reduce latencia a <100ms y elimina carga de polling. La gestión de reconexión en etcd-cpp-apiv3 es robusta (la librería maneja `watch_id` y reenvío automático ante desconexión).

**Contra-argumento al long-poll HTTP:** Sin estado de conexión significa que cada reconexión requiere reestablecer el watch desde el `revision` actual, con riesgo de perder eventos intermedios si no gestionáis `start_revision` manualmente.

**Recomendación:** gRPC watch nativo via `etcd-cpp-apiv3::Watch`. Para infraestructura crítica, la fiabilidad del push supera la simplicidad aparente del poll.

---

### Q3 — `CryptoEpochCoordinator`: **Integrado en el health-check loop existente**

**Razonamiento:** Ya tenéis un loop de 5s en `etcd-server/main.cpp`. Añadir 6 hilos dedicados (uno por componente) en un sistema embebido es una explosión de threading que complica debugging y scheduling. El grace period de 10s hace que 5s de resolución temporal sea aceptable — detectáis el cambio de epoch en máximo una iteración del loop, dejando 5s de margen para el rollover criptográfico.

**Diseño sugerido:**
```cpp
// En main.cpp, dentro del loop existente:
coordinator.poll();  // non-blocking, chequea watch queue
if (coordinator.epoch_changed()) {
    provider.refresh();
    handle.reload();
    coordinator.write_ack();
}
```

**Recomendación:** Loop integrado. Mantened el número de hilos bajo control. El health-check es el sitio natural para verificar sanidad del sistema, incluyendo la epoch criptográfica.

---

### Síntesis para el PI

| Decisión | Recomendación del Consejo | Justificación clave |
|----------|---------------------------|---------------------|
| Cliente etcd | `etcd-cpp-apiv3` | Deuda pagada, no reinventar protocolo |
| Watch | gRPC nativo | Latencia <100ms, sin carga de polling |
| Threading | Loop integrado | 5s ≤ 10s grace, evitar +6 hilos |

**Nota operacional:** Si en FASE 5 el grace period baja a <2s, reconsiderad el polling integrado por un hilo de eventos gRPC dedicado compartido entre componentes. Para DAY 164, el loop de 5s es la decisión correcta.