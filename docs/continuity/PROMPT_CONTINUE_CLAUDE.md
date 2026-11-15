# aRGus NDR — prompt de continuidad DAY328 (sigue de DAY327)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.

## Dónde estamos
- Rama: `feat/etcd-ha-plano-control` (PR2b de **DEBT-ETCD-HA-TLS-RAFT-001**, ADR-048), en `c89da507f`, todo subido.
  F2 de Falco cerrado; recursos del anfitrión y los dos tests del clúster etcd, dentro de EMECAS.
- **EMECAS+++ desde cero DAY327 (14:17-19:15): 29 pasos en verde, rojo en `mitre-check`** (paso 30). Verdes por
  primera vez desde cero: `anfitrion-recursos`, `test-etcd-cluster`, `test-etcd-reinicio`, `test-clave-bronce`,
  `test-vault-unseal`, `test-falco-silencio`, `test-anfitrion-recursos`, `falco-silencio` (0 CRITICAL desde la creación
  de las 4 VMs), lab-e2e entero (1h51m) y los actos de emecas++. `mitre-check` se arregló (dos fallos, abajo) y pasó
  suelto sobre ese lab (titular 1215, invariante 0): **falta la corrida desde cero que certifique**.
- Commits de DAY327: `9a91811f2` test de silencio de Falco (`falco_silencio.py`, sonda incluida, 31 tests);
  `346ca4ff` semillas con `sudo sha256sum` + macros Notice de invariante e inyectores; `0333d7f56` pausa del escritor
  (`ETCD_REINICIO_ESCRITOR_S`, defecto 2); `0270e609e` los dos tests del clúster en emecas; `c8e21b4b2` R3 del reinicio
  cuenta `ALERTA_PROTEGIDO`; `ec2e3f4e1` + `7e54fdeae` recursos del anfitrión (16 tests); `2e4c63bdd` fuera los cuatro
  `d321_*`; `9a5a3771b` `kuzu_query` imprime el error de Kuzu; `7ccee51c0` + `c89da507f` mitre/ctu: poblador de
  `CORRELATES_FLOW` solo entre sensores distintos y la clave de 64 hex filtrada.
- Sin trackear en `scripts/etcd_ha/` (aplicados; se archivan tras el EMECAS bueno): los `d324_*`, `d325_*`, `d326_*` y
  de DAY327 `d327_f2f_silencio.py`, `d327_f2g_semillas_inyectores.py`, `d327_escritor_pausa.py`,
  `d327_emecas_plano_control.py`, `d327_r3_protegido.py`, `d327_recursos_anfitrion.py`, `d327_recursos_umbrales.py`,
  `d327_correlates.py`, `d327_clave_pty.py`, `d327_docs.py`.
- Lab al cerrar DAY327: arriba (el de la corrida de las 14:17) y sano: etcd 3/3, líder control-2.

## Lo siguiente, en este orden
1. **EMECAS+++ desde cero, el que certifica** (~5 h; la parte tras mitre-check no se ha visto desde DAY323). CLion
   cerrado. Lanzar con `nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &`;
   seguirlo con `tail -F logs/lab/emecas/emecas_actual.log` o `make emecas-progreso`; terminado cuando existe
   `logs/lab/emecas/emecas_actual.rc` (0 = verde). La barra de progreso calcula con los 22 pasos de la última buena (hoy
   son 30+): su «100 %» no vale. Muestreo del anfitrión en otra terminal (bucle de `sysctl` a `/tmp/…`).
2. Si verde: archivar los parcheadores en una rama de archivo del remoto, borrarlos del Mac, push, PR, merge. Después,
   **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`).
3. **Documentación** (decidida DAY326, pendiente): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001
   con las recomendaciones al admin sobre la clave de desellado (Shamir con `-pgp-keys` y YubiKey, HSM solo Enterprise,
   KMS de nube, transit desde el Vault de la VM admin; nunca en claro en disco), comprobado contra la documentación de
   Vault 2.2.1; ADR-048 (DAY324-327) y ADR-060 (argus-disco con `rutas`, `clave-publica`, desellado en Python,
   `unseal.key` vigilada, macros nuevas de Falco).
4. **Decidido DAY326, por medir**: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001): antes, medir si el
   etcd-server tiene un estado equivalente y leer cómo trata el firewall la ranura siguiente.
5. **Deudas nuevas de DAY327, fuera del PR2b** (en el BACKLOG): DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001 (el Raft entre nodos
   sale como ~11 flujos nuevos por segundo; 88 % del bronce de aRGus en la ventana MITRE) y DEBT-CRYPTO-NONCE-REINICIO-001
   (nonce de crypto-transport desde 0 en cada arranque con la misma clave; medir primero). DEBT-DDOS-COLATERAL-LEGITIMO-001
   ampliada (Alonso: hay que cerrarla; va después del PR2, antes de REA).
6. En el defender, borrar `/var/lib/ml-defender/firewall-linaje-anterior/` cuando se decida lo del suelo.

## Lecciones medidas DAY327
- **`vagrant ssh -c` desde una terminal abre pty y mete el stderr de la VM en el stdout**; con `nohup` (EMECAS) no. Un
  script que se lanza de las dos formas no puede tomar el stdout entero: filtrar la línea que se espera.
- Un veredicto antiguo puede romperse por lo que el diseño añadió después (el R3 de DAY322 no conocía `ALERTA_PROTEGIDO`
  y los sensores entraron en el manifiesto en DAY323): el pipeline hizo bien y el examinador no.
- **El swap no separa el Mac sano del ahogado** (7,2 GB sano, 5,3 GB ahogado); la carga y la presión sí. Tras
  `vagrant destroy` el swap baja solo (7,2 → 1,5 GB en 40 s → 0,76 en minutos). Recursos de EMECAS: tras el destroy.
- Con tres nodos, el sniffer del defender ve el Raft de etcd: cambia el volumen del grafo (13915 filas de aRGus en 96 s
  frente a ~1700 con un nodo). Cualquier emparejamiento por `community_id` tiene que ser entre sensores, no dentro.
- Una herramienta que esconde el error de su librería (`kuzu_query`) alarga el diagnóstico: medir sobre una copia de la
  BD fallida (`cp` al `/tmp` de la VM) sirvió para probar el arreglo en segundos sin otro EMECAS.
- Hipótesis de Claude que los datos tumbaron hoy: «EMECAS falló por recursos» (fue el R3); «carrera entre cortes» o
  «cola del ataque» en el R3; «el swap se libera del todo al destruir»; «la clave o el converter romperán mitre» (fue el
  poblador); «`community_id` vacío»; «4-5 h hasta el final» (eran 2h17m hasta lab-e2e en la primera corrida).

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- Falco: `provisioning/falco/argus_lab.yaml`; a las VMs con `vagrant provision <vm> --provision-with falco`. Macros de
  administración (Notice): etcdctl/curl con sudo (etcd-server.key), openssl desde bash (private.pem), argus-infra,
  `argus_lab_despliegue_etcd_server`, `argus_lab_clave_bronce`, `argus_lab_invariante_semilla`,
  `argus_lab_inyector_sintetico`. Dueño del desellado: `argus_lab_es_desellado`. Wazuh: 100551/100552/100553.
- Targets nuevos DAY327: `falco-silencio` (`FALCO_SILENCIO_DESDE=AAAA-MM-DDTHH:MM:SSZ` para medir a mano desde una
  marca), `test-falco-silencio`, `anfitrion-recursos` (`RECURSOS_PERFIL=emecas|lab_e2e`), `test-anfitrion-recursos`.
  Los de siempre: `etcd-cluster-deploy`, `etcd-vm-deploy`, `test-etcd-cluster`, `test-etcd-reinicio`,
  `test-plano-control`, `etcd-vm-check`, `protegidos-pubkey`, `protegidos-bootstrap`, `test-argus-infra`,
  `test-clave-bronce`, `test-vault-unseal`, `lab-e2e` y sus `lab-e2e-*`, `mitre-check`.
- Duraciones EMECAS+++ DAY327: vagrant-up 1h03m, bootstrap 51m, test-all 18m, lab-e2e 1h51m, emecas++ ~13 min,
  mitre-check 25 min (antes 14: el tráfico etcd).
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~3, swap 0,2-1,5 GB, nivel de memoria 79-84; lab sano carga
  hasta 8,2, swap hasta 7,2 GB, nivel ≥ 67, presión 1.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley.
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla; se copian a
  `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256. Lo que lleve tabuladores, por parcheador.
- Comandos exactos, en orden, diciendo dónde se ejecutan; salida a `/tmp/…` y `; cat`; no encadenar salidas grandes.
  `git grep`, nunca `grep -rn .` en la raíz. Un commit por cambio lógico, con el mensaje propuesto y `git status`
  antes del `git add`. Nunca reescribir la historia. Software de terceros solo de sus mantenedores. Sin usos nuevos
  de curl. Mientras corre un EMECAS no se aplica nada al repo.
- Claves privadas nunca en el repo ni por /vagrant.
