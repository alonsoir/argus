# DEBT-ALERTING-LIBCRYPTO-PROVIDER-001

**Prioridad:** P1  
**Estado:** ABIERTA  
**Detectado:** DAY 158  

## Síntoma
`alert_client.hpp` es header-only e incluye `httplib.h` directamente.
Cualquier componente que lo incluya Y enlace con `libetcd_client.so`
(que también compila httplib::ClientImpl) produce ODR violation → SIGSEGV.

Afecta a: firewall (resuelto eliminando alert_client), y potencialmente
a cualquier otro componente que quiera usar alertas.

Hoy solo etcd-server puede enviar alertas Discord/Telegram de forma segura.

## Fix
Mover `AlertClient` como implementación opaca dentro de `libcrypto_provider.so`.
Exponer `argus/alerting.h` con interfaz sin httplib en los headers:

```cpp
// argus/alerting.h — sin httplib, sin ODR
namespace argus {
  void alert_sos(const SosPayload& payload);
}
```

Todos los componentes enlazan con `libcrypto_provider.so` para alertas.
httplib queda completamente encapsulado, invisible para el linker de los binarios.

## Prerequisito para
- DEBT-ALERTING-VAULT-001 (migrar credenciales a Vault)
