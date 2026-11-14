from lib import *
import lib
def rsi(c,n=2):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn.replace(0,1e-12))
r2=rsi(C,2); s200=C.rolling(200).mean(); s100=C.rolling(100).mean()
hi=C.rolling(250,min_periods=200).max().shift(1); lo=C.rolling(250,min_periods=200).min().shift(1); r=C/hi
hi120=C.rolling(120).max().shift(1); vmed=V.where(traded).rolling(20).median().shift(1)
# wyjście RSI2>70 lub 7 sesji, wejście: otwarcie t+1 (FW['x']) albo zamknięcie t (FW['xc'])
ex=pd.DataFrame(np.nan,index=idx,columns=C.columns)
for k in range(1,8):
    cond=(r2.shift(-k)>70) if k<7 else pd.DataFrame(True,index=idx,columns=C.columns)
    ex=ex.where(ex.notna(), C.shift(-k).where(cond))
okb=O.shift(-1).notna()&~bad.shift(-1).fillna(False)
FW[71]=(ex/O.shift(-1)-1-COST).clip(-.7,1.5).where(okb); BASE[71]=FW[71].where(elig).mean(axis=1)
FW[72]=(ex/C-1-COST).clip(-.7,1.5).where(okb); BASE[72]=FW[72].where(elig).mean(axis=1)
FW[11]=(C.shift(-10)/C-1-COST).clip(-.7,1.5).where(okb); BASE[11]=FW[11].where(elig).mean(axis=1)
dn5=((ret<0).astype(float).rolling(5).sum()==5)
print("=== wyjście RSI2>70/7 sesji: N=71 wejście na otwarciu t+1, N=72 wejście na zamknięciu dnia sygnału")
sigs={"RSI2<5 nad SMA200 (obecna reguła)":first((r2<5)&(C>s200),5),
 "  RSI2: do 10% od szczytu 52t":first((r2<5)&(C>s200)&(r>=0.90),5),
 "  RSI2: ponad 10% pod szczytem 52t":first((r2<5)&(C>s200)&(r<0.90),5),
 "5 spadków nad SMA100 (obecna reguła)":first(dn5&(C>s100),5),
 "  5sp: do 10% od szczytu 52t":first(dn5&(C>s100)&(r>=0.90),5),
 "  5sp: ponad 10% pod szczytem 52t":first(dn5&(C>s100)&(r<0.90),5),
 "cofnięcie: do 10% od szczytu 52t + RSI2<10":first((r>=0.90)&(r2<10),5),
 "cofnięcie: do 5% od szczytu 52t + RSI2<10":first((r>=0.95)&(r2<10),5)}
for k,S in sigs.items():
    ev(S,71,k); ev(S,72,k)
print("\n=== wybicia: 120 sesji (obecna reguła) vs 52 tygodnie; N=10 otwarcie, N=11 zamknięcie dnia sygnału, N=20")
b120=first((C>hi120)&(V>=1.5*vmed)&(C>s200),10); b250=first((C>hi)&(V>=1.5*vmed),10)
for N in (10,11,20):
    ev(b120,N,"szczyt 120 sesji + wolumen + SMA200 (obecna)")
    ev(b250,N,"szczyt 52t + wolumen")
    ev(b120&~(C>hi),N,"szczyt 120 sesji, ale NIE 52t")
atr=(H-L).div(C).rolling(14).mean()*100
for lab,m in (("zmienność <3%",atr<3),("3–5%",(atr>=3)&(atr<5)),("≥5%",atr>=5)):
    ev(b250&m,20,f"szczyt 52t + wolumen, {lab}")
# ryzyko
for nm,S,N in (("szczyt 52t+wol, 20 sesji",b250,20),("cofnięcie 10% + RSI2<10, RSI2-exit",sigs["cofnięcie: do 10% od szczytu 52t + RSI2<10"],71)):
    x=FW[N].where(S&elig).stack().dropna(); print(f"{nm}: n={len(x)} najgorsza {x.min()*100:.0f}% strata>10%: {(x<-0.10).mean()*100:.1f}% mediana {x.median()*100:+.2f}% śr {x.mean()*100:+.2f}%")
print("sygnałów/rok: szczyt52t+wol", int((b250&elig)[idx>='2022-01-01'].values.sum()/4.87), " cofnięcie10", int((sigs['cofnięcie: do 10% od szczytu 52t + RSI2<10']&elig)[idx>='2022-01-01'].values.sum()/4.87))
