import pandas as pd, numpy as np, json, sys
from sklearn.metrics import average_precision_score, roc_auc_score
D='data/scored/'
t=pd.read_parquet(D+'transactions.parquet')
a=pd.read_parquet(D+'alerts.parquet')
acc=pd.read_parquet(D+'accounts_summary.parquet').set_index('account_id')
lp=pd.read_parquet(D+'laundering_patterns.parquet')
me=pd.read_parquet(D+'model_evaluation.parquet')
t=t.reset_index(drop=True)
ts=t['timestamp'].values.astype('datetime64[m]')
# account -> row indices
long=pd.concat([pd.DataFrame({'acct':t.from_account,'i':t.index}),pd.DataFrame({'acct':t.to_account,'i':t.index})])
idx=long.groupby('acct')['i'].apply(lambda s: np.unique(s.values)).to_dict()
# alert counts per account
ac=pd.concat([a.subject_account_id,a.counterparty_account_id]).value_counts().to_dict()
pat_tx=lp.groupby('pattern_id')['transaction_id'].apply(list).to_dict()
txrow=pd.Series(t.index,index=t.transaction_id).to_dict()

a=a.sort_values('laundering_probability',ascending=False).reset_index(drop=True)
sel=list(a.index[:36])
for typ,g in a.groupby('primary_typology'):
    if not any(a.loc[i,'primary_typology']==typ for i in sel): sel.append(g.index[0])
# a couple of medium-band alerts for contrast
med=a[a.risk_band=='Medium'].index[:4].tolist(); sel+= [i for i in med if i not in sel]
sel=sorted(set(sel))
H=np.timedelta64(72,'h')

def rows_near(acct,center,cap,exclude):
    r=idx.get(acct); 
    if r is None: return []
    r=r[(ts[r]>=center-H)&(ts[r]<=center+H)]
    r=[int(x) for x in r if int(x) not in exclude]
    r.sort(key=lambda x: abs((ts[x]-center).astype(int)))
    return r[:cap]

def edge(i,hop,inpat,seed=False):
    r=t.iloc[i]
    return dict(id=int(r.transaction_id),s=r.from_account,d=r.to_account,amt=round(float(r.amount_usd),2),
                ts=str(ts[i])[:16],fmt=r.payment_format,p=round(float(r.laundering_probability),3),
                band=r.risk_band,gt=int(r.is_laundering_ground_truth),hop=hop,pat=int(inpat),seed=int(seed))

def acct_node(aid,hop):
    n=dict(id=aid,hop=hop,alerts=int(ac.get(aid,0)))
    if aid in acc.index:
        s=acc.loc[aid]
        n.update(bank=str(s.bank_id),tier=str(s.risk_tier),vin=round(float(s.volume_24h_inbound),2),vout=round(float(s.volume_24h_outbound),2),
                 ntx=int(s.total_txn_count),ncp=int(s.counterparty_count),maxp=round(float(s.max_risk_score),3),nhigh=int(s.high_risk_txn_count))
    return n

alerts=[]
for i in sel:
    al=a.loc[i]; center=np.datetime64(al.alerted_ts,'m')
    subj,cp=al.subject_account_id,al.counterparty_account_id
    seedrow=txrow[int(al.transaction_id)]
    used={seedrow}; edges=[edge(seedrow,0,False,True)]
    for s_ in (subj,cp):
        for r in rows_near(s_,center,100,used): used.add(r); edges.append(edge(r,1,False))
    hop1=pd.Series([e['s'] for e in edges]+[e['d'] for e in edges]).value_counts()
    hop1=[x for x in hop1.index if x not in (subj,cp)][:40]
    for h in hop1:
        for r in rows_near(h,center,6,used): used.add(r); edges.append(edge(r,2,False))
    pid=al.pattern_id if isinstance(al.pattern_id,str) else None
    pat_ids=set()
    if pid:
        for tx in pat_tx.get(pid,[]):
            r=txrow.get(int(tx)); 
            if r is None: continue
            pat_ids.add(int(tx))
            if r in used:
                for e in edges:
                    if e['id']==int(tx): e['pat']=1
            else:
                used.add(r); edges.append(edge(r,3,True))
    nodes={}
    for e in edges:
        for k,who in (('s',e['s']),('d',e['d'])):
            hop=0 if who in (subj,cp) else (1 if e['hop']<=1 else (2 if e['hop']==2 else 3))
            if who not in nodes or hop<nodes[who]['hop']: nodes[who]=acct_node(who,hop)
    alerts.append(dict(id=al.alert_id,tx=int(al.transaction_id),subj=subj,cp=cp,status=al.status,prio=al.priority,
        typ=al.primary_typology,p=round(float(al.laundering_probability),3),band=al.risk_band,amt=round(float(al.amount_usd),2),
        fmt=al.payment_format,ts=str(center)[:16],model=al.model_version.split('.')[-1][:8],
        truth=dict(pid=pid,typ=al.true_typology if isinstance(al.true_typology,str) else None,gt=int(al.is_laundering_ground_truth),n=len(pat_ids)),
        nodes=list(nodes.values()),edges=edges))
    print(al.alert_id, len(nodes), len(edges), file=sys.stderr)

# evaluation
y=t.is_laundering_ground_truth.values; p=t.laundering_probability.values
order=np.argsort(-p); cum=np.cumsum(y[order])
ks=[10,25,50,100,200,500,1000,2000,5000,10000]
pk=[dict(k=k,prec=round(float(cum[k-1]/k),3),hits=int(cum[k-1])) for k in ks]
bands=t.groupby('risk_band').is_laundering_ground_truth.agg(['count','sum']).reindex(['High','Medium','Low'])
bands=[dict(band=b,n=int(r['count']),pos=int(r['sum'])) for b,r in bands.iterrows()]
bins=np.linspace(0,1,21)
h1,_=np.histogram(p[y==1],bins); h0,_=np.histogram(p[y==0],bins)
hist=[dict(lo=round(float(bins[i]),2),pos=int(h1[i]),neg=int(h0[i])) for i in range(20)]
ct=pd.crosstab(a[a.is_laundering_ground_truth==1].primary_typology,a[a.is_laundering_ground_truth==1].true_typology)
conf=dict(rows=list(ct.index),cols=list(ct.columns),m=ct.values.tolist())
prio=a.groupby(['priority','risk_band']).size().reset_index().rename(columns={0:'n'}).to_dict('records')
evald=dict(n=int(len(t)),pos=int(y.sum()),prauc=round(float(average_precision_score(y,p)),3),rocauc=round(float(roc_auc_score(y,p)),3),
    val=dict(prauc=0.564,f1=0.584,rocauc=0.987,epoch=33,epochs=39),thr=dict(high=0.623,medium=0.351),
    pk=pk,bands=bands,hist=hist,conf=conf,prio=prio,nalerts=int(len(a)),
    window=[str(ts.min())[:16],str(ts.max())[:16]],
    me=me.to_dict('records'),model='aml_gnn_hi_small v1 · ri.models.main.model-version.5f131650')
out=dict(alerts=alerts,eval=evald)
s=json.dumps(out,separators=(',',':'),default=str)
open('/private/tmp/claude-501/-Users-saimeda-Desktop-Palantir-foundry-aml/2989cd20-c26e-4ef9-b9f2-49f5e551515a/scratchpad/viz/data.json','w').write(s)
print('alerts',len(alerts),'bytes',len(s), file=sys.stderr)
print(json.dumps(evald)[:1500])
