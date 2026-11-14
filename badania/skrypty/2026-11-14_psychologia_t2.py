from lib import *
def rsi(c,n=2):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn.replace(0,1e-12))
hi=C.rolling(250,min_periods=200).max().shift(1); lo=C.rolling(250,min_periods=200).min().shift(1); r=C/hi
r2=rsi(C,2)
print("=== B2. KOTWICA 52t – warianty pod horyzont 1–2 tyg.")
for N in (5,10,20):
    ev(first(C>hi,20),N,"nowy szczyt 52t")
    ev(first((C>hi)&(V>=1.5*V.where(traded).rolling(20).median().shift(1)),20),N,"nowy szczyt 52t + wolumen 1.5x")
    ev(first((r>=0.90)&(r2<10),5),N,"do 10% od szczytu 52t + RSI2<10 (cofnięcie)")
    ev(first((r>=0.95)&(r2<5),5),N,"do 5% od szczytu 52t + RSI2<5")
    ev(first((r<0.70)&(r2<5),5),N,"KONTROLA: >30% pod szczytem + RSI2<5")
    ev(first(C<lo,20),N,"nowy dołek 52t")
    ev(first((C<lo)&(r2<5),20),N,"nowy dołek 52t + RSI2<5 (łapanie noża)")
print("\n=== C. OKRĄGŁE CENY (ceny nieskorygowane)")
step=10.0**np.floor(np.log10(Cr.clip(lower=0.5)))
def lvl_cross(off):
    k=np.floor(Cr/step-off); kp=np.floor(Cr.shift(1)/step-off)
    up=(k>kp)&(Cr.shift(1)>0)&(step==step.shift(1)); dn=(k<kp)&(step==step.shift(1))
    dist=((np.floor(Cr/step-off)+1+off)*step)/Cr-1   # odległość do następnego poziomu w górę
    return up,dn,dist
for name,off in (("OKRĄGŁY",0.0),("placebo .37",0.37),("placebo .63",0.63)):
    up,dn,dist=lvl_cross(off)
    for N in (5,10):
        ev(first(up,5),N,f"{name}: przebicie poziomu w górę")
        ev(first(dn,5),N,f"{name}: przebicie poziomu w dół")
    ev(first((dist<0.015)&(C/C.shift(10)-1>0.05),5),5,f"{name}: tuż pod poziomem (do 1,5%) po wzroście")
big=(Cr>=9.5)
for name,off in (("OKRĄGŁY ≥10 zł",0.0),("placebo .37 ≥10 zł",0.37)):
    up,dn,dist=lvl_cross(off); ev(first(up&big,5),10,f"{name}: w górę"); ev(first(dn&big,5),10,f"{name}: w dół")
