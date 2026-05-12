# aRGus NDR -- Schema Arrow: firewall_acl_events
# SECRETO INDUSTRIAL -- no exponer en docs/ publicos
# Consejo DAY 148: 8/8 aprobado. Tipos acordados.
# DEBT-PARQUET-TIMESTAMP-NS-001: firewall-acl-agent produce ms.
# Workaround: writer multiplica x 1_000_000 -> ns en Parquet.
# Fix correcto: modificar firewall-acl-agent para emitir ns en origen.
# Revisar rag-security si en algun momento consume Parquet directamente.
import pyarrow as pa

FIREWALL_ACTION = {"ALLOW": 0, "BLOCKED": 1}

schema_firewall = pa.schema([
    pa.field("timestamp_utc_ns", pa.int64(),
             metadata={b"note": b"epoch ns UTC - fuente CSV en ms, x1_000_000 en ingesta"}),
    pa.field("anon_src_host_id", pa.dictionary(pa.int32(), pa.utf8()),
             metadata={b"note": b"HMAC-SHA256(K_pseudo) - IP en claro en test"}),
    pa.field("anon_dst_host_id", pa.dictionary(pa.int32(), pa.utf8()),
             metadata={b"note": b"HMAC-SHA256(K_pseudo) - IP en claro en test"}),
    pa.field("threat_label",     pa.dictionary(pa.int32(), pa.utf8())),
    pa.field("action",           pa.int8(),
             metadata={b"encoding": b"0=ALLOW 1=BLOCKED"}),
    pa.field("confidence",       pa.float32()),
    pa.field("ed25519_sig",      pa.utf8(),
             metadata={b"note": b"Ed25519 hex 64 chars"}),
])
