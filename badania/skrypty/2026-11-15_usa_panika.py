"""Hipoteza 1: czy spadek S&P > 2% / skok VIX dzień wcześniej zapowiada 🔥 panikę na GPW?
Dane: yfinance (140 spółek z TICKERY, dzienne 2012–2026, auto_adjust=False + Adj Close), ^GSPC, ^VIX.
Indeks = równowagowy płynnych spółek (jak w skaner.py), panika = RSI2(indeksu) < 10.
Sygnał USA dla sesji GPW t = ostatnia sesja USA przed dniem t (zamyka się po GPW).
Trening 2013–2021, test 2022–2026. Koszt 0,4%. TP +3% na High dziennym (brak stopu → remis nieistotny), max 10 sesji.
Uruchom: python 2026-11-15_usa_panika.py <katalog z daily_raw.pkl i us.pkl>
"""
import pickle, sys, numpy as np, pandas as pd
D = sys.argv[1] if len(sys.argv) > 1 else "."
COST = 0.004
raw = pickle.load(open(f"{D}/daily_raw.pkl", "rb")); us = pickle.load(open(f"{D}/us.pkl", "rb"))
def P(col): return pd.concat({t: d[col] for t, d in raw.items()}, axis=1).sort_index()
Cr = P("Close"); A = P("Adj Close").where(lambda x: x > 0); V = P("Volume"); f = A / Cr
O = P("Open") * f; H = P("High") * f; C = A; idx = C.index
traded = (V > 0) & Cr.notna()
turn = (Cr * V).where(traded).rolling(20, min_periods=10).median()
elig = traded & (turn >= 200_000) & (Cr >= 1)
ret = C / C.shift(1) - 1; ret = ret.where(ret.abs() < 0.6)
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
mret = ret.where(elig).mean(axis=1).fillna(0)
ix = (1 + mret).cumprod(); r2 = rsi(ix, 2); pan = r2 < 10
gap = (O / C.shift(1) - 1).where(elig).mean(axis=1)  # luka otwarcia rynku
# --- USA zmapowane na sesje GPW (ostatnia sesja USA ściśle przed dniem t)
spx = us["Close"]["^GSPC"].dropna(); vix = us["Close"]["^VIX"].dropna()
U = pd.DataFrame({"spx": spx.pct_change(), "vixch": vix.pct_change(), "vix": vix})
U.index = U.index + pd.Timedelta(hours=1)  # przesunięcie: dzień USA d jest „przed” sesją GPW d+1
Um = U.reindex(U.index.union(idx)).ffill().shift(1).reindex(idx)  # tylko dane z dni < t
# shift(1) po union: wartość z ostatniego wiersza przed t (dla t = dzień GPW pomijamy USA z tego samego dnia)
Um = U.copy(); Um.index = Um.index.normalize()
Um = Um.reindex(Um.index.union(idx)).ffill()
Um = Um.shift(1).reindex(idx)  # USA z dnia ≤ t−1 (kalendarzowo)
TR = (idx >= "2013-01-01") & (idx < "2022-01-01"); TE = idx >= "2022-01-01"
EV = {"S&P < −2%": Um.spx < -0.02, "S&P < −1,5%": Um.spx < -0.015, "VIX +20%": Um.vixch > 0.20,
      "VIX > 30": Um.vix > 30, "S&P<−2% lub VIX+20%": (Um.spx < -0.02) | (Um.vixch > 0.20)}
onset = pan & ~(pan.shift(1).rolling(5, min_periods=1).max().fillna(0).astype(bool))  # pierwszy dzień paniki po ≥5 dniach bez
pan_next3 = pd.concat([pan.shift(-k) for k in range(0, 3)], axis=1).fillna(False).any(axis=1)  # panika w t..t+2
print(f"Sesji: {len(idx)}, dni paniki: {pan[idx>='2013'].sum()}, początki paniki: {onset[idx>='2013'].sum()}")
print("\n## 1. Czy zdarzenie w USA zapowiada panikę? (P = prawdop. paniki w dniu t / w t..t+2, gdy RSI2 rynku w t−1 ≥ 10)")
notpan = ~pan.shift(1).fillna(False)
rows = []
for nm, e in EV.items():
    for lab, m in (("TR", TR), ("TE", TE)):
        base = notpan & m; ee = e & base
        p1 = pan[ee].mean(); p1b = pan[base].mean(); p3 = pan_next3[ee].mean(); p3b = pan_next3[base].mean()
        rec = (onset & m & e).sum() / max((onset & m).sum(), 1)
        rows.append([nm, lab, int(ee.sum()), round(p1*100), round(p1b*100), round(p3*100), round(p3b*100), round(rec*100)])
print(pd.DataFrame(rows, columns=["zdarzenie", "okres", "dni", "P(panika t)%", "baza%", "P(panika t..t+2)%", "baza%", "% początków paniki poprzedzonych"]).to_string(index=False))
# warunkowo: rynek już słaby (RSI2 w t−1 < 30)
print("\n   Gdy RSI2 rynku w t−1 < 30 (już słabo):")
rows = []
for nm in ("S&P < −2%", "S&P < −1,5%", "VIX +20%"):
    e = EV[nm]
    for lab, m in (("TR", TR), ("TE", TE)):
        base = (r2.shift(1) < 30) & (r2.shift(1) >= 10) & m; ee = e & base
        rows.append([nm, lab, int(ee.sum()), round(pan[ee].mean()*100), round(pan[base].mean()*100)])
print(pd.DataFrame(rows, columns=["zdarzenie", "okres", "dni", "P(panika t)%", "baza%"]).to_string(index=False))

# --- 2. Handel: wyjście TP +3% / 10 sesji, wejście open t+1 (lub open t)
def tp_exit(entry_shift, tp=1.03, N=10):
    """zwraca DataFrame: wynik transakcji wejścia na otwarciu dnia t+entry_shift dla każdej (t, spółka)"""
    eo = O.shift(-entry_shift); res = pd.DataFrame(np.nan, index=idx, columns=C.columns); done = pd.DataFrame(False, index=idx, columns=C.columns)
    for k in range(N):
        h = H.shift(-(entry_shift + k)); c = C.shift(-(entry_shift + k))
        hit = (h >= eo * tp) & ~done
        # jeśli otwarcie dnia k>0 już ≥ TP → wyjście po otwarciu
        ok = O.shift(-(entry_shift + k)); fill = np.where(ok >= eo * tp, ok / eo - 1, tp - 1) if k > 0 else tp - 1
        res = res.where(~hit, pd.DataFrame(fill, index=idx, columns=C.columns) if k > 0 else tp - 1); done |= hit
        if k == N - 1:
            last = ~done & c.notna(); res = res.where(~last, c / eo - 1)
    return (res - COST).where(eo.notna()).clip(-0.7, 1.5)
X1 = tp_exit(1); X0 = tp_exit(0)
r5 = C / C.shift(5) - 1
def first_sig(S, k=10):  # jedna pozycja naraz na spółkę: blokada 10 sesji
    S = S.fillna(False).copy(); arr = S.values; out = np.zeros_like(arr)
    for j in range(arr.shape[1]):
        last = -999
        for i in np.where(arr[:, j])[0]:
            if i - last >= k: out[i, j] = True; last = i
    return pd.DataFrame(out, index=S.index, columns=S.columns)
ALL1 = X1.where(elig); ALL0 = X0.where(elig)
def ev(S, X, ALL, label):
    S = first_sig(S & elig); x = X.where(S); base_day = ALL.mean(axis=1); out = [label]
    for m in (TR, TE):
        xs = x[m].stack().dropna(); ex = x[m].sub(base_day[m], axis=0).stack().dropna()
        rnd = ALL[m].stack().dropna()
        out += [len(xs), round((xs > 0).mean()*100), round(xs.mean()*100, 2), round(ex.mean()*100, 2), round((xs.mean()-rnd.mean())*100, 2)]
    allx = x[idx >= "2013"].stack().dropna(); q = allx.groupby(allx.index.get_level_values(0).to_period("Q")).mean()
    y = allx.groupby(allx.index.get_level_values(0).year).mean()
    out += [f"{(q>0).sum()}/{len(q)}", f"{(y>0).sum()}/{len(y)}", round((allx < -0.10).mean()*100, 1)]
    return out
cols = ["wariant", "TR n", "TR win%", "TR śr%", "TR vs ten sam dzień", "TR vs losowy dzień", "TE n", "TE win%", "TE śr%", "TE vs ten sam dzień", "TE vs losowy dzień", "kwartały+", "lata+", "% <−10%"]
spx_3 = pd.concat([(Um.spx < -0.02).shift(k) for k in range(0, 3)], axis=1).fillna(False).any(axis=1)
vix_3 = pd.concat([(Um.vixch > 0.20).shift(k) for k in range(0, 3)], axis=1).fillna(False).any(axis=1)
us3 = spx_3 | vix_3
def M(s): return pd.DataFrame(np.repeat(s.values[:, None], C.shape[1], 1), index=idx, columns=C.columns)
PAN = M(pan); US3 = M(us3); D10 = r5 <= -0.10
rows = [
 ev(PAN & D10, X1, ALL1, "🔥 panika (obecna reguła)"),
 ev(PAN & D10 & US3, X1, ALL1, "🔥 panika + USA (S&P<−2% / VIX+20% w 3 dni)"),
 ev(PAN & D10 & ~US3, X1, ALL1, "🔥 panika bez sygnału z USA"),
 ev(M(pan & ~pan.shift(1).fillna(False)) & D10, X1, ALL1, "🔥 tylko 1. dzień paniki"),
 # wczesne wejście: sygnał z USA, wejście na otwarciu t (zanim GPW potwierdzi panikę)
 ev(M(Um.spx < -0.02) & (r5.shift(1) <= -0.10), X0, ALL0, "USA S&P<−2% → open t, spółka −10%/5d (t−1)"),
 ev(M((Um.spx < -0.02) & (r2.shift(1) < 30)) & (r5.shift(1) <= -0.05), X0, ALL0, "S&P<−2% i RSI2 rynku<30 → open t, spółka −5%/5d"),
 ev(M(Um.spx < -0.02) & elig, X0, ALL0, "S&P<−2% → open t, wszystkie płynne"),
 ev(M(Um.vixch > 0.20) & elig, X0, ALL0, "VIX+20% → open t, wszystkie płynne"),
 ev(M((Um.spx < -0.02) & (gap < -0.01)) & elig, X0, ALL0, "S&P<−2% i luka rynku <−1% → open t, wszystkie"),
]
pd.set_option("display.width", 250)
print("\n## 2. Handel (TP +3%, max 10 sesji, koszt 0,4%); 'vs ten sam dzień' = minus średnia wszystkich płynnych spółek kupionych tego dnia tym samym wyjściem; 'vs losowy dzień' = minus średnia z wszystkich dni okresu")
print(pd.DataFrame(rows, columns=cols).to_string(index=False))
# wyniki roczne dla wariantów kluczowych
for lab, S, X, ALL in (("panika+USA", PAN & D10 & US3, X1, ALL1), ("panika bez USA", PAN & D10 & ~US3, X1, ALL1), ("S&P<−2% wszystkie open t", M(Um.spx < -0.02) & elig, X0, ALL0)):
    x = X.where(first_sig(S & elig)); a = x[idx >= "2013"].stack().dropna()
    g = a.groupby(a.index.get_level_values(0).year)
    print(f"\n{lab} – per rok (n, śr%):", " ".join(f"{y}:{len(v)}/{v.mean()*100:+.1f}" for y, v in g))

print("\n## 3. Odporność wariantu 'luka rynku' (wejście na otwarciu t wszystkich płynnych, TP +3%/10 sesji)")
rows = []
for nm, s in (("S&P<−2% & luka<−0,5%", (Um.spx < -0.02) & (gap < -0.005)), ("S&P<−2% & luka<−1%", (Um.spx < -0.02) & (gap < -0.01)),
              ("S&P<−2% & luka<−1,5%", (Um.spx < -0.02) & (gap < -0.015)), ("S&P<−1,5% & luka<−1%", (Um.spx < -0.015) & (gap < -0.01)),
              ("sama luka<−1% (bez USA)", gap < -0.01), ("sama luka<−1,5%", gap < -0.015), ("S&P<−2% & luka ≥ −1%", (Um.spx < -0.02) & (gap >= -0.01))):
    r = ev(M(s) & elig, X0, ALL0, nm); r.insert(1, f"dni TR/TE {int((s&TR).sum())}/{int((s&TE).sum())}"); rows.append(r)
print(pd.DataFrame(rows, columns=cols[:1] + ["dni"] + cols[1:]).to_string(index=False))
s = (Um.spx < -0.02) & (gap < -0.01)
dm = ALL0.mean(axis=1)[s & (idx >= "2013")]
print("dni S&P<−2% & luka<−1% (średnia wszystkich spółek):", " ".join(f"{d:%Y-%m-%d}:{v*100:+.1f}" for d, v in dm.items()))
print("średnia losowego dnia TR/TE:", round(ALL0[TR].stack().mean()*100, 2), round(ALL0[TE].stack().mean()*100, 2))
