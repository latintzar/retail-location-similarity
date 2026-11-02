"""Recompute the three retained London presets from the checksummed original matrix.

Run manually: python tools/precompute_london.py --matrix data/london-res10.parquet
The calculation reads all 131,596 × 1,956 values twice; it is not a server startup task.
"""
import json,time,warnings,argparse,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import duckdb,h3,numpy as np
from _scoring import compute_diem
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--matrix",type=Path,default=ROOT/"data/london-res10.parquet")
parser.add_argument("--output",type=Path,default=ROOT/"data/london/presets-recomputed.json")
args=parser.parse_args()
MATRIX=args.matrix.resolve()
manifest=json.loads((ROOT/"data/london/manifest.json").read_text())
with MATRIX.open("rb") as source:
 if hashlib.file_digest(source,"sha256").hexdigest()!=manifest["sha256"]:raise ValueError("London matrix checksum mismatch")
places=[('Covent Garden',51.5117,-.124),('Shoreditch',51.5255,-.078),('Soho',51.5136,-.135)]
refs={h3.latlng_to_cell(a,b,10):None for _,a,b in places}; excluded={h:set(h3.grid_disk(h,15)) for h in refs}
db=duckdb.connect();db.execute("SET threads=2");db.execute("SET memory_limit='256MB'");db.execute("SET max_temp_directory_size='512MB'");path=str(MATRIX);schema=db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[path]).fetchall();numeric=('TINYINT','SMALLINT','INTEGER','BIGINT','HUGEINT','UTINYINT','USMALLINT','UINTEGER','UBIGINT','FLOAT','DOUBLE','DECIMAL');cols=[r[0] for r in schema if r[0]!='h3_index' and r[1].startswith(numeric)];q='SELECT h3_index,'+','.join('"'+c.replace('"','""')+'"' for c in cols)+' FROM read_parquet(?)';mins=np.full(len(cols),np.inf);maxs=np.full(len(cols),-np.inf);t=time.monotonic();cur=db.execute(q,[path])
with warnings.catch_warnings():
 warnings.filterwarnings('ignore',message='All-NaN slice encountered')
 while rows:=cur.fetchmany(512):
  x=np.asarray([r[1:] for r in rows],dtype=np.float64);mins=np.fmin(mins,np.nanmin(x,axis=0));maxs=np.fmax(maxs,np.nanmax(x,axis=0))
  for i,r in enumerate(rows):
   if r[0] in refs:refs[r[0]]=x[i].copy()
assert all(v is not None for v in refs.values());mins[np.isinf(mins)]=np.nan;maxs[np.isinf(maxs)]=np.nan
results={h:[] for h in refs};totals={h:0.0 for h in refs};count=0;cur=db.execute(q,[path])
while rows:=cur.fetchmany(512):
 x=np.asarray([r[1:] for r in rows],dtype=np.float64);count+=len(rows)
 for h,ref in refs.items():
  scores=compute_diem(ref,x,mins,maxs);totals[h]+=float(scores.sum());results[h].extend((r[0],float(s)) for r,s in zip(rows,scores) if r[0] not in excluded[h])
output={}
for name,lat,lng in places:
 h=h3.latlng_to_cell(lat,lng,10);top=sorted(results[h],key=lambda a:a[1],reverse=True)[:100];vals=np.array([x[1] for x in top]);rank=np.empty(len(vals));order=np.argsort(vals,kind='stable');i=0
 while i<len(order):
  j=i+1
  while j<len(order) and vals[order[j]]==vals[order[i]]:j+=1
  rank[order[i:j]]=(i+1+j)/(2*len(vals));i=j
 matches=[{'hex':k,'similarity':s,'percentile':float(r*100),'value':float(r**2.5*100)} for (k,s),r in zip(top,rank)];a,b=h3.cell_to_latlng(h)
 output[h]={'reference':{'hex':h,'lat':a,'lng':b,'description':None,'starter_pack':None,'top_scores':[]},'similar_hexes':matches,'stats':{'total_hexes':count,'feature_dimensions':len(cols),'top_k':100,'mean_similarity':totals[h]/count,'max_similarity':top[0][1],'min_similarity':top[-1][1]},'cache_provenance':{'matrix_sha256':'3e56da16150bc01b7b8a9e84d7d68c85eb76210fc0a0d2916801aafd1dabab5f','source':'historic Leo calibrated distance','name':name}}
args.output.write_text(json.dumps(output,allow_nan=False));print(json.dumps({'seconds':round(time.monotonic()-t,2),'rows':count,'features':len(cols),'top':{v['cache_provenance']['name']:v['similar_hexes'][0] for v in output.values()}}))
