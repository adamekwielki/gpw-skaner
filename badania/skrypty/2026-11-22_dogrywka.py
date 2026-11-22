# Hipoteza 2 – „dogrywka”: spółka ≥ +X% o 16:00 (zamknięcie świecy 15:00) → kupno na fixingu zamknięcia,
# sprzedaż następnego dnia (otwarcie / 10:00 / zamknięcie). Koszt 0,4%. Trening < 2025-06-01, test ≥ 2025-06-01.
import pickle, sys, numpy as np, pandas as pd
COST=0.004; SPLIT=pd.Timestamp("2025-06-01")
data=pickle.load(open(sys.argv[1],"rb"))
rows=[]
for tic,h in data["h"].items():
    h=h.copy(); h.index=h.index.tz_convert("Europe/Warsaw").tz_localize(None)
    day=h.index.normalize(); hr=h.index.hour
    g=h.groupby(day)
    D=pd.DataFrame(dict(Open=g.Open.first(),High=g.High.max(),Low=g.Low.min(),Close=g.Close.last(),Volume=g.Volume.sum()))
    b15=h[hr==15]; b15.index=b15.index.normalize()
    b9=h[hr==9]; b9.index=b9.index.normalize()
    hist=h[hr<=15]; vol16=hist.groupby(hist.index.normalize()).Volume.sum()
    hi16=hist.groupby(hist.index.normalize()).High.max()
    D["p16"]=b15.Close.reindex(D.index); D["p10"]=b9.Close.reindex(D.index)
    D["vol16"]=vol16.reindex(D.index); D["hi16"]=hi16.reindex(D.index)
    D["pc"]=D.Close.shift(1)
    D["turn"]=(D.Close*D.Volume).rolling(20).median().shift(1)
    D["vavg"]=D.Volume.rolling(20).mean().shift(1)
    D["nO"]=D.Open.shift(-1); D["n10"]=D.p10.shift(-1); D["nC"]=D.Close.shift(-1); D["n2C"]=D.Close.shift(-2)
    D["nH"]=D.High.shift(-1)
    D["tic"]=tic
    rows.append(D.iloc[21:-2])
A=pd.concat(rows); A.index.name="date"; A=A.reset_index()
A=A[(A.turn>=200_000)&(A.Close>=1)&A.p16.notna()&A.nO.notna()&A.n10.notna()]
A["g16"]=A.p16/A.pc-1; A["gC"]=A.Close/A.pc-1; A["v16r"]=A.vol16/A.vavg
for k,col in (("O","nO"),("10","n10"),("C","nC"),("2C","n2C")): A["r"+k]=A[col]/A.Close-1-COST
A["okres"]=np.where(A.date<SPLIT,"trening","test"); A["kw"]=A.date.dt.to_period("Q").astype(str)
# średnia wszystkich płynnych spółek kupionych tego samego dnia (losowe wejście, to samo wyjście)
for k in ("O","10","C","2C"): A["m"+k]=A.groupby("date")["r"+k].transform("mean")
pd.set_option("display.width",250)
print("Spółek:",A.tic.nunique(),"dni:",A.date.nunique(),A.date.min().date(),A.date.max().date())
print("\nLOSOWE wejście na fixingu (wszystkie płynne spółko-dni):")
print(A.groupby("okres")[["rO","r10","rC","r2C"]].agg(lambda x:x.mean()*100).round(2))
def stat(S,lab):
    out=[]
    for okr in ("trening","test"):
        s=S[S.okres==okr]
        d=dict(war=lab,okres=okr,n=len(s))
        for k in ("O","10","C","2C"):
            d["sr_"+k]=s["r"+k].mean()*100; d["win_"+k]=(s["r"+k]>0).mean()*100; d["prz_"+k]=(s["r"+k]-s["m"+k]).mean()*100
        out.append(d)
    return out
res=[]
V={}
for X in (0.05,0.08,0.10,0.15):
    V[f"g16>={X:.0%}"]=A[A.g16>=X]
    V[f"g16>={X:.0%} v16>=2.5"]=A[(A.g16>=X)&(A.v16r>=2.5)]
V["g16 5-8%"]=A[(A.g16>=0.05)&(A.g16<0.08)]
V["g16>=8% & p16>=0.97*hi16"]=A[(A.g16>=0.08)&(A.p16>=0.97*A.hi16)]
V["g16>=8% & p16<0.97*hi16"]=A[(A.g16>=0.08)&(A.p16<0.97*A.hi16)]
V["KONTROLA g16<=-8%"]=A[A.g16<=-0.08]
for lab,S in V.items(): res+=stat(S,lab)
R=pd.DataFrame(res).round(2)
print("\nSYGNAŁY (sr = średni wynik po koszcie 0,4%, prz = przewaga nad losowym wejściem tego samego dnia):")
print(R[["war","okres","n","sr_O","win_O","prz_O","sr_10","win_10","prz_10","sr_C","win_C","prz_C","sr_2C","prz_2C"]].to_string(index=False))
S=V["g16>=8%"]
print("\nPer kwartał (g16>=8%, wyjście na otwarciu t+1):")
q=S.groupby("kw").apply(lambda s:pd.Series(dict(n=len(s),sr=s.rO.mean()*100,prz=(s.rO-s.mO).mean()*100,sr10=s.r10.mean()*100,prz10=(s.r10-s.m10).mean()*100))).round(2)
print(q.to_string()); print("kwartały z przewagą>0 (otwarcie):",(q.prz>0).sum(),"/",len(q)," (10:00):",(q.prz10>0).sum(),"/",len(q))
print("\nOgony (g16>=8%, otwarcie): % strat > 3%:",round((S.rO<-0.03).mean()*100,1),"najgorsza:",round(S.rO.min()*100,1),"mediana:",round(S.rO.median()*100,2))
print("Ile dodatkowo do fixingu (zamknięcie vs 16:00) średnio:",round(((S.Close/S.p16-1)*100).mean(),2),"%")
print("Udział największej transakcji w sumie:",round(S.rO.max()/S.rO.sum()*100,1),"%")
print("\nNajwiększe pojedyncze wyniki:");print(S.sort_values("rO")[["date","tic","g16","gC","rO","r10"]].iloc[list(range(3))+list(range(-3,0))].round(3).to_string(index=False))
A.to_pickle(sys.argv[1].replace(".pkl","_A.pkl"))
