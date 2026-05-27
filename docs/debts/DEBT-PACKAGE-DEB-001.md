# DEBT-PACKAGE-DEB-001

## Estado
Abierta — DAY 161

## Descripción
Producir un paquete .deb instalable de aRGus NDR como artefacto primario de release.

## Motivación
El artefacto de distribución final es un .deb, no una Vagrant box.
Jenkins debe archivar el .deb y make deploy-vagrant-test debe instalarlo en VM limpia.

## Trabajo requerido
- Estructura Debian: DEBIAN/control, preinst, postinst, postrm
- Directorios: usr/bin/, usr/lib/, etc/ml-defender/, lib/systemd/system/
- Binarios: etcd-server, sniffer, ml-detector, firewall-acl-agent, rag-ingester, rag-security
- Libs: libcrypto_transport.so, libseed_client.so, libplugin_loader.so, libetcd_client.so
- CPack o dpkg-deb
- Targets Makefile: make package-deb, make deploy-vagrant-test

## Prerequisitos
- Hardware físico UEx disponible (RPi5x2 + N100x2)
- Servidor Jenkins real (DEBT-JENKINS-PROD-001)
- DEBT-CONFIG-JINJA2-PIPELINE-001 resuelto (configs generadas, no originales)

## Prioridad
P2 — post hardware UEx

## Deadline
Antes de primera demo FEDER
