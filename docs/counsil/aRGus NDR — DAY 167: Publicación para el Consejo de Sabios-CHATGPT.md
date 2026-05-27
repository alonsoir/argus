## Consejo de Sabios — Respuesta DAY 167

La sensación general es que habéis cruzado una frontera importante: no es “solo” un Jenkins verde. Habéis demostrado que EMECAS++ puede ejecutarse de forma determinista en CI bajo un entorno hostil/no ideal (VirtualBox + nested orchestration + Vault + etcd fault injection). Eso tiene mucho valor arquitectónico.

---

# Q1 — `KNOWN-FAIL-VM-PERF-001`: ¿excluir o aceptar?

Consenso fuerte hacia **C** con una variante híbrida mínima de B.

### Recomendación principal:

* Mantener los fallos visibles.
* Documentarlos explícitamente en:

    * `docs/KNOWN-FAILS.md`
    * salida Jenkins
    * comentario inline en `Jenkinsfile.dev`

### Motivo

Ocultar tests de performance en CI virtualizado suele acabar degradando la señal del sistema. Hoy son thresholds imposibles; mañana puede aparecer un fallo funcional real y quedar enterrado bajo “el filtro”.

La transparencia aquí es importante porque:

* EMECAS++ es vuestro gate real.
* El pipeline ya comunica correctamente “SUCCESS”.
* Los fallos no son silenciosos.
* El operador entiende el contexto.

### Lo que el Consejo evitaría

#### Evitar A (`DISABLED`)

Porque:

* introduce divergencia semántica entre CI y runtime real;
* reduce observabilidad;
* crea deuda invisible.

### Variante aceptable

Si el ruido visual empieza a afectar productividad:

* usar B parcialmente,
* pero únicamente para los tests puramente temporales/performance,
* nunca para funcionales.

Ejemplo sano:

```bash
--gtest_filter=-IPSetWrapperTest.BatchAddPerformance
```

Pero dejando:

* functional tests activos;
* warning explícito en logs.

### Recomendación final

**C hoy.**
Migrar parcialmente hacia B únicamente si el ruido operacional se vuelve inaceptable.

---

# Q2 — `.deb` vs Suricata

El Consejo está bastante alineado:

## Suricata primero.

No por “más importante técnicamente”, sino por:

* valor demostrativo FEDER;
* capacidad de enseñar correlación multicapa;
* percepción de madurez del sistema;
* impacto visual y narrativo.

Un `.deb`:

* mejora distribución;
* mejora packaging;
* mejora DX/ops.

Pero Suricata:

* amplía capacidad operacional real;
* mejora detección;
* fortalece la tesis “NDR enterprise”.

## Recomendación concreta

Orden recomendado:

1. NTP gate mínimo.
2. Suricata integration.
3. Community ID.
4. Packaging `.deb`.
5. Deploy automation.

### Motivo estratégico

Ahora mismo el cuello de botella no es distribución:
es capacidad demostrable.

Para una demo:

* “correlación Zeek + Suricata + EMECAS++”
  vende muchísimo más que:
* “generamos un paquete `.deb`”.

---

# Q3 — NTP como P0 gate

Aquí el Consejo es bastante firme:

## Sí, debe entrar antes de Suricata.

Pero:

* como gate ligero;
* no como megaproyecto.

ADR-046 v3 lo declara P0.
Si no está en EMECAS++, la semántica de “P0” queda incoherente.

Además:

* correlación temporal;
* ordering de eventos;
* trazabilidad de incidentes;
* TTL cryptográfico;
* Vault leases;
* rotación de epochs;

…todo depende críticamente del tiempo.

## Recomendación

Incluirlo en Acto I como:

* bootstrap health gate;
* check rápido;
* fail-fast.

Ejemplo conceptual:

```bash
chronyc tracking
offset > 1s => FAIL
```

No hace falta algo más sofisticado inicialmente.

### Consejo adicional

No bloquearía DAYs enteros por esto.
Es:

* un hardening pequeño,
* pero arquitectónicamente correcto.

---

# Q4 — `BACKLOG-CRYPTO-VENDOR-KEY-001`

Aquí hay división parcial del Consejo.

## Mayoría:

### Hacerlo antes de Suricata.

Porque:

* toca raíz de confianza;
* elimina secreto persistente en repo;
* endurece supply chain;
* limpia arquitectura enterprise.

Y especialmente porque:

* ahora que Jenkins funciona,
* podéis integrar Vault correctamente,
* aprovechando el momentum CI.

## Minoría:

Suricata primero por valor visible.

---

# Síntesis equilibrada recomendada

## Orden óptimo sugerido

### DAY 168

* cerrar commits/tag/docs;
* introducir NTP gate mínimo;
* mover `vendor.key` a Vault/env Jenkins.

### DAY 169+

* integración Suricata;
* Community ID;
* correlación.

### Posteriormente

* `.deb`;
* deploy automation;
* packaging completo.

---

# Observación arquitectónica importante

El fix:

```bash
pkill -x etcd-server &
```

es más importante de lo que parece.

El Consejo considera que habéis descubierto un patrón clásico de CI distribuido:

> herramientas de fault injection que accidentalmente degradan el supervisor padre.

Eso valida que EMECAS++ ya está entrando en una zona donde aparecen bugs “de infraestructura real”, no simples bugs de aplicación.

Es una señal de madurez del sistema.
