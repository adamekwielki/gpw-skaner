import pickle, numpy as np, pandas as pd
COST=0.004
raw=pickle.load(open("daily_raw.pkl","rb"))
def P(col): return pd.concat({t:d[col] for t,d in raw.items()},axis=1).sort_index()
Cr=P("Close"); A=P("Adj Close"); V=P("Volume"); f=A/Cr
A=A.where(A>0); f=A/Cr; O=P("Open")*f; H=P("High")*f; L=P("Low")*f; C=A
idx=Cr.index
traded=(V>0)&Cr.notna()
turn=(Cr*V).where(traded).rolling(20,min_periods=10).median()
elig=traded&(turn>=200_000)&(Cr>=1)
ret=C/C.shift(1)-1
# usuń ewidentne błędy danych
bad=(ret.abs()>0.6)
FW={}; BASE={}
for N in (1,3,5,10,20):
    x=(C.shift(-N)/O.shift(-1)-1-COST).clip(-0.7,1.5)
    x=x.where(O.shift(-1).notna()&~bad.shift(-1).fillna(False))
    FW[N]=x; BASE[N]=x.where(elig).mean(axis=1)
TR=(idx>="2013-01-01")&(idx<"2022-01-01"); TE=(idx>="2022-01-01")
def first(S,k): return S&~(S.shift(1).rolling(k,min_periods=1).max().fillna(0).astype(bool))
def ev(S,N,label,show=True):
    S=(S&elig).reindex_like(elig).fillna(False)
    x=FW[N].where(S); ex=x.sub(BASE[N],axis=0)
    out=[label,N]
    for m in (TR,TE):
        xs=x[m].stack().dropna(); es=ex[m].stack().dropna()
        dm=ex[m].mean(axis=1).dropna()
        t=dm.mean()/(dm.std()/np.sqrt(len(dm))) if len(dm)>5 else np.nan
        out+= [len(xs), round((xs>0).mean()*100,1), round(xs.mean()*100,2), round(es.mean()*100,2), round(t,1)]
    yr=ex[idx>="2013-01-01"].stack().dropna(); yy=yr.groupby(yr.index.get_level_values(0).year).mean()
    out.append(f"{(yy>0).sum()}/{len(yy)}")
    if show: print("{:<46s} N={:<2d} | TR n={:<6d} win={:<5} śr={:<6} przew={:<6} t={:<5} | TE n={:<6d} win={:<5} śr={:<6} przew={:<6} t={:<5} | lata+ {}".format(*out))
    return out
