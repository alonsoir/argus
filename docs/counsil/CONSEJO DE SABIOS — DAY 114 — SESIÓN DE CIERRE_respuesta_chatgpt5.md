El trabajo está en un punto muy sólido. Lo que has construido ya no es “una idea bien ejecutada”, es un sistema con propiedades operativas reales (fail-closed, testado, reproducible). Dicho eso, voy a ser directo en lo importante: ahora el riesgo ya no es técnico profundo, es **operativo y de consistencia**. Ahí es donde hay que apretar.

---

# Q1 — DEBT-SIGN-AUTO (firma automática)

### Veredicto: **Correcto, pero incompleto si no añades invariantes fuertes**

El diseño es bueno (idempotente, simple, ejecutable siempre), pero ahora mismo tiene un hueco crítico:

## Problema clave

Estás asumiendo:

> “si falta firma o es inválida → firmar automáticamente”

Esto rompe parcialmente tu modelo de confianza **offline signing (D1)**.

### Riesgo real

Si alguien consigue meter un `.so` malicioso en el directorio:

* Tu sistema lo detecta como “no firmado”
* **Lo firma automáticamente**
* Se convierte en “válido”

→ Has destruido la cadena de confianza.

---

## Recomendación (importante)

Divide el comportamiento en dos modos:

### 🔒 Modo producción (estricto)

```
Si .sig no existe → ERROR (NO firmar)
Si firma inválida → ERROR (NO firmar)
Si plugin nuevo no conocido → ERROR
```

### 🛠️ Modo desarrollo / provisioning

```
check-plugins --sign-missing:
  solo firma si:
    - plugin está en allowlist
    - o hash coincide con build reciente
```

---

## Mejora concreta

Añade **allowlist + hash tracking**:

```
/var/lib/ml-defender/plugin-manifest.json

{
  "plugins": {
    "libplugin_x.so": {
      "sha256": "...",
      "signed": true
    }
  }
}
```

Flujo:

* Plugin nuevo → no está en manifest → NO firmar automáticamente
* Plugin existente modificado → hash mismatch → ALERTA, NO firmar

---

## Conclusión Q1

✔ Bien planteado
⚠ Necesita separar claramente:

* **trust establishment (manual/offline)**
* **operational convenience (automático)**

Si no, introduces una puerta trasera involuntaria.

---

# Q2 — DEBT-HELLO-001

### Veredicto: **C (ambas) es la correcta sin matices**

Pero con una mejora:

## Recomendación final

* `BUILD_DEV_PLUGINS=OFF` (default)
* JSON de producción **sin referencia**
* Y además:

```
/usr/lib/ml-defender/plugins/dev/
```

Separar físicamente plugins dev vs prod.

---

## Motivo

Incluso aunque no lo cargues:

* Sigue siendo superficie de ataque
* Puede ser firmado accidentalmente
* Puede acabar en allowlist

---

## Mejora adicional

Haz que el loader rechace explícitamente:

```
if (path.contains("/dev/")) reject;
```

---

## Conclusión Q2

✔ Decisión correcta: C
✔ Añadir separación física de directorios

---

# Q3 — Priorización PHASE 3

### Veredicto: **El orden es bueno, pero hay una dependencia oculta importante**

## Problema

Has puesto:

1. systemd
2. AppArmor
3. CI
4. reset keys
5. sign-auto

Pero en realidad:

👉 **AppArmor depende de conocer comportamiento estable del sistema**

---

## Orden recomendado

### 🔥 Orden óptimo

1. **systemd hardening**
2. **DEBT-SIGN-AUTO (modo seguro corregido)**
3. **DEBT-HELLO-001**
4. **TEST-PROVISION-1 (CI gate)**
5. **AppArmor profiles**
6. **D11 key rotation**

---

## Por qué

### AppArmor antes = error típico

Si lo haces demasiado pronto:

* perfiles incorrectos
* falsos positivos
* debugging infernal

Primero estabiliza:

* arranque
* firma
* despliegue

Luego encierras.

---

## Conclusión Q3

✔ Buen criterio general
⚠ Ajustar orden: AppArmor debe ir después de estabilización operativa

---

# Q4 — Troubleshooting

### Veredicto: **Muy buen inicio, pero le falta profundidad de sistema**

Ahora mismo cubres solo plugin-loader. Falta:

---

## Casos adicionales que debes incluir

### 1. Fallo silencioso (crítico)

```
Pipeline arranca pero no procesa tráfico →
  ¿sniffer activo? →
  ¿interfaces correctas? →
  ¿XDP attach OK?
```

---

### 2. ZeroMQ

```
No hay eventos →
  ¿puertos abiertos? →
  ¿bind vs connect invertido? →
  ¿backpressure?
```

---

### 3. ML detector

```
No hay detecciones →
  ¿modelo cargado? →
  ¿features vacías? →
  ¿umbral mal configurado?
```

---

### 4. Permisos / AppArmor (cuando llegue PHASE 3)

```
EPERM / EACCES →
  revisar dmesg →
  aa-status →
  modo complain vs enforce
```

---

### 5. Firma (ampliado)

```
Firma válida pero falla →
  ¿clave pública correcta en binario?
  ¿endianness / hex parsing?
```

---

## Formato recomendado

### NO: CLAUDE.md

### NO: disperso

### SÍ:

```
docs/operations/troubleshooting.md
```

Y además:

```
man argus-troubleshoot
```

(opcional pero muy potente)

---

## Mejora clave

Añade:

```
make diagnose
```

Que haga:

* check plugins
* check firmas
* check sockets
* check procesos

---

## Conclusión Q4

✔ Muy buen inicio
⚠ Falta cubrir sistema completo (no solo plugins)
⭐ Gran oportunidad: convertirlo en herramienta (`make diagnose`)

---

# Evaluación global DAY 114

## Lo que está muy bien

* Fail-closed real funcionando en producción → esto es serio
* Ed25519 bien implementado (decisiones maduras)
* Tests coherentes con modelo de amenazas
* Disciplina en ADRs muy alta

---

## Donde debes poner foco ahora

### 1. Riesgos operativos (principal)

* firma automática mal diseñada → riesgo real
* deploy inconsistente → ya lo has vivido hoy

### 2. Superficie de ataque residual

* plugins dev
* paths no aislados
* posibles errores humanos

### 3. Observabilidad

* troubleshooting aún incompleto
* falta tooling automático

---

## Insight importante

Has cruzado un umbral:

> Ya no estás diseñando seguridad, estás diseñando **operación segura**.

Y eso es otro problema distinto.

---

# Recomendaciones finales (claras)

1. **Corrige DEBT-SIGN-AUTO antes de implementarlo**
2. **Elimina completamente plugins dev del runtime**
3. **Retrasa AppArmor hasta tener estabilidad operativa**
4. **Crea `make diagnose`**
5. **Introduce manifest de plugins (hash + estado)**

---

Si mantienes este nivel de rigor en PHASE 3, el proyecto deja de ser “un NDR interesante” y pasa a ser **una referencia seria de ingeniería defensiva aplicada**.
