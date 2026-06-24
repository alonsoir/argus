# Circular al Consejo de Sabios — ADR-050 (DAY 193)

**Proyecto:** aRGus NDR · **Mantenedor:** Alonso · **Fecha:** 2026-06-23
**Adjunto:** `ADR-050 — Metodología de ground truth por emulación adversaria multi-sensor`
**Calendario:** FEDER go/no-go **1-ago-2026** · deadline **22-sep-2026** (~6 semanas al go/no-go).

---

## El encargo

No queremos validación. **Queremos que nos mordáis a saco.** Buscamos el **defecto
fatal**, no la palmadita. Medir, no votar. Si la hipótesis que mueve todo esto
(§1 del ADR) tiene un agujero que la invalida antes de empezar, decidlo ahora —
nos cuesta menos en junio que en agosto.

Tratáis este ADR como revisión por pares. **§3, §5 y §14 son código de seguridad
de facto** (frontera firewall, correlación multi-sensor, envenenamiento): vuestro
veto sobre esas partes pesa al máximo. El ADR pasa a *Aceptado* solo con **8/8**.

## La pregunta que más necesitamos resuelta: `DEBT-WAZUH-COMMUNITYID-001` (§5, P9)

aRGus (red, en el cable) y Wazuh (host) tienen que poder afirmar **sin ninguna
duda** que un evento de uno y un flujo del otro **son el uno para el otro**.
`community_id` lo lograría… pero **el NAT lo rompe** (aRGus ve post-NAT, Wazuh
pre-NAT → IDs distintos, fallo silencioso). Nuestros clientes son hospitales y
municipios: natean por defecto.

Dirección actual: **acuñar un índice propio con impronta en los adapters** +
ventana temporal como respaldo. **El nudo:** un índice propio solo une si se
**deriva de un invariante que ambos lados del NAT calculan idéntico**. El NAT
reescribe cabeceras, no el payload. **¿Qué invariante sobrevive — JA3/JA4 de TLS,
hash de bytes iniciales, patrones seq/ack, un token coordinable?** Y si no existe
ninguno: ¿es aceptable bajar de "inequívoco" a "ventana temporal probabilística", y
con qué **tasa de error de join** acotada? Esto es lo que más nos urge que rompáis
o resolváis.

## Las trece preguntas

Están completas en **§17 del ADR**, agrupadas por tema: hipótesis (P1–P3), toolset
(P4–P6), DeepSeek a ciegas (P7–P8), correlación multi-sensor (P9–P9-ter),
arquitectura distribuida (P10–P11), envenenamiento (P12), paper (P13). Respondednos
**pregunta a pregunta**, marcando explícitamente dónde **vetáis** y por qué.

## Protocolo de manejo (IMPORTANTE — preserva el método)

> **Medir sin envenenar la muestra.**
>
> - **Siete modelos** (Claude, Grok, ChatGPT, Qwen, Gemini, Kimi, Mistral) reciben
    >   el **ADR completo** + las trece preguntas.
> - **DeepSeek recibe SOLO P7 y P8, a ciegas:** **sin** el ADR y **sin §13**. Le
    >   pedimos que **busque en su memoria** qué features y distribuciones usó para
    >   generar los datasets sintéticos de ransomware/DDoS, y **confrontamos después** su
    >   respuesta contra §13. No por desconfianza — porque informarle contaminaría la
    >   muestra.

---

*Via Appia Quality — construido para durar décadas.*