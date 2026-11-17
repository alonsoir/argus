#!/usr/bin/env python3
# d324_pki_nodos.py — DAY324, PR2b paso 3 de DEBT-ETCD-HA-TLS-RAFT-001 [PKI-NODOS-D324]: d312_pki.sh gana el modo
# 'nodos', que emite con la CA existente, para CADA nodo de argus_control_nodos (la lista que valida nodos_control.rb),
# tres certificados con la IP del nodo en el SAN: etcd-<nodo> (OU=etcd: cliente y peer de etcd), vault-<nodo>
# (OU=vault: listener y unión al clúster raft) y etcd-server-<nodo> (OU=etcd-server; CN de instancia, porque tres
# etcd-server con CN=etcd-server se pisarían el registro). No pisa nada: un certificado que ya existe con su IP se
# deja; uno que existe SIN la IP del nodo hace fallar (la IP cambió: reemitir a mano). Y el Makefile gana
# test-pki-nodos (scripts/etcd_ha/test_pki_nodos.sh). Los certificados de un nodo de hoy (etcd, vault, etcd-server)
# no se tocan: se dejan de usar en el paso 4 (etcd), PR2c (Vault) y PR2d (etcd-server).
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_pki_nodos.py
import hashlib
import os
import sys

PKI = "scripts/etcd_ha/d312_pki.sh"
PARTIDA = {
    PKI: "8011d47d83e326169efb7442e010aec356e66680da9ab7a1991d84a9068a6e97",
    "Makefile": "54b871a2af566500fdda89547ff77d32dfe949cb0286452545a8970d1a7c5561",
}
NODOS_CASE = '''  nodos)
    # [PKI-NODOS-D324] un juego por nodo del plano de control, de la lista que valida nodos_control.rb (la misma del
    # Vagrantfile). CN = <perfil>-<nodo> (instancia), OU = perfil (rol); SAN = localhost, la IP del nodo y 127.0.0.1;
    # EKU servidor y cliente (etcd: peers; Vault: retry_join presenta certificado al listener; etcd-server: su
    # cliente de etcd y de Vault). Lo que ya existe con su IP se deja; sin su IP, se falla: no se pisa una clave.
    GVF=${3:-ansible/inventory/group_vars/argus_dev.yml}; VF=${4:-Vagrantfile}
    [ -f "$D/ca.crt" ] && [ -f "$D/ca.key" ] || falla "$D no tiene CA: primero init"
    fuera_de_git "$D"
    command -v ruby >/dev/null || falla "no hay ruby (lo necesita scripts/etcd_ha/nodos_control.rb)"
    LISTA=$(ruby "$(dirname "$0")/nodos_control.rb" nodos "$GVF" "$VF" 2>&1) || { echo "$LISTA"; falla "la lista de nodos de $GVF no vale"; }
    log "nodos de $GVF: $(printf '%s\\n' "$LISTA" | awk -F'\\t' '$1 == "nodo" {printf "%s=%s ", $2, $3}')"
    nuevos=0; ya=0
    while IFS=$'\\t' read -r k nodo ip mac; do
      [ "$k" = nodo ] || continue
      for perfil in etcd vault etcd-server; do
        nom="$perfil-$nodo"
        if [ -e "$D/$nom.crt" ]; then
          san_de "$D/$nom.crt" | grep -qx "IP:$ip" \\
            || falla "$D/$nom.crt existe sin IP:$ip en el SAN (¿cambió la IP de $nodo?): no se pisa; reemitir a mano"
          ya=$((ya+1))
        else
          firmar "$nom" "$nom" "$perfil" "serverAuth,clientAuth" "DNS:localhost,IP:$ip,IP:127.0.0.1"
          nuevos=$((nuevos+1))
        fi
      done
    done <<< "$LISTA"
    log "nodos: $nuevos certificados nuevos, $ya ya estaban con su IP"
    comprobar
    ;;
  reemitir)
'''
CAMBIOS = {
    PKI: [
        ("#   bash d312_pki.sh cliente DIR ROL [INSTANCIA] añade un certificado de cliente (CN=INSTANCIA, defecto ROL; OU=ROL)\n",
         "#   bash d312_pki.sh cliente DIR ROL [INSTANCIA] añade un certificado de cliente (CN=INSTANCIA, defecto ROL; OU=ROL)\n"
         "#   bash d312_pki.sh nodos   DIR [GROUP_VARS [VAGRANTFILE]]  [PKI-NODOS-D324] etcd-, vault- y etcd-server-<nodo> con\n"
         "#                                la IP de cada nodo de argus_control_nodos (desde la raíz del repo; ver el modo)\n"),
        ("huella() { openssl x509 -in \"$1\" -noout -fingerprint -sha256 | sed 's/^.*=//; s/://g' | tr 'A-F' 'a-f'; }\n",
         "huella() { openssl x509 -in \"$1\" -noout -fingerprint -sha256 | sed 's/^.*=//; s/://g' | tr 'A-F' 'a-f'; }\n"
         "# [PKI-NODOS-D324] entradas del SAN, una por línea (DNS:x, IP:x), con OpenSSL o LibreSSL (el del Mac)\n"
         "san_de() { openssl x509 -in \"$1\" -noout -text | sed -n '/Subject Alternative Name/{n;p;}' | tr ',' '\\n' \\\n"
         "  | sed 's/^ *//; s/IP Address:/IP:/'; }\n"),
        ('| $0 cliente DIR ROL [INSTANCIA]"', '| $0 cliente DIR ROL [INSTANCIA] | $0 nodos DIR [GROUP_VARS [VAGRANTFILE]]"'),
        ("  reemitir)\n", NODOS_CASE),
        ("(init | reemitir | cliente)", "(init | reemitir | cliente | nodos)"),
    ],
    "Makefile": [
        ("test-plano-control:\n\t@python3 -I scripts/etcd_ha/test_plano_control.py\n\n",
         "test-plano-control:\n\t@python3 -I scripts/etcd_ha/test_plano_control.py\n\n"
         "# [PKI-NODOS-D324] d312_pki.sh nodos sobre una PKI de usar y tirar en /tmp (Mac, sin VMs): SAN con la IP de cada\n"
         "# nodo, idempotente, y falla si un certificado no lleva la IP de su nodo o no lo firmó la CA\n"
         "test-pki-nodos:\n\t@bash scripts/etcd_ha/test_pki_nodos.sh\n\n"),
    ],
}


def falla(msg):
    print("[D324-PKI] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    nuevos = []
    for ruta, pares in CAMBIOS.items():
        if not os.path.isfile(ruta):
            falla(ruta + " no existe (¿raíz del repo?)")
        with open(ruta, "rb") as f:
            b = f.read()
        if sha(b) != PARTIDA[ruta]:
            falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + PARTIDA[ruta][:16] + ")")
        t = b.decode("utf-8")
        for viejo, nuevo in pares:
            k = t.count(viejo)
            if k != 1:
                falla("%s: '%s' aparece %d veces (esperada 1)" % (ruta, viejo.strip()[:60], k))
            t = t.replace(viejo, nuevo)
        nuevos.append((ruta, t))
    for ruta, t in nuevos:
        tmp = ruta + ".d324tmp"
        st = os.stat(ruta)
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-PKI] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-PKI] RESULTADO PASA: %d ficheros; ahora: make test-pki-nodos" % len(nuevos))


if __name__ == "__main__":
    main()
