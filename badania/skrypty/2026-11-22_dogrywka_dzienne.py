# Hipoteza 2 – przybliżenie na danych dziennych 2012–2026: dzień ≥ +X% (zamknięcie do zamknięcia; na godzinowych
# zamknięcie ≈ cena z 16:00, śr. różnica +0,02%) → kupno na zamknięciu, sprzedaż na otwarciu t+1 / zamknięciu t+1 / t+2.
# Trening 2013–2021, test 2022–2026. Koszt 0,4%. Przewaga = wynik − średnia płynnych spółek kupionych tego samego dnia.
import pickle, sys, numpy as np, pandas as pd
COST=0.004
data=pickle.load(open(sys.argv[1],"rb"))
rows=[]
for tic,D in data["d"].items():
    D=D[D.Volume>0].copy()
    D["pc"]=D.Close.shift(1); D["turn"]=(D.Close*D.Volume).rolling(20).median().shift(1)
    D["vavg"]=D.Volume.rolling(20).mean().shift(1)
    D["nO"]=D.Open.shift(-1); D["nC"]=D.Close.shift(-1); D["n2C"]=D.Close.shift(-2); D["tic"]=tic
    rows.append(D.iloc[21:-2])
A=pd.concat(rows); A.index.name="date"; A=A.reset_index()
A=A[(A.turn>=200_000)&(A.Close>=1)&(A.date>="2013-01-01")]
A["g"]=A.Close/A.pc-1; A["vr"]=A.Volume/A.vavg
for k,col in (("O","nO"),("C","nC"),("2C","n2C")): A["r"+k]=A[col]/A.Close-1-COST; A["m"+k]=A.groupby("date")["r"+k].transform("mean")
A["okres"]=np.where(A.date<"2022-01-01","trening","test"); A["rok"]=A.date.dt.year
# Odrzuć oczywiste błędy danych (ruch nocny > 40%)
A=A[(A.rO.abs()<0.4)&(A.g<1.0)]
pd.set_option("display.width",250)
print("Losowe:",A.groupby("okres")[["rO","rC","r2C"]].mean().mul(100).round(2).to_dict())
out=[]
for lab,S in {"g>=8%":A[A.g>=0.08],"g>=8% v>=2.5":A[(A.g>=0.08)&(A.vr>=2.5)],"g>=10%":A[A.g>=0.10],"g>=15%":A[A.g>=0.15],"g 5-8%":A[(A.g>=0.05)&(A.g<0.08)]}.items():
    for okr,s in S.groupby("okres"):
        d=dict(war=lab,okres=okr,n=len(s))
        for k in ("O","C","2C"): d["sr_"+k]=s["r"+k].mean()*100; d["win_"+k]=(s["r"+k]>0).mean()*100; d["prz_"+k]=(s["r"+k]-s["m"+k]).mean()*100
        out.append(d)
print(pd.DataFrame(out).round(2).to_string(index=False))
S=A[A.g>=0.08]
y=S.groupby("rok").apply(lambda s:pd.Series(dict(n=len(s),sr_O=s.rO.mean()*100,prz_O=(s.rO-s.mO).mean()*100,sr_2C=s.r2C.mean()*100,prz_2C=(s.r2C-s.m2C).mean()*100))).round(2)
print(y.to_string()); print("lata z przewagą>0 (otwarcie):",(y.prz_O>0).sum(),"/",len(y),"  (t+2):",(y.prz_2C>0).sum(),"/",len(y))
print("lata ze średnią>0 po koszcie (otwarcie):",(y.sr_O>0).sum(),"/",len(y))
