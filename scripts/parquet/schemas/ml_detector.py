# aRGus NDR -- Schema Arrow: ml_detector_events
# SECRETO INDUSTRIAL -- no exponer en docs/ publicos
# Consejo DAY 148: 8/8 aprobado. Tipos acordados.
import pyarrow as pa

ML_DETECTOR_CLASSIFICATION = {"BENIGN": 0, "MALICIOUS": 1}
ML_DETECTOR_ACTION         = {"ALLOW": 0, "DROP": 1, "BLOCK": 2}
SENTINEL = -9999.0  # valores CIC-IDS-2017 ausentes -> null en Parquet

schema_ml_detector = pa.schema([
    pa.field("timestamp_utc_ns", pa.int64(),
             metadata={b"note": b"epoch nanoseconds UTC"}),
    pa.field("flow_id",          pa.dictionary(pa.int32(), pa.utf8())),
    pa.field("anon_src_host_id", pa.dictionary(pa.int32(), pa.utf8()),
             metadata={b"note": b"HMAC-SHA256(K_pseudo) - vacio en test"}),
    pa.field("anon_dst_host_id", pa.dictionary(pa.int32(), pa.utf8()),
             metadata={b"note": b"HMAC-SHA256(K_pseudo) - vacio en test"}),
    pa.field("src_port",         pa.uint16()),
    pa.field("dst_port",         pa.uint16()),
    pa.field("protocol",         pa.int8()),
    pa.field("classification",   pa.int8(),
             metadata={b"encoding": b"0=BENIGN 1=MALICIOUS"}),
    pa.field("confidence",       pa.float32()),
    pa.field("threat_label",     pa.dictionary(pa.int32(), pa.utf8())),
    pa.field("threat_score",     pa.float32()),
    pa.field("score_a",          pa.float32()),
    pa.field("score_b",          pa.float32()),
    pa.field("action",           pa.int8(),
             metadata={b"encoding": b"0=ALLOW 1=DROP 2=BLOCK"}),
    pa.field("ed25519_sig",      pa.utf8(),
             metadata={b"note": b"Ed25519 hex 64 chars"}),
])
