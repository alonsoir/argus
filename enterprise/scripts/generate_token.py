#!/usr/bin/env python3
"""
aRGus NDR — Enterprise Token Generator (provisional)
-----------------------------------------------------
Genera un token enterprise firmado con Ed25519.

Uso:
    # Generar keypair (solo la primera vez)
    python3 generate_token.py --gen-keypair --privkey argus_enterprise.key --pubkey argus_enterprise.pub

    # Generar token
    python3 generate_token.py \
        --privkey argus_enterprise.key \
        --instance-id hospital-badajoz-01 \
        --features vault_crypto \
        --days 365 \
        --out enterprise.token

    # Verificar token
    python3 generate_token.py --verify enterprise.token --pubkey argus_enterprise.pub

Dependencias:
    pip install cryptography
"""

import argparse
import base64
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PrivateFormat,
        PublicFormat,
        NoEncryption,
        load_pem_private_key,
        load_pem_public_key,
    )
    from cryptography.exceptions import InvalidSignature
except ImportError:
    print("ERROR: pip install cryptography", file=sys.stderr)
    sys.exit(1)

ARGUS_TOKEN_VERSION = "1"
SUPPORTED_FEATURES = {
    "vault_crypto",
    "dataset_generator",
    "ensemble_builder",
    "graph_engine",
    "wazuh_integration",
    "suricata_zeek",
    "dashboards",
}


def gen_keypair(privkey_path: Path, pubkey_path: Path) -> None:
    if privkey_path.exists():
        print(f"ERROR: {privkey_path} ya existe. No sobreescribo claves privadas.",
              file=sys.stderr)
        sys.exit(1)
    key = Ed25519PrivateKey.generate()
    privkey_path.write_bytes(
        key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    pubkey_path.write_bytes(
        key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    privkey_path.chmod(0o600)
    print(f"OK  Clave privada: {privkey_path}  (chmod 600)")
    print(f"OK  Clave pública: {pubkey_path}")
    print("AVISO: Guarda la clave privada fuera del repositorio.")


def generate_token(
    privkey_path: Path,
    instance_id: str,
    features: list[str],
    days: int,
    out_path: Path,
) -> None:
    unknown = set(features) - SUPPORTED_FEATURES
    if unknown:
        print(f"ERROR: features desconocidas: {unknown}", file=sys.stderr)
        print(f"       Válidas: {SUPPORTED_FEATURES}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    payload = {
        "version": ARGUS_TOKEN_VERSION,
        "instance_id": instance_id,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=days)).isoformat(),
        "features": sorted(features),
    }

    # Firma sobre JSON canónico (separadores sin espacios, claves ordenadas)
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    privkey_pem = privkey_path.read_bytes()
    key = load_pem_private_key(privkey_pem, password=None)
    signature = key.sign(payload_bytes)

    token = {
        "payload": base64.b64encode(payload_bytes).decode(),
        "signature": base64.b64encode(signature).decode(),
    }

    out_path.write_text(json.dumps(token, indent=2))
    print(f"OK  Token generado: {out_path}")
    print(f"    instance_id : {instance_id}")
    print(f"    features    : {sorted(features)}")
    print(f"    expires_at  : {payload['expires_at']}")


def verify_token(token_path: Path, pubkey_path: Path) -> None:
    token = json.loads(token_path.read_text())
    payload_bytes = base64.b64decode(token["payload"])
    signature = base64.b64decode(token["signature"])
    payload = json.loads(payload_bytes)

    pubkey_pem = pubkey_path.read_bytes()
    pubkey = load_pem_public_key(pubkey_pem)

    try:
        pubkey.verify(signature, payload_bytes)
    except InvalidSignature:
        print("FATAL: firma inválida.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(payload["expires_at"])
    if now > expires:
        print(f"FATAL: token expirado el {expires.isoformat()}", file=sys.stderr)
        sys.exit(1)

    print("OK  Token válido.")
    print(f"    instance_id : {payload['instance_id']}")
    print(f"    features    : {payload['features']}")
    print(f"    expires_at  : {payload['expires_at']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="aRGus Enterprise Token Generator")
    parser.add_argument("--gen-keypair", action="store_true")
    parser.add_argument("--privkey", type=Path, default=Path("argus_enterprise.key"))
    parser.add_argument("--pubkey", type=Path, default=Path("argus_enterprise.pub"))
    parser.add_argument("--instance-id", type=str)
    parser.add_argument("--features", nargs="+", default=["vault_crypto"])
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--out", type=Path, default=Path("enterprise.token"))
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()

    if args.gen_keypair:
        gen_keypair(args.privkey, args.pubkey)
    elif args.verify:
        verify_token(args.verify, args.pubkey)
    elif args.instance_id:
        generate_token(args.privkey, args.instance_id, args.features, args.days, args.out)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
