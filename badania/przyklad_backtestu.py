import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0,".")
import features as F
COST=0.004
data=pickle.load(open("hourly.pkl","rb"))
Ds={}
for grp in ("wse","nc"):
    for tic,h in data[grp].items():
        D=F.daily_from_hourly(h)
        if len(D)>=200: Ds[(grp,tic)]=D
# indeks równowagowy (wse) do paniki
rets=pd.concat([D["Close"].pct_change().rename(k[1]) for k,D in Ds.items() if k[0]=="wse" and (D.Close*D.Volume).tail(250).median()>=200_000],axis=1)
idx=(1+rets.mean(axis=1).fillna(0)).cumprod(); idx_r2=F.rsi(idx,2)
rows=[]
for (grp,tic),D in Ds.items():
    o,hi,lo,c,v=(D[x].values for x in ("Open","High","Low","Close","Volume")); n=len(c); dates=D.index
    r2=F.rsi(D["Close"],2).values
    s100=D.Close.rolling(100).mean().values; s200=D.Close.rolling(200).mean().values
    trend=np.where(np.isfinite(s200),c>s200,c>s100)
    turn=pd.Series(c*v).rolling(20).median().values
    vmed=pd.Series(v).rolling(20).median().shift(1).values; vavg=pd.Series(v).rolling(20).mean().shift(1).values
    hh=pd.Series(c).rolling(120).max().shift(1).values
    down=pd.Series(np.r_[False,c[1:]<c[:-1]]).rolling(5).sum().values
    ret=np.r_[np.nan,c[1:]/c[:-1]-1]; ret5=pd.Series(c).pct_change(5).values
    ir2=idx_r2.reindex(dates).values
    last={}
    def ev(rule,j,e,base_exit):
        # j = dzień wejścia (indeks), e = cena wejścia
        if j+20>n-1: return
        res=dict(regula=rule,date=dates[j],rynek=grp)
        bx,bd=base_exit; res["obecne"]=bx/e-1-COST; res["d_obecne"]=bd-j+1
        for N in (10,15,20): res[f"trzym{N}"]=c[j+N-1]/e-1-COST
        for cap in (10,20):
            tp=e*1.03; out=None
            for d in range(j,j+cap):
                if d>j and o[d]>=tp: out=(o[d],d);break
                if hi[d]>=tp and (d>j or rule!="WYSTRZAL"): out=(tp,d);break
            if out is None: out=(c[j+cap-1],j+cap-1)
            res[f"tp3_{cap}"]=out[0]/e-1-COST; res[f"d_tp3_{cap}"]=out[1]-j+1
        rows.append(res)
    def rsi2exit(t,maxd=7):
        for d in range(t+1,min(t+maxd,n-1)+1):
            if r2[d]>70 or d==t+maxd: return (c[d],d)
    for t in range(130,n-21):
        if not(turn[t]>=200_000 and c[t]>=1): continue
        sig=[]
        if np.isfinite(ir2[t]) and ir2[t]<10 and ret5[t]<=-0.10: sig.append(("PANIKA",lambda t:rsi2exit(t)))
        if r2[t]<5 and trend[t]: sig.append(("RSI2",rsi2exit))
        if down[t]>=5 and np.isfinite(s100[t]) and c[t]>s100[t]: sig.append(("5SPADKOW",rsi2exit))
        if np.isfinite(hh[t]) and c[t]>hh[t] and vmed[t]>0 and v[t]>=1.5*vmed[t] and trend[t]:
            sig.append(("WYBICIE",lambda t:(c[t+7],t+7)))
        for name,fn in sig:
            if t<=last.get(name,-1): continue
            bx=fn(t)
            if bx: ev(name,t+1,o[t+1],bx); last[name]=t+5
        if ret[t]>=0.08 and vavg[t]>0 and v[t]>=2.5*vavg[t] and t>last.get("WYSTRZAL",-1):
            L=c[t]-0.618*(c[t]-c[t-1])
            for j in range(t+1,min(t+16,n-21)):
                if lo[j]<=L:
                    e=min(o[j],L); bx=None
                    for d in range(j,j+6):
                        if d>j and hi[d]>=hi[t]: bx=(max(o[d],hi[t]),d);break
                        if d==j+5: bx=(c[d],d);break
                    ev("WYSTRZAL",j,e,bx); last["WYSTRZAL"]=j+5; break
T=pd.DataFrame(rows); T.to_pickle("exits.pkl")
cols=["obecne","trzym10","trzym15","trzym20","tp3_10","tp3_20"]
out=[]
for reg,g in list(T.groupby("regula"))+[("RAZEM",T)]:
    for col in cols:
        x=g[col]; d={"obecne":g.d_obecne.mean(),"trzym10":10,"trzym15":15,"trzym20":20,"tp3_10":g.d_tp3_10.mean(),"tp3_20":g.d_tp3_20.mean()}[col]
        out.append(dict(regula=reg,n=len(g),wyjscie=col,win=(x>0).mean()*100,sr=x.mean()*100,med=x.median()*100,
            sr_strata=x[x<=0].mean()*100,najg=x.min()*100,dni=d,na_dzien=x.mean()*100/d))
pd.set_option("display.width",200)
print(pd.DataFrame(out).round(2).to_string(index=False))
