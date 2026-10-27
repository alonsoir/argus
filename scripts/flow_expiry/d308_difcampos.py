#!/usr/bin/env python3
# DAY308 — campos que cambian entre dos salidas de paridad (d307_paridad_rasgos / d308_paridad_tolerancia), contados
# por campo y con un ejemplo de cada uno. SOLO MEDIDA. Uso: d308_difcampos.py A.tsv B.tsv
import sys, collections
a,b=sys.argv[1],sys.argv[2]
cnt=collections.Counter(); ev=0; tot=0; ej={}
for la,lb in zip(open(a),open(b)):
    if la.startswith('#'): continue
    tot+=1
    da=dict(x.split('=',1) for x in la.split('\t',1)[1].strip().rstrip(';').split(';') if x)
    db=dict(x.split('=',1) for x in lb.split('\t',1)[1].strip().rstrip(';').split(';') if x)
    d=[k for k in set(da)|set(db) if da.get(k)!=db.get(k)]
    if d: ev+=1
    for k in d:
        cnt[k]+=1
        ej.setdefault(k,(la.split('\t')[0],da.get(k),db.get(k)))
print(f"eventos={tot} con_diferencias={ev}")
for k,v in cnt.most_common(): print(f"  {k}: {v}  ej evento {ej[k][0]}: {ej[k][1]} -> {ej[k][2]}")
