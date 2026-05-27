# Convocatoria Consejo de Sabios — ADR-037
**Fecha:** 2026-04-20 (DAY 123)  
**Asunto:** Veredicto requerido — Static Analysis Security Hardening

---

Consejo de Sabios,

Os convocamos para un veredicto sobre **ADR-037 — Static Analysis Security Hardening**.

El ADR adjunto documenta los resultados de un análisis estático Snyk sobre el
codebase C++ de aRGus NDR en su estado `v0.5.0-preproduction`. Se han identificado
17 findings de severidad media. Este ADR es **bloqueante para ADR-036**
(Formal Verification Baseline), que es a su vez el último ítem del backlog antes
de poder considerar el pipeline apto para entornos de producción real.

Os pedimos que leáis el ADR con atención y precisión. Cada decisión aquí afecta
directamente a la seguridad de un sistema pensado para proteger hospitales, escuelas
y municipios que no pueden permitirse soluciones enterprise. La superficie de ataque
que dejemos abierta hoy puede ser la brecha que explote mañana en una institución
que depende de nosotros.

---

## Lo que os pedimos

**Responded a las 4 preguntas del §9 pensando exclusivamente en lo mejor para
el pipeline.** No en la elegancia teórica, no en la solución más académica —
en lo que hace el sistema más seguro, más mantenible y más pequeño.

Para facilitar el veredicto, estructurad vuestra respuesta así:

### P1 — `weakly_canonical` vs `canonical`
Para paths de escritura (ficheros aún no creados), `canonical` lanzaría una
excepción porque el fichero no existe todavía. `weakly_canonical` resuelve
symlinks y `..` sin requerir existencia previa.

**¿Aceptáis `weakly_canonical` para los casos de escritura, o proponéis
una alternativa que cubra ambos casos (lectura y escritura) con igual
o mayor seguridad?**

### P2 — Granularidad de prefijos por componente
La propuesta usa prefijos específicos por componente:
`/etc/ml-defender/keys/` para seed-client,
`/etc/ml-defender/` para configs,
`/shared/` para contrib/tools.

**¿Es correcta esta granularidad, o se debe usar un prefijo único
`/etc/ml-defender/` para toda la superficie de producción?**
Tened en cuenta que más granularidad = más restricción = mejor seguridad,
pero también más puntos de configuración que mantener.

### P3 — Contrib/ y tools/ — ¿mismo estándar o nivel menor?
Los ficheros en `contrib/` y `tools/` no corren en producción ni bajo AppArmor.
Son herramientas de investigación con input controlado por el investigador.

**¿Se les aplica el mismo `safe_path::resolve()` con prefijo `/shared/`,
o se acepta un nivel de restricción menor (solo documentar, no enforcer)?**
Considerad que aplicar el mismo estándar simplifica el mantenimiento
y forma hábito en el equipo, aunque el riesgo operacional sea bajo.

### P4 — Falsos positivos inotify (F15/F16)
En `csv_dir_watcher.cpp:168` y `csv_file_watcher.cpp:112`, Snyk alerta de
integer overflow en `ptr < buf + n`. El análisis propio concluye que es un
**falso positivo**: `n` procede de `read()` cuyo resultado está acotado por
`BUF_SIZE = 4096`, haciendo imposible el overflow en la práctica.

**¿Aceptáis el veredicto de FP y la decisión de no modificar el código,
documentando la justificación en el ADR? ¿O identificáis algún vector
de ataque que invalide este análisis?**

---

## Lo que NO os pedimos

- No necesitamos debate sobre arquitecturas alternativas de seguridad.
- No necesitamos comparativas con otras herramientas de análisis estático.
- No necesitamos reescribir la solución propuesta salvo que encontréis
  un defecto técnico concreto y demostrable en `safe_path::resolve()`.

---

## Formato de respuesta esperado

```
MODELO: [nombre]

P1: [ACEPTO weakly_canonical | PROPONGO alternativa: ...]
P2: [ACEPTO granularidad por componente | PREFIERO prefijo único | OTRO: ...]
P3: [MISMO estándar para contrib/tools | NIVEL MENOR aceptable | ...]
P4: [ACEPTO FP — no modificar código | RECHAZO FP — vector de ataque: ...]

OBSERVACIONES ADICIONALES: [opcional, solo si hay algo crítico no cubierto]
```

---

El pipeline protege infraestructura crítica real. Vuestro análisis importa.

*Alonso Isidoro Roman — aRGus NDR, DAY 123*
*"Via Appia Quality — la superficie mínima es la superficie más segura."*