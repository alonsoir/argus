#!/usr/bin/env python3
# host_domain_v1_ref.py
# aRGus NDR — REFERENCIA (oráculo autorado) del contrato bronce host_domain_v1.
# Authors: Alonso Isidoro Roman + Claude (Anthropic)
#
# PROCEDENCIA (DAY 241): a diferencia de correlation_v1 (cuyo golden se CAPTURÓ de un
# binario C++ previo), host_domain_v1 no tiene oráculo. ESTE fichero ES la definición
# ejecutable primaria: el `serialize` de C++ debe salir byte-idéntico a `serialize` de
# aquí sobre el dominio de los vectores congelados. Regenerar este script produce
# vectores idénticos (determinista) — esa es la propiedad que hace reproducible el paper.
#
# Tres primitivas (espejo 1:1 de las firmas de host_domain_v1.hpp):
#   mint_event_id(raw_line)      -> "wz1:" + base64_std(BLAKE2b-256("argus-hostevent-v1" || raw_line))
#   encode_string_list(items)    -> JSON compacto canónico  (json.dumps sep=(',',':'), ensure_ascii=False)
#   serialize(row, key)          -> línea bronce cols 0-33 (HMAC-SHA256 sobre 0-32)
#
# D-HOST-5 (decisión de contrato, DAY 241): TODA columna string pasa por csv_string
# (no-op salvo coma/comilla/newline); rule_level (col 11) es entero crudo. Diverge a
# propósito del reparto crudo 0,1,5,6,9,10 de correlation_v1, que era fidelidad a un
# oráculo que aquí no existe.

import base64
import hashlib
import hmac as _hmac
import json

TAG = b"argus-hostevent-v1"          # D-HOST-1
TOTAL_COLS = 34                       # 0-32 datos + 33 HMAC

# Orden posicional del contrato (cols 0-32). El nombre = miembro del struct C++.
COLS = [
    "schema_version",   # 0
    "source_sensor",    # 1
    "event_id",         # 2
    "host_id",          # 3
    "wazuh_alert_id",   # 4
    "timestamp",        # 5
    "agent_id",         # 6
    "agent_name",       # 7
    "agent_ip",         # 8
    "os_hostname",      # 9
    "rule_id",          # 10
    "rule_level",       # 11  <- ÚNICO entero (crudo)
    "rule_description", # 12
    "rule_groups",      # 13  [json]
    "decoder_name",     # 14
    "location",         # 15
    "full_log",         # 16
    "data_json",        # 17  [json]
    "srcuser",          # 18
    "dstuser",          # 19
    "srcip",            # 20
    "srcport",          # 21
    "uid",              # 22
    "command",          # 23
    "mitre_ids",        # 24  [json]
    "mitre_tactics",    # 25  [json]
    "mitre_techniques", # 26  [json]
    "pci_dss",          # 27  [json]
    "gdpr",             # 28  [json]
    "hipaa",            # 29  [json]
    "nist_800_53",      # 30  [json]
    "tsc",              # 31  [json]
    "gpg13",            # 32  [json]
]
RULE_LEVEL_COL = "rule_level"
STRING_COLS = [c for c in COLS if c != RULE_LEVEL_COL]   # 32 columnas string


# --- mint_event_id — PRIMITIVA de identidad (D-HOST-1) ----------------------
# raw_line = bytes EXACTOS de la línea JSON de alerts.json, tal cual la devuelve
# getline, SIN el \n terminador. Acepta str (se codifica utf-8) o bytes.
def mint_event_id(raw_line) -> str:
    if isinstance(raw_line, str):
        raw_line = raw_line.encode("utf-8")
    digest = hashlib.blake2b(TAG + raw_line, digest_size=32).digest()
    return "wz1:" + base64.b64encode(digest).decode("ascii")


# --- encode_string_list — PRIMITIVA de listas (D-HOST-2) --------------------
def encode_string_list(items) -> str:
    return json.dumps(list(items), separators=(",", ":"), ensure_ascii=False)


# --- csv_string — espejo del de correlation_v1 (locale-safe, manipulación de chars) --
def csv_string(s: str) -> str:
    if not any(c in s for c in (",", '"', "\n")):
        return s
    return '"' + s.replace('"', '""') + '"'


# --- compute_hmac — HMAC-SHA256 sobre el contenido de cols 0-32, hex minúsculas ----
def compute_hmac(content: str, key: bytes) -> str:
    return _hmac.new(key, content.encode("utf-8"), hashlib.sha256).hexdigest()


# --- build_cols_0_32 — orden/separadores/quoting del contrato (D-HOST-5) -----
def build_cols_0_32(row: dict) -> str:
    out = []
    for c in COLS:
        if c == RULE_LEVEL_COL:
            out.append(str(int(row[c])))          # entero crudo, sin locale grouping
        else:
            out.append(csv_string(str(row[c])))    # D-HOST-5: csv_string universal
    return ",".join(out)


# --- validate — NOTARIO ÚNICO (P3). v1 mínimo (medir, no votar) --------------
# ERROR FUNDAMENTAL: host_id vacío (PK del nodo Host ausente) -> va primero.
# NEWLINE-GUARD: \n/\r embebido en cualquier col string rompe el reader getline.
# DIFERIDO a commit de contrato posterior (no en v1): rule_id no vacío, rango de
# rule_level, formato de event_id ("wz1:"+base64). Se añaden cuando se mida la necesidad.
def validate(row: dict) -> tuple:
    if str(row["host_id"]) == "":
        return (False, "host_id vacío: PK del nodo Host ausente (error fundamental)")
    for c in STRING_COLS:
        v = str(row[c])
        if "\n" in v or "\r" in v:
            return (False, ("col texto '" + c + "' contiene \\n o \\r embebido: "
                                                "rompe el reader getline (DEBT-BRONZE-EMBEDDED-NEWLINE-001)"))
    return (True, "")


# --- serialize — Row -> línea bronce (cols 0-33). PURA: (row, key) y nada más --------
def serialize(row: dict, key: bytes) -> tuple:
    ok, err = validate(row)
    if not ok:
        return (False, "", err)
    if len(key) != 32:
        return (False, "", ("hmac_key debe ser 32 bytes (got " + str(len(key)) +
                            "): clave ausente o incorrecta"))
    cols_0_32 = build_cols_0_32(row)
    h = compute_hmac(cols_0_32, key)
    return (True, cols_0_32 + "," + h, "")


# ============================================================================
# Generación de vectores congelados
# ============================================================================
# Clave HMAC de test FIJA (32 bytes de 0xAB), idéntica al kTestKey del C++.
# En producción viene de ARGUS_BRONZE_HMAC_KEY_HEX (compartida con la red).
TEST_KEY_HEX = "ab" * 32
TEST_KEY = bytes.fromhex(TEST_KEY_HEX)


def base_row() -> dict:
    r = {c: "" for c in STRING_COLS}
    r["rule_level"] = 0
    r["schema_version"] = "host_domain_v1"
    r["source_sensor"] = "wazuh"
    # listas vacías por defecto = "[]"
    for c in ("rule_groups", "mitre_ids", "mitre_tactics", "mitre_techniques",
              "pci_dss", "gdpr", "hipaa", "nist_800_53", "tsc", "gpg13"):
        r[c] = encode_string_list([])
    r["data_json"] = "{}"
    return r


def build_vectors() -> dict:
    # ---------- mint_event_id ----------
    raw_a = ('{"timestamp":"2026-07-31T03:22:09.071+0000","rule":{"level":3,'
             '"id":"5715"},"agent":{"id":"002","name":"zeek","ip":"192.168.100.11"},'
             '"id":"1785468156.2917"}')
    raw_b = "{}"
    mint_vectors = [
        {"name": "sshd_line", "raw_line": raw_a, "expected": mint_event_id(raw_a)},
        {"name": "empty_obj", "raw_line": raw_b, "expected": mint_event_id(raw_b)},
    ]

    # ---------- encode_string_list ----------
    esl_cases = [
        ("empty", []),
        ("groups", ["syslog", "pam", "authentication_success"]),
        ("mitre_ids", ["T1078", "T1021"]),
        ("single", ["authentication_success"]),
        ("with_quote", ['he said "hi"']),          # congela el escaping JSON
        ("utf8", ["café", "über"]),                 # congela ensure_ascii=False
    ]
    esl_vectors = [{"name": n, "items": it, "expected": encode_string_list(it)}
                   for n, it in esl_cases]

    # ---------- serialize OK ----------
    ok_rows = []

    # 1) sshd 5715 — auth success, MITRE T1078+T1021 (Lateral Movement), coordenada de red
    r = base_row()
    r["event_id"] = mint_event_id(raw_a)
    r["host_id"] = "002"
    r["wazuh_alert_id"] = "1785468156.2917"
    r["timestamp"] = "2026-07-31T03:22:09.071+0000"
    r["agent_id"] = "002"; r["agent_name"] = "zeek"; r["agent_ip"] = "192.168.100.11"
    r["os_hostname"] = "argus-zeek"
    r["rule_id"] = "5715"; r["rule_level"] = 3
    r["rule_description"] = "sshd: authentication success"
    r["rule_groups"] = encode_string_list(["syslog", "sshd", "authentication_success"])
    r["decoder_name"] = "sshd"; r["location"] = "journald"
    r["full_log"] = "Accepted password for root from 10.0.2.2 port 55043 ssh2"
    r["data_json"] = '{"srcip":"10.0.2.2","srcport":"55043","dstuser":"root"}'
    r["srcip"] = "10.0.2.2"; r["srcport"] = "55043"; r["dstuser"] = "root"
    r["mitre_ids"] = encode_string_list(["T1078", "T1021"])
    r["mitre_tactics"] = encode_string_list(["Initial Access", "Lateral Movement"])
    r["mitre_techniques"] = encode_string_list(["Valid Accounts", "Remote Services"])
    r["pci_dss"] = encode_string_list(["10.2.5"])
    r["hipaa"] = encode_string_list(["164.312.b"])
    r["gdpr"] = encode_string_list(["IV_35.7.d"])
    ok_rows.append(("sshd_5715_lateral", r))

    # 2) sudo->ROOT 5402 — T1548.003, data con command (path con espacios)
    r = base_row()
    raw2 = '{"rule":{"id":"5402","level":3},"agent":{"id":"000"},"id":"1785468200.4410"}'
    r["event_id"] = mint_event_id(raw2)
    r["host_id"] = "000"
    r["wazuh_alert_id"] = "1785468200.4410"
    r["timestamp"] = "2026-07-31T03:23:20.410+0000"
    r["agent_id"] = "000"; r["agent_name"] = "argus-wazuh"; r["agent_ip"] = ""
    r["os_hostname"] = "argus-wazuh"
    r["rule_id"] = "5402"; r["rule_level"] = 3
    r["rule_description"] = "Successful sudo to ROOT executed"
    r["rule_groups"] = encode_string_list(["syslog", "sudo"])
    r["decoder_name"] = "sudo"; r["location"] = "journald"
    r["full_log"] = "vagrant : TTY=pts/0 ; PWD=/home/vagrant ; USER=root ; COMMAND=/usr/bin/apt install wazuh-agent"
    r["data_json"] = ('{"srcuser":"vagrant","dstuser":"root","pwd":"/home/vagrant",'
                      '"command":"/usr/bin/apt install wazuh-agent"}')
    r["srcuser"] = "vagrant"; r["dstuser"] = "root"
    r["command"] = "/usr/bin/apt install wazuh-agent"
    r["mitre_ids"] = encode_string_list(["T1548.003"])
    r["mitre_tactics"] = encode_string_list(["Privilege Escalation", "Defense Evasion"])
    r["mitre_techniques"] = encode_string_list(["Abuse Elevation Control Mechanism"])
    r["pci_dss"] = encode_string_list(["10.2.5", "10.2.2"])
    ok_rows.append(("sudo_5402_privesc", r))

    # 3) PAM 5501 — T1078, data con uid presente, srcport ausente ("")
    r = base_row()
    raw3 = '{"rule":{"id":"5501","level":3},"agent":{"id":"002"},"id":"1785468156.1204"}'
    r["event_id"] = mint_event_id(raw3)
    r["host_id"] = "002"
    r["wazuh_alert_id"] = "1785468156.1204"
    r["timestamp"] = "2026-07-31T03:22:36.204+0000"
    r["agent_id"] = "002"; r["agent_name"] = "zeek"; r["agent_ip"] = "192.168.100.11"
    r["os_hostname"] = "argus-zeek"
    r["rule_id"] = "5501"; r["rule_level"] = 3
    r["rule_description"] = "PAM: Login session opened."
    r["rule_groups"] = encode_string_list(["syslog", "pam", "authentication_success"])
    r["decoder_name"] = "pam"; r["location"] = "journald"
    r["full_log"] = "session opened for user root(uid=0) by (uid=0)"
    r["data_json"] = '{"dstuser":"root","uid":"0"}'
    r["dstuser"] = "root"; r["uid"] = "0"   # srcport queda "" (ausente)
    r["mitre_ids"] = encode_string_list(["T1078"])
    r["mitre_tactics"] = encode_string_list(["Initial Access"])
    r["mitre_techniques"] = encode_string_list(["Valid Accounts"])
    ok_rows.append(("pam_5501_login", r))

    # 4) netstat 533 — SIN data, SIN mitre: listas "[]", comunes "", data_json "{}"
    r = base_row()
    raw4 = '{"rule":{"id":"533","level":7},"agent":{"id":"000"},"id":"1785468300.9001"}'
    r["event_id"] = mint_event_id(raw4)
    r["host_id"] = "000"
    r["wazuh_alert_id"] = "1785468300.9001"
    r["timestamp"] = "2026-07-31T03:25:00.901+0000"
    r["agent_id"] = "000"; r["agent_name"] = "argus-wazuh"
    r["os_hostname"] = "argus-wazuh"
    r["rule_id"] = "533"; r["rule_level"] = 7
    r["rule_description"] = "Listened ports status (netstat) changed (new port opened or closed)."
    r["rule_groups"] = encode_string_list(["ossec"])
    r["decoder_name"] = ""; r["location"] = "netstat listening ports"
    r["full_log"] = "ossec: output: 'netstat listening ports':\ntcp 0.0.0.0:1514"  # <- NOTA abajo
    ok_rows.append(("netstat_533_nodata", r))

    # 5) \t embebido en command -> validate ACEPTA, serialize emite (frontera del guard)
    r = base_row()
    r["event_id"] = "wz1:PLACEHOLDER"
    r["host_id"] = "000"
    r["rule_id"] = "5402"; r["rule_level"] = 3
    r["command"] = "col1\tcol2"          # \t NO rompe getline
    ok_rows.append(("tab_in_command_ok", r))

    # OJO: el vector 4 lleva un \n embebido en full_log a propósito, para que sea REJECT,
    # no OK. Lo movemos a la lista de rechazos (ver abajo) y dejamos el 4 limpio.
    ok_rows[3][1]["full_log"] = ("ossec: output: 'netstat listening ports': "
                                 "tcp 0.0.0.0:1514 LISTEN")

    serialize_ok = []
    for name, row in ok_rows:
        ok, line, err = serialize(row, TEST_KEY)
        assert ok, "vector OK que no serializa: " + name + " -> " + err
        serialize_ok.append({"name": name, "row": row, "expected_line": line})

    # ---------- serialize REJECT (validate rechaza, serialize no emite) ----------
    reject = []

    # host_id vacío
    r = base_row(); r["host_id"] = ""; r["rule_id"] = "5501"; r["rule_level"] = 3
    reject.append(("host_id_empty", r, "host_id vacío"))

    # \n embebido en full_log
    r = base_row(); r["host_id"] = "000"; r["rule_id"] = "533"; r["rule_level"] = 7
    r["full_log"] = "linea1\nlinea2"
    reject.append(("newline_in_full_log", r, "\\n o \\r embebido"))

    # \r embebido en event_id
    r = base_row(); r["host_id"] = "000"; r["rule_id"] = "5402"; r["rule_level"] = 3
    r["event_id"] = "wz1:AAA\rBBB"
    reject.append(("cr_in_event_id", r, "\\n o \\r embebido"))

    serialize_reject = []
    for name, row, substr in reject:
        ok, line, err = serialize(row, TEST_KEY)
        assert not ok, "vector REJECT que sí serializa: " + name
        assert substr in err, "diagnóstico inesperado en " + name + ": " + err
        serialize_reject.append({"name": name, "row": row,
                                 "expected_error_substr": substr})

    return {
        "meta": {
            "contract": "host_domain_v1",
            "total_cols": TOTAL_COLS,
            "hmac": "HMAC-SHA256 sobre cols 0-32 (col 33)",
            "event_id": "wz1: + base64_std(BLAKE2b-256(argus-hostevent-v1 || raw_line))",
            "list_encoding": "json.dumps(sep=(',',':'), ensure_ascii=False)",
            "quoting": "D-HOST-5: csv_string en TODAS las columnas string; rule_level entero crudo",
            "generated_by": "host_domain_v1_ref.py (determinista; regenerar da bytes idénticos)",
        },
        "hmac_key_hex": TEST_KEY_HEX,
        "mint_event_id": mint_vectors,
        "encode_string_list": esl_vectors,
        "serialize_ok": serialize_ok,
        "serialize_reject": serialize_reject,
    }


def _self_check(vectors: dict) -> None:
    # Re-serializa cada vector OK y compara -> determinismo.
    key = bytes.fromhex(vectors["hmac_key_hex"])
    for v in vectors["serialize_ok"]:
        ok, line, _ = serialize(v["row"], key)
        assert ok and line == v["expected_line"], "round-trip roto: " + v["name"]
    # Re-mint / re-encode.
    for v in vectors["mint_event_id"]:
        assert mint_event_id(v["raw_line"]) == v["expected"], "mint roto: " + v["name"]
    for v in vectors["encode_string_list"]:
        assert encode_string_list(v["items"]) == v["expected"], "encode roto: " + v["name"]
    # Estructura de línea: cada línea OK tiene 34 celdas lógicas y la HMAC es 64 hex.
    for v in vectors["serialize_ok"]:
        hmac_cell = v["expected_line"].rsplit(",", 1)[1]
        assert len(hmac_cell) == 64 and all(ch in "0123456789abcdef" for ch in hmac_cell)


if __name__ == "__main__":
    import sys
    vectors = build_vectors()
    _self_check(vectors)
    out = "host_domain_v1_vectors.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(vectors, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("OK — vectores generados y auto-verificados:", out)
    print("  mint_event_id     :", len(vectors["mint_event_id"]))
    print("  encode_string_list:", len(vectors["encode_string_list"]))
    print("  serialize_ok      :", len(vectors["serialize_ok"]))
    print("  serialize_reject  :", len(vectors["serialize_reject"]))
    print()
    print("Muestra — sshd_5715_lateral (línea bronce, truncada a 240 chars):")
    print(" ", vectors["serialize_ok"][0]["expected_line"][:240], "...")