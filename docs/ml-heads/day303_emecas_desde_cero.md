# DAY303 — EMECAS+++ desde cero de verdad, en producción, con los E2E del lab como puerta

Rama certificada `fix/ddos-etapa1-histeresis` (último commit `52307b19`). EMECAS+++ `PROFILE=production`: inicio 2026-10-21 08:40:20, fin 2026-10-21 11:13:12,
**2h32m**, rc=0, `EMECAS+++ PASSED`. Log: `logs/lab/emecas/emecas_20261021_084020.log`.

## Decisiones de Alonso (DAY303)

- Compilar y probar siempre en producción (`PROFILE ?= production`): máxima confianza en el compilador.
- EMECAS+++ certifica el merge. El pase con sanitizers (ASan/TSan) queda para hardware real de
  preproducción/producción, no para el Mac de 2019.
- EMECAS estricto y determinista: si pasa, el pipeline E2E funciona como se diseñó, sin más.
- rag/rag-security: su deprecado se certifica en una rama propia tras este merge (no se mezclan tareas).

## Lo que estaba mal y cómo se midió

| Hallazgo | Medida | Arreglo |
|---|---|---|
| Inyectores del E2E sintético sin recompilar desde junio | `tools/build-*/synthetic_*` del 7 y 12-jun | `pipeline-build` incluye `tools` |
| Todos los `build-active` apuntaban a `build-debug` desde el 14-oct | `ls -ld */build-active` | `pipeline-build` termina con `set-build-profile` |
| `set-build-profile` solo en `bootstrap` y ANTES de compilar (se salta lo que no existe) | `set-build-profile.sh` + orden de `bootstrap` | idem |
| rag-security arrancaba un binario debug del 14-abr; `rag-build` compilaba en `rag/build` | `ls -l rag/build*/rag-security` | `RAG_BUILD_DIR` por perfil; `rag-start` desde `$(RAG_BUILD_DIR)` |
| EMECAS no limpiaba nada: `/vagrant` es la carpeta del Mac y sobrevive a `vagrant destroy` | K1-K5 | `clean-host-builds` en el Mac, antes de `vagrant up` |
| `provision.sh` compila seed-client, crypto-transport, plugin-loader y etcd-client en `/vagrant/*/build` durante el `up` | K11 | idem (un `clean-all` tras el `up` rompía `libcrypto_transport.so`) |
| `crypto-transport/build` versionado en git (Makefile de CMake y `.so`) | K12 | fuera del índice y en `.gitignore` |
| `tools/build` (enlace generado) versionado | `git ls-files -s` | fuera del índice y en `.gitignore` |
| Los E2E del lab dependían del ruido de fondo de Wazuh/Zeek (5 VMs) para "esperar ESTABLE" | K13-K15: el lector solo escribe claves con paquetes; 6 filas en 120 s con 3 VMs | fondo ICMP controlado solo durante la espera |
| Los análisis de DAY300 no tenían PASA/FALLA (solo medían) | D1 | veredictos estrictos con criterios del diseño |
| Step 4 de Vault: `$(CMAKE_FLAGS)` (con comillas dobles) dentro de `vagrant ssh -c "..."` | 7 argumentos para vagrant (shlex) | comillas simples, verificado con shlex en los 4 perfiles |
| Los E2E del lab paran el pipeline y el acto II lo necesita arrancado | injector sin etcd-server en 2379, timeout 124 | `lab-e2e` termina con `pipeline-start` y exige 5/5 RUNNING |
| `pgrep -a -f` se imprime a sí mismo: su línea contiene `STOPPED` | falso positivo de `grep STOPPED` | patrón estricto `^ *❌ ... STOPPED` |

## Puertas de EMECAS y sus números

Limpieza en el Mac:
    [CLEAN-HOST] PASA: 0 directorios de build en el Mac

Frescura (cada binario del pipeline en `build-production`, `build-active` apuntando ahí y más nuevo que el sello
escrito tras el `vagrant up`):
    [FRESCURA] ok    etcd-server: etcd-server 2026-10-21 07:16:15
    [FRESCURA] ok    rag: rag-security 2026-10-21 07:17:08
    [FRESCURA] ok    rag-ingester: rag-ingester 2026-10-21 07:19:03
    [FRESCURA] ok    ml-detector: ml-detector 2026-10-21 07:22:30
    [FRESCURA] ok    sniffer: sniffer 2026-10-21 07:28:06
    [FRESCURA] ok    firewall-acl-agent: firewall-acl-agent 2026-10-21 07:31:07
    [FRESCURA] ok    tools: synthetic_sniffer_injector 2026-10-21 07:33:26
    [FRESCURA] ok    tools: synthetic_ml_output_injector 2026-10-21 07:33:36
    [FRESCURA] resumen perfil=production sello=/vagrant/logs/lab/emecas_inicio.stamp comprobados=8 fallos=0
    [FRESCURA] PASA

Puerta del firewall con root (`ctest_label_gate.sh`, falla con cualquier test saltado o gtest de 0 tests):
    [CTEST-GATE] resumen etiqueta=e2e rc_ctest=0 tests=23 saltados_ctest=0 saltados_gtest=0 did_not_run=0 gtest_vacios=0
    [CTEST-GATE] PASA (e2e): 23 tests, 0 saltados
    [CTEST-GATE] resumen etiqueta=perf rc_ctest=0 tests=2 saltados_ctest=0 saltados_gtest=0 did_not_run=0 gtest_vacios=0
    [CTEST-GATE] PASA (perf): 2 tests, 0 saltados

Medidas de rendimiento (no fallan por tiempo; solo por medida inválida):
    [PERF] add_batch 1000 IPs (fichero temporal + 1 proceso 'ipset restore -exist'): n=20 min=14530.2 p50=17204.2 p99=25368.3 max=25368.3 media=17866.4 us | set vaciado antes de cada medida; 1 vuelta de calentamiento descartada
    [PERF] add_batch 1000 IPs: 58125 IPs/s a p50
    [PERF] test() IP presente: n=500 min=2638.4 p50=3689.7 p99=6600.5 max=33999.2 media=3918.9 us | set de 10000 IPs; 1 proceso 'ipset test' por consulta (fork+execv), NO el hash del kernel
    [PERF] test() IP ausente: n=500 min=2696.6 p50=3693.3 p99=5878.8 max=38718.4 media=3881.5 us | set de 10000 IPs; 1 proceso 'ipset test' por consulta (fork+execv), NO el hash del kernel
    [PERF] test() todas: n=1000 min=2638.4 p50=3693.3 p99=6102.0 max=38718.4 media=3900.2 us | set de 10000 IPs; 1 proceso 'ipset test' por consulta (fork+execv), NO el hash del kernel

E2E del lab (`lab-e2e`), veredictos:
    [VEREDICTO] PASA  R1 identidad: ml marcados 8260+0=8260 = firewall DROP_resumenes 8260
    [VEREDICTO] PASA  R2 restauracion: sin_estado_previo=2 restauradas=0 (1_bajo_presion=0) volcados_antes_de_restaurar=2 (1_bajo_presion=1)
    [VEREDICTO] PASA  R3 marcado: antes=8260 despues=0 (en frio, 0 tras el reinicio)
    [VEREDICTO] dato (no decide): razon despues/antes=0.000; banda DAY300 para ordenada/kill9 1,15-1,40
    [VEREDICTO] RESULTADO PASA (reinicio antes)
    [VEREDICTO] PASA  R1 identidad: ml marcados 8463+11827=20290 = firewall DROP_resumenes 20290
    [VEREDICTO] PASA  R2 restauracion: sin_estado_previo=1 restauradas=1 (1_bajo_presion=1) volcados_antes_de_restaurar=1 (1_bajo_presion=1)
    [VEREDICTO] PASA  R3 marcado: antes=8463 despues=11827 razon=1.397 (frontera 0,5)
    [VEREDICTO] dato (no decide): razon despues/antes=1.397; banda DAY300 para ordenada/kill9 1,15-1,40
    [VEREDICTO] RESULTADO PASA (reinicio ordenada)
    [VEREDICTO] PASA  R1 identidad: ml marcados 8525+11747=20272 = firewall DROP_resumenes 20272
    [VEREDICTO] PASA  R2 restauracion: sin_estado_previo=1 restauradas=1 (1_bajo_presion=1) volcados_antes_de_restaurar=0 (1_bajo_presion=0)
    [VEREDICTO] PASA  R3 marcado: antes=8525 despues=11747 razon=1.378 (frontera 0,5)
    [VEREDICTO] dato (no decide): razon despues/antes=1.378; banda DAY300 para ordenada/kill9 1,15-1,40
    [VEREDICTO] RESULTADO PASA (reinicio kill9)
    [VEREDICTO] PASA  P1 configuracion: intranet .61 del JSON (1), CONFIG-DEFAULT ddos_protegidos=0
    [VEREDICTO] PASA  P2 episodio: 1 FIN, origenes=192.168.100.50:10787
    [VEREDICTO] PASA  P3 alertas: alertas=5393 intranet=5393 dmz=0 externos_criticos=0 por_defecto=0
    [VEREDICTO] PASA  P4 identidad: DROP_resumenes 16180 = DROP_FIN 10787 + alertas 5393
    [VEREDICTO] PASA  P5 volumen: DROP_FIN 10787 en [10584, 10800], alertas 5393 en [5292, 5400]
    [VEREDICTO] RESULTADO PASA (protegidos)
    RESULTADO PASA
    === [11:00:38] HECHO: logs/lab/day303/lab_mitigacion/ (analisis rc=0)

## Validación de los veredictos antes de usarlos (V1)

Sobre las corridas guardadas de DAY300: `antes2`, `ordenada`, `kill9` y `protegidos` PASA; la `antes` original
(corte del log anotado antes de parar el sniffer, 997 marcados del sniffer viejo) FALLA solo en R3. El veredicto
aprueba lo que DAY300 dio por bueno y rechaza lo que se rechazó entonces.

La banda 1,15-1,40 de la razón no decide: en la corrida suelta de DAY303 `kill9` dio 1,487 (el `pkill` para antes
que `sniffer-stop`: menos ataque antes del corte, más después) y es una corrida correcta.
