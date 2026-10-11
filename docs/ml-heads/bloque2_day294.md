# Bloque 2 — cabeza DDoS v2 cableada en SOMBRA (DAY293-294)

Rama `feat/ddos-head-contract`. Continúa `bloque1_day293.md`.

## Qué se construyó
- Cabeza `ddos_v2` factorizada en C++: etapa 1 `victim_rate_ratio >= K` (K=3, en el JSON del ml-detector con defecto
  validado + aviso); etapa 2 RandomForest (100 árboles, 6 rasgos de flujo, umbrales CRUDOS, sin MinMax) solo bajo presión.
  Modelo `ddos_v2_fact_rf@day293-f3d6b261`.
- ml-detector: la cabeza corre en cada evento de flujo, sin compuerta de level1; `final_decision` y `overall_threat_score`
  salen SOLO de ddos_v2 (única cabeza arreglada). Resumen periódico `[DDOS-V2] bajo_presion=N ataque=M`.
- firewall-acl-agent en SOMBRA: `dry_run: true`, compuerta por `final_decision`, `DdosShadowPolicy` POR VÍCTIMA
  (m=5, k/n=3/5, hold=30 s; defectos de LABORATORIO en firewall.json con rango y aviso), registros INICIO/FIN con todo el
  contexto, resumen periódico `[SOMBRA-DDOS] resumen:`; reloj de la sombra = solo eventos de flujo. No bloquea nada.

## Medido
- Paridad Python/C++ del modelo: 127930/127930.
- DAY293, ntp 60 + base .51 en vivo: atacante 100 %, inocente 0 %; 0 en benigno.
- DAY294, E2E de la sombra (VMs sincronizadas por NTP): 1 INICIO (2 s de reloj de eventos tras el primer DROP; el primer
  DROP llega ~1,3 s tras el inicio del ataque), 1 FIN (29,3 s tras el último DROP), origenes solo 192.168.100.50:5357,
  0 del inocente .51 concurrente, p1_min 0,96.
- DAY294, corrida benigna que presiona la etapa 1 con tráfico nunca visto en entrenamiento (base .51 450 s + dnsperf real
  contra unbound a 30 y 100 q/s + subida TCP legítima 50 KB/s): 0 INICIO. Etapa 2: 2 positivos aislados en ~18000 filas
  bajo presión (~0,01 %), absorbidos por k=3/5. Subida TCP 50 KB/s: 0 positivos (el bosque viejo la marcaba al 100 %).

## Arreglos encontrados por el camino
- [DDOS-SHADOW-RELOJ-D293] dos bases de tiempo en event_timestamp congelaban el reloj de la sombra.
- [FW-DRYRUN-VERIF-D294] en dry_run el firewall moría al arrancar en un kernel sin ipsets.
- [ARGUS-LAB-NTP-D294] el client (sin Internet por diseño) toma la hora del defender.

## Límites conocidos (no se arreglan en este PR)
- Los del bloque 1: la etapa 2 aprende firmas de los generadores (tamaño + reflexión), no comportamiento; familia fuera
  ~0 %; víctima fría: el modelo no bloquea (regla fría del admin, futura).
- Fast-alert fuera de la decisión. El firewall NO bloquea (sombra); la mitigación real por víctima es otro PR.
- Observaciones DAY294 a medir: eventos no-flujo ~37/s bajo carga DNS; el reloj de eventos de flujo del firewall avanza
  ~0,55 s/s durante dns100 y recupera después (cola o semántica de event_timestamp).
