from lib import *
pd.set_option("display.width",220)
print("=== A. PODATKOWA WYPRZEDAŻ → EFEKT STYCZNIA")
def sess(d): 
    i=idx.searchsorted(pd.Timestamp(d)); return i if i<len(idx) else None
rows=[]
for Y in range(2013,2026):
    i0=sess(f"{Y}-01-01"); 
    for buy,sell in (("12-01","01-15"),("12-15","01-15"),("12-20","01-31"),("12-27","01-15"),("12-27","01-31"),("11-15","12-15")):
        ib=sess(f"{Y}-{buy}"); isell=sess(f"{Y+1 if sell.startswith('01') else Y}-{sell}")
        if ib is None or isell is None or isell>=len(idx) or ib+1>=len(idx): continue
        ytd=(C.iloc[ib]/C.iloc[i0]-1).where(elig.iloc[ib])
        ytd=ytd.dropna()
        if len(ytd)<50: continue
        r=(C.iloc[isell]/O.iloc[ib+1]-1-COST).clip(-0.7,1.5).reindex(ytd.index).dropna(); ytd=ytd.reindex(r.index)
        q=ytd.rank(pct=True)
        rows.append(dict(rok=Y,okno=f"{buy}→{sell}",n=len(r),wszystkie=r.mean()*100,przegrani=r[q<=0.2].mean()*100,srodek=r[(q>0.4)&(q<=0.6)].mean()*100,
                         zwyciezcy=r[q>0.8].mean()*100,przegr_min30=r[ytd<-0.30].mean()*100,n_min30=int((ytd<-0.30).sum()),
                         win_przegr=(r[q<=0.2]>0).mean()*100))
T=pd.DataFrame(rows)
for ok,g in T.groupby("okno"):
    g=g.assign(roznica=g.przegrani-g.wszystkie)
    print(f"\nOkno {ok}: śr. wszystkie {g.wszystkie.mean():.2f}% | przegrani(20% najgorszych YTD) {g.przegrani.mean():.2f}% | zwycięzcy {g.zwyciezcy.mean():.2f}% | przegrani−wszystkie {g.roznica.mean():+.2f} pkt (lat na plus: {(g.roznica>0).sum()}/{len(g)}), przegrani>0 w {(g.przegrani>0).sum()}/{len(g)} lat, t={g.roznica.mean()/(g.roznica.std()/np.sqrt(len(g))):.1f}")
    if ok in ("12-27→01-15","12-15→01-15","11-15→12-15"): print(g[["rok","n","wszystkie","przegrani","zwyciezcy","roznica","win_przegr"]].round(1).to_string(index=False))

print("\n=== F. KALENDARZ: indeks równowagowy płynnych spółek (bez kosztów, %)")
m=ret.where(elig.shift(1).fillna(False)&~bad).mean(axis=1)
on=(O/C.shift(1)-1).where(elig.shift(1).fillna(False)).clip(-.3,.3).mean(axis=1); intr=(C/O-1).where(elig.shift(1).fillna(False)).clip(-.3,.3).mean(axis=1)
D=pd.DataFrame({"r":m,"noc":on,"sesja":intr}); D=D[D.index>="2013-01-01"]; D["dow"]=D.index.dayofweek; D["okres"]=np.where(D.index<"2022-01-01","TR","TE")
print((D.groupby(["okres","dow"])[["r","noc","sesja"]].mean()*100).round(3).unstack(0).to_string())
print("ogółem: całość/noc/sesja", (D[["r","noc","sesja"]].mean()*100).round(3).to_dict())
# przełom miesiąca
ym=D.index.to_period("M"); pos=D.groupby(ym).cumcount(); rev=D.groupby(ym).cumcount(ascending=False)
D["tom"]=np.where(rev<=1,"ostatnie 2",np.where(pos<=2,"pierwsze 3","reszta"))
print((D.groupby(["okres","tom"]).r.agg(["mean","count"]).assign(mean=lambda d:d["mean"]*100)).round(3).to_string())
# przed świętem
nxt=pd.Series(idx[1:].tolist()+[pd.NaT],index=idx); gap=(nxt-pd.Series(idx,index=idx)).dt.days
hol=((gap>3)|((gap>=2)&(pd.Series(idx.dayofweek,index=idx)<4))).reindex(D.index)
D["przed_sw"]=hol.values
print((D.groupby(["okres","przed_sw"]).r.agg(["mean","count"]).assign(mean=lambda d:d["mean"]*100)).round(3).to_string())

print("\n=== G/H. LUKI PANIKI NA OTWARCIU (cały rynek otwiera się nisko)")
elp=elig.shift(1).fillna(False)
gapm=(O/C.shift(1)-1).where(elp).clip(-.3,.3).mean(axis=1)
for thr in (-0.01,-0.015,-0.02):
    days=(gapm<=thr)&(gapm.index>="2013-01-01")
    for nm,x in (("kup otwarcie→zamknięcie tego dnia",(C/O-1-COST)),("kup otwarcie→zamknięcie +2 sesje",(C.shift(-2)/O-1-COST)),("kup otwarcie→zamknięcie +5 sesji",(C.shift(-5)/O-1-COST))):
        x=x.where(elp).clip(-.7,1.5); dm=x.mean(axis=1)
        a=dm[days&TR]; b=dm[days&TE]; base=dm[dm.index>="2013-01-01"].mean()
        print(f"luka rynku ≤ {thr*100:.1f}%: {nm:36s} TR dni={len(a):3d} śr={a.mean()*100:+.2f}% win={(a>0).mean()*100:.0f}% | TE dni={len(b):3d} śr={b.mean()*100:+.2f}% win={(b>0).mean()*100:.0f}% | zwykły dzień {base*100:+.2f}%")
# najmocniej przecenione na otwarciu w taki dzień
days=(gapm<=-0.015)
g1=(O/C.shift(1)-1).where(elp)
for lab,mask in (("spółki z luką ≤ −4%",g1<=-0.04),("spółki z luką −1..−4%",(g1>-0.04)&(g1<=-0.01)),("spółki bez luki (> −1%)",g1>-0.01)):
    for nm,x in (("→zamknięcie",C/O-1-COST),("→+2 sesje",C.shift(-2)/O-1-COST)):
        x=x.where(mask&elp).clip(-.7,1.5)[days.values]
        a=x[x.index<"2022-01-01"].stack().dropna(); b=x[x.index>="2022-01-01"].stack().dropna()
        print(f"  w dniu luki rynku ≤ −1,5%: {lab:24s}{nm:12s} TR n={len(a):5d} śr={a.mean()*100:+.2f}% win={(a>0).mean()*100:.0f}% | TE n={len(b):5d} śr={b.mean()*100:+.2f}% win={(b>0).mean()*100:.0f}%")
print("\n=== G2. UWAGA TŁUMU: dzień po wystrzale (+8%, wolumen 2,5x)")
att=(ret>=0.08)&(V>=2.5*V.where(traded).rolling(20).mean().shift(1))&elig
for nm,x in (("noc (zamknięcie→otwarcie)",O.shift(-1)/C-1),("następna sesja (otwarcie→zamknięcie)",C.shift(-1)/O.shift(-1)-1)):
    x=x.where(att).clip(-.5,.5); a=x[TR].stack().dropna(); b=x[TE].stack().dropna()
    print(f"  {nm:38s} TR n={len(a)} śr={a.mean()*100:+.2f}% | TE n={len(b)} śr={b.mean()*100:+.2f}%  (bez kosztów)")
