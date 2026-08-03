import sys, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1])
print("rows", t.num_rows, "| cols", t.num_columns)
assert t.num_columns == 34, "no son 34 columnas"
assert str(t.schema.field("rule_level").type) == "int32", "rule_level no es int32"
assert str(t.schema.field("hmac_row").type) == "string", "falta hmac_row"
d = t.to_pydict()
found = 0
for i, rid in enumerate(d["rule_id"]):
    if rid == "5403":                       # sudo -> root (la espina privesc)
        found += 1
        assert d["rule_level"][i] == 4, f"rule_level != 4 en fila {i}"
        assert "T1548.003" in d["mitre_ids"][i], f"T1548.003 ausente en fila {i}"
print("filas rule_id=5403 verificadas:", found)
print("OK" if (t.num_rows == 533 and found > 0) else "REVISAR")
