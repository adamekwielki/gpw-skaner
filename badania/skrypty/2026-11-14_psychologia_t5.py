from lib import *
def rsi(c,n=2):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn.replace(0,1e-12))
r2=rsi(C,2); s200=C.rolling(200).mean(); s100=C.rolling(100).mean()
hi=C.rolling(250,min_periods=200).max().shift(1); r=C/hi
vavg=V.where(traded).rolling(20).mean().shift(1)
spike=(ret>=0.08)&(V>=2.5*vavg)&elig&~bad
Oa,Ha,La,Ca=O.values,H.values,L.values,C.values; n=len(idx); yrs=idx.year.values
def sim_tp(i,j,e,tp,cap,same_day):
    for d in range(j,min(j+cap,n)):
        if np.isnan(Ca[d,i]): continue
        if d>j and Oa[d,i]>=e*tp: return Oa[d,i]/e-1-COST
        if Ha[d,i]>=e*tp and (d>j or same_day): return tp-1-COST
    d=min(j+cap-1,n-1)
    while d>j and np.isnan(Ca[d,i]): d-=1
    return Ca[d,i]/e-1-COST
print("=== WYSTRZAŁ: poziom limitu vs wypełnienie (ważność 15 sesji, TP +2% / 10 sesji)")
ti,ii=np.where(spike.values)
for k in (0.236,0.382,0.5,0.618):
  for tp in (1.02,1.03):
    res=[]; nsig=0; last={}
    for t,i in zip(ti,ii):
        if idx[t]<pd.Timestamp("2013-01-01") or t+26>=n or t<=last.get(i,-1): continue
        nsig+=1; Lm=Ca[t,i]-k*(Ca[t,i]-Ca[t-1,i])
        for j in range(t+1,t+16):
            if La[j,i]<=Lm:
                e=min(Oa[j,i],Lm)
                if not e>0: break
                res.append((yrs[j],sim_tp(i,j,e,tp,10,False))); last[i]=j+5; break
    R=pd.DataFrame(res,columns=["y","r"]); R["r"]=R.r.clip(-.7,1.5)
    a=R[R.y<2022].r; b=R[R.y>=2022].r; yy=R.groupby("y").r.mean()
    print(f"limit {k:.3f} TP{int((tp-1)*100)}%: sygnałów {nsig}, wypełnione {len(R)/nsig*100:.0f}% | TR n={len(a)} win={(a>0).mean()*100:.0f}% śr={a.mean()*100:+.2f}% | TE n={len(b)} win={(b>0).mean()*100:.0f}% śr={b.mean()*100:+.2f}% | lata+ {(yy>0).sum()}/{len(yy)} | strata>10%: {(R.r<-0.1).mean()*100:.1f}% najg {R.r.min()*100:.0f}%")
print("\n=== REGUŁY „W DOŁKU” z wyjściem na +X% (wejście na otwarciu t+1, TP możliwy od dnia wejścia)")
dn5=((ret<0).astype(float).rolling(5).sum()==5)
new52=(C>hi); rec52=new52.rolling(10).max().shift(1).fillna(0).astype(bool)
sigs={"RSI2<5 nad SMA200, ≥10% pod szczytem 52t":first((r2<5)&(C>s200)&(r<0.90),5),
      "RSI2<5 nad SMA200 (wszystkie)":first((r2<5)&(C>s200),5),
      "5 spadków nad SMA100":first(dn5&(C>s100),5),
      "RSI2<10 nad SMA200, spadek ≥8% w 5 sesji":first((r2<10)&(C>s200)&(C/C.shift(5)-1<=-0.08),5),
      "cofnięcie po świeżym szczycie 52t (RSI2<15, do 7% od szczytu)":first(rec52&(r2<15)&(r>=0.93),5),
      "LOSOWO (co 7. sesja)":elig&pd.DataFrame(np.tile((np.arange(n)%7==0)[:,None],(1,C.shape[1])),index=idx,columns=C.columns)}
for name,S in sigs.items():
    S=(S&elig).values; ti2,ii2=np.where(S)
    for tp,cap in ((1.02,10),(1.03,10),(1.05,10)):
        res=[]
        for t,i in zip(ti2,ii2):
            if idx[t]<pd.Timestamp("2013-01-01") or t+12>=n: continue
            e=Oa[t+1,i]
            if not e>0 or bad.values[t+1,i]: continue
            res.append((yrs[t],sim_tp(i,t+1,e,tp,cap,True)))
        R=pd.DataFrame(res,columns=["y","r"]); R["r"]=R.r.clip(-.7,1.5)
        a=R[R.y<2022].r; b=R[R.y>=2022].r; yy=R.groupby("y").r.mean()
        print(f"{name:62s} TP{int(round((tp-1)*100))}%/{cap}: TR n={len(a):5d} win={(a>0).mean()*100:.0f}% śr={a.mean()*100:+.2f}% | TE n={len(b):5d} win={(b>0).mean()*100:.0f}% śr={b.mean()*100:+.2f}% | lata+ {(yy>0).sum()}/{len(yy)} | strata>10% {(R.r<-0.1).mean()*100:.1f}%")
