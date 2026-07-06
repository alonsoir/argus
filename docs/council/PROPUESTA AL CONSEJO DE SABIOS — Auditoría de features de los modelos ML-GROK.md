**Respuesta del Consejo de Sabios — DAY 209**

Hemos revisado con atención la auditoría. Es un trabajo limpio, trazable y honesto. Cumple el principio *medir, no votar*. A continuación, nuestras posiciones concretas sobre las 5 preguntas.

### 1. Cabeza de ransomware embebida actual

**Sí, desactivar inmediatamente** (`enabled: false` en `ml_detector_config.json`).

Razones:
- Produce **scores sistemáticamente engañosos** porque 9/10 features son proxies sin correlación semántica con lo que el modelo entrenó.
- La feature dominante (entropy, 36%) está siendo simulada con varianza de longitud de paquetes. Eso no es detección, es ruido.
- Mantenerla activa contamina la confianza en todo el sistema de alertas de nivel 2.

**Recomendación adicional**: no basta con desactivarla. Debe ir acompañada de un **ADR** (Architecture Decision Record) que explique el porqué y registre la lección aprendida sobre *domain mismatch*. Mientras no se tenga un reemplazo, la ausencia de señal en esta cabeza es preferible al falso confort.

Etiquetarla como “proxy-based, unreliable” solo sería aceptable como medida temporal muy corta (días). Mejor desactivar.

### 2. Modelo `ransomware_network_detector_proto_aligned` (XGBoost 45 features)

**Sí, registrar inmediatamente `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001`** y autorizar su borrado posterior vía `git rm`.

Condiciones:
- El DEBT debe documentar claramente: origen del artefacto, por qué se abandonó el camino, y qué problema de trazabilidad de features generó.
- Mantener el directorio y el artefacto en el commit de borrado (no `rm` a secas) para que quede en la historia.
- No es urgente borrarlo hoy, pero sí debe salir del pipeline de builds y del config antes de la siguiente release.

Esto es limpieza técnica + higiene epistemológica.

### 3. Features constantes en el detector DDoS

**Sí, registrar `DEBT-DDOS-FEATURES-CONSTANT-001`**.

No requiere acción inmediata. El DDoS está **degradado pero vivo**, y sus features de mayor peso parecen correctas. Las tres constantes (especialmente la que el compilador resuelve a `false` en compile-time) son deuda técnica aceptable en el corto plazo.

Prioridad baja-media. Se puede abordar en la misma iteración en que se toque el extractor de features de nivel 2.

### 4. Entrenar un modelo comportamental de ransomware de verdad

**Autorizamos avanzar con la Opción A (modelo de red) de inmediato**.

Justificación:
- Está dentro del alcance actual de aRGus como NDR.
- Es entrenable con datos que ya podemos generar legalmente (Atomic Red Team + topología existente).
- Se alinea con la fortaleza real del sistema: detección de las fases de red del ataque (C2, discovery, lateral movement, exfil).
- Evita el scope creep pre-FEDER.

**Opción B (híbrido red+host)** queda explícitamente post-FEDER. Requiere integración de telemetría Wazuh, alineación de timelines, normalización de features y un pipeline más complejo. Es la dirección correcta a medio plazo, pero no ahora.

El nuevo modelo de red debe nacer con **contrato de features explícito y documentado** (a diferencia del artefacto de 45 features anónimas). Exigimos que el feature store o el JSON de configuración sea la fuente de verdad.

### 5. Línea MITRE ATT&CK + Atomic Red Team

**Aprobada completamente** como trabajo pre-FEDER.

Valor añadido esperado:
- Matriz técnica × sensor × componente (ablación) es un entregable excelente y publicable.
- Genera datos comportamentales reales y trazables para entrenar el modelo de Opción A.
- Refuerza el discurso honesto ante Andrés: “esto es lo que vemos desde red, esto es lo que no vemos y por qué, y así es como cubrimos el gap con Wazuh”.

**Recomendaciones operativas**:
- Elegir LockBit u otro perfil bien cartografiado (ya existen mappings públicos buenos).
- Documentar claramente las técnicas emuladas y las que quedan fuera.
- Incluir al menos una corrida con el ransomware actual desactivado vs activado (aunque sepamos que da ruido) para cuantificar la contaminación actual.

---

### Observaciones finales del Consejo

Esta auditoría refuerza una verdad estructural: **un NDR excelente sigue siendo un NDR**. Pretender que vea cifrado de disco es luchar contra la física de la red. La madurez no está en inflar capacidades, sino en declarar fronteras con precisión y cubrirlas con las herramientas adecuadas (Wazuh para host).

El contraste entre el ransomware (muerto por domain mismatch) y el DDoS (vivo aunque degradado) es oro pedagógico. Úsenlo.

Estamos de acuerdo en desactivar lo roto, registrar las deudas y avanzar con datos reales sobre lo que sí podemos observar. Procedan.

*Via Appia Quality mantiene el rumbo.*

FDO

GROK