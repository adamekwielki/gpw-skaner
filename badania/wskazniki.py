"""Buduje tabelę cech (spółka x dzień) i wyniki wejścia dla każdego dnia.

Decyzja na zamknięciu dnia t, wejście na otwarciu t+1 (pierwsza świeca godzinowa).
Wyjście symulowane na świecach 4H (9-13, 13-17):
  - stop: najniższy low z 10 dni przed wejściem (luka pod stop -> wyjście po otwarciu)
  - realizacja: Stoch RSI K >= 80 na zamknięciu świecy 4H lub dnia -> wyjście po zamknięciu
  - limit czasu: zamknięcie N-tego dnia (N = 5 i 7)
"""
import os, sys, pickle
import numpy as np
import pandas as pd

S = "/tmp/claude-0/-home-claude/e8718b13-3df2-5d60-a93c-587237027e6b/scratchpad"
COST = 0.004  # 0,4% za całą transakcję (spread + poślizg; XTB 0% prowizji do limitu)


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def stoch_rsi(c):
    r = rsi(c)
    lo, hi = r.rolling(14).min(), r.rolling(14).max()
    k = (100 * (r - lo) / (hi - lo).replace(0, np.nan)).rolling(3).mean()
    return k, k.rolling(3).mean()


def tr(df):
    pc = df["Close"].shift()
    return pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)


def chop(df, n=14):
    rng = df["High"].rolling(n).max() - df["Low"].rolling(n).min()
    return 100 * np.log10(tr(df).rolling(n).sum() / rng.replace(0, np.nan)) / np.log10(n)


AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def daily_from_hourly(h):
    return h.groupby(h.index.normalize()).agg(AGG).dropna()


def fourh_from_hourly(h):
    # stooq: znacznik czasu = koniec świecy godzinowej (10:00 = 9:00-10:00)
    half = np.where(h.index.hour <= 13, 0, 1)
    key = [h.index.normalize(), half]
    f = h.groupby(key).agg(AGG).dropna()
    f.index = pd.MultiIndex.from_tuples(f.index, names=["day", "half"])
    return f


def build(ticker, h, dly=None, idx_daily=None):
    D = daily_from_hourly(h)
    if len(D) < 80:
        return None
    # dzienne wskaźniki: jeśli są dane dzienne z dłuższą historią, liczymy na nich (stosunki cen)
    base = D
    if dly is not None and len(dly) > len(D):
        base = dly.copy()
        base.index = base.index.normalize()
    c = base["Close"]
    f = pd.DataFrame(index=base.index)
    ch = chop(base)
    f["chop"] = ch
    f["chop_prev"] = ch.shift(1)
    for n in (3, 5, 10):
        f[f"chop_max{n}"] = ch.rolling(n).max()
    k, d = stoch_rsi(c)
    f["k"], f["d"], f["k_prev"] = k, d, k.shift(1)
    f["k_min4"] = k.rolling(4).min()
    f["k_min6"] = k.rolling(6).min()
    atr = tr(base).rolling(14).mean()
    f["atr_pct"] = atr / c * 100
    for n in (50, 100, 200):
        s = c.rolling(n).mean()
        f[f"dist{n}"] = (c / s - 1) * 100
        f[f"touch{n}"] = (base["Low"].rolling(5).min() <= s * 1.005) & (c > s)
    f["sma50_gt_200"] = c.rolling(50).mean() > c.rolling(200).mean()
    sd = c.rolling(20).std()
    bbw = 4 * sd / c.rolling(20).mean()
    f["bb_pct"] = bbw.rolling(120, min_periods=60).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    v = base["Volume"]
    f["vol5_20"] = v.rolling(5).mean() / v.rolling(20).mean()
    f["vol10_50"] = v.rolling(10).mean() / v.rolling(50).mean()
    f["drop_on_vol"] = (c < c.shift(5)) & (f["vol5_20"] > 1.1)
    f["ret60"] = (c / c.shift(60) - 1) * 100
    f["ret20"] = (c / c.shift(20) - 1) * 100
    lo60, hi60 = base["Low"].rolling(60).min(), base["High"].rolling(60).max()
    f["pos60"] = (c - lo60) / (hi60 - lo60) * 100
    rng10 = base["High"].rolling(10).max() - base["Low"].rolling(10).min()
    f["flat"] = rng10 / atr
    f["turnover20"] = (c * v).rolling(20).median()
    f["price"] = c
    # tygodniowy Stoch RSI tylko z zakończonych tygodni (bez zaglądania w przyszłość)
    w = base.resample("W-FRI").agg(AGG).dropna()
    kw, dw = stoch_rsi(w["Close"])
    wk = pd.DataFrame({"kw": kw, "dw": dw, "kw_prev": kw.shift(1)})
    wk.index = wk.index + pd.Timedelta(days=3)  # dostępne od poniedziałku po zamknięciu tygodnia
    f = f.join(wk.reindex(f.index, method="ffill"))

    # ograniczamy do dni z danymi godzinowymi (tam symulujemy transakcje)
    f = f.reindex(D.index)

    # 4H
    F = fourh_from_hourly(h)
    k4, d4 = stoch_rsi(F["Close"])
    ch4 = chop(F.reset_index(drop=True)).values
    F = F.assign(k4=k4.values, d4=d4.values, chop4=ch4)
    F["k4_prev"] = F["k4"].shift(1)
    F["k4_min8"] = F["k4"].rolling(8).min()
    F["chop4_max6"] = F["chop4"].rolling(6).max()
    last4 = F.groupby(level="day").tail(1).droplevel("half")
    f = f.join(last4[["k4", "d4", "k4_prev", "k4_min8", "chop4", "chop4_max6"]])

    # 1H średnie
    hc = h["Close"]
    for n in (100, 200):
        s = hc.rolling(n).mean()
        dist = (hc / s - 1) * 100
        touch = (h["Low"].rolling(6).min() <= s * 1.005) & (hc > s)
        g = pd.DataFrame({f"h_dist{n}": dist, f"h_touch{n}": touch})
        gl = g.groupby(g.index.normalize()).tail(1)
        gl.index = gl.index.normalize()
        f = f.join(gl)

    # ---- symulacja wyjść dla wejścia po każdym dniu t ----
    days = D.index
    Fo, Fh, Fl, Fc, Fk = (F[x].values for x in ("Open", "High", "Low", "Close", "k4"))
    Fday = F.index.get_level_values("day")
    day_pos = {dd: i for i, dd in enumerate(days)}
    first4 = {}
    for i, dd in enumerate(Fday):
        first4.setdefault(dd, i)
    dk = f["k"].values  # dzienne K (na zamknięciu dnia)
    lows10 = D["Low"].rolling(10).min().values
    atr_d = tr(D).rolling(14).mean().values

    res = {}
    for N in (5, 7):
        for stop_kind in ("low10", "atr15", "none"):
            r = np.full(len(days), np.nan)
            ex = np.full(len(days), -1)
            for t in range(len(days) - 1):
                nd = days[t + 1]
                if nd not in first4:
                    continue
                j = first4[nd]
                entry = Fo[j]
                if not np.isfinite(entry) or entry <= 0:
                    continue
                if stop_kind == "low10":
                    stop = lows10[t]
                elif stop_kind == "atr15":
                    stop = entry - 1.5 * atr_d[t]
                else:
                    stop = -np.inf
                if not np.isfinite(stop) or stop >= entry:
                    stop = -np.inf if stop_kind == "none" else entry * 0.97
                out, exit_day = None, None
                last_day_idx = min(t + N, len(days) - 1)
                jj = j
                while jj < len(Fo) and day_pos.get(Fday[jj], 10**9) <= last_day_idx:
                    if Fl[jj] <= stop:
                        out = min(Fo[jj], stop) if jj > j else min(entry, stop)
                        exit_day = day_pos[Fday[jj]]
                        break
                    if np.isfinite(Fk[jj]) and Fk[jj] >= 80 and jj > j:
                        out, exit_day = Fc[jj], day_pos[Fday[jj]]
                        break
                    # koniec dnia: dzienne K
                    end_of_day = (jj + 1 >= len(Fo)) or (Fday[jj + 1] != Fday[jj])
                    di = day_pos[Fday[jj]]
                    if end_of_day and di > t and np.isfinite(dk[di]) and dk[di] >= 80:
                        out, exit_day = Fc[jj], di
                        break
                    if end_of_day and di >= last_day_idx:
                        out, exit_day = Fc[jj], di
                        break
                    jj += 1
                if out is None:
                    continue
                if t + N > len(days) - 1 and exit_day == len(days) - 1:
                    continue  # transakcja ucięta końcem danych
                r[t] = out / entry - 1 - COST
                ex[t] = exit_day
            res[f"r_{N}_{stop_kind}"] = r
            res[f"x_{N}_{stop_kind}"] = ex
    for kk, vv in res.items():
        f[kk] = vv
    # czy wynik jest pełny (nie ucięty końcem danych)
    f["ticker"] = ticker
    f["day_i"] = np.arange(len(f))
    return f


def run(job):
    t, h, d, grp = job
    try:
        f = build(t, h, d)
        if f is not None:
            f["rynek"] = grp
        return f
    except Exception as e:
        print("ERR", t, repr(e), file=sys.stderr)
        return None


if __name__ == "__main__":
    data = pickle.load(open(f"{S}/bt/hourly.pkl", "rb"))
    dly = {}
    if os.path.exists(f"{S}/bt/daily.pkl"):
        dly = pickle.load(open(f"{S}/bt/daily.pkl", "rb"))
    from multiprocessing import Pool
    jobs = [(t, h, dly.get(grp, {}).get(t), grp) for grp in ("wse", "nc") for t, h in data[grp].items()]
    with Pool(os.cpu_count()) as p:
        frames = [f for f in p.map(run, jobs, chunksize=4) if f is not None]
    allf = pd.concat(frames)
    allf.index.name = "date"
    allf = allf.reset_index()
    # siła względna: percentyl ret60 w danym dniu
    allf["rs_pct"] = allf.groupby("date")["ret60"].rank(pct=True) * 100
    # stan rynku (WIG)
    idx = data["idx"].get("WIG")
    base_idx = dly.get("idx", {}).get("WIG")
    src = base_idx if base_idx is not None else daily_from_hourly(idx)
    src = src.copy(); src.index = src.index.normalize()
    ic = src["Close"]
    reg = pd.DataFrame({"wig_gt200": ic > ic.rolling(200).mean(),
                        "wig_gt50": ic > ic.rolling(50).mean(),
                        "wig50_up": ic.rolling(50).mean() > ic.rolling(50).mean().shift(10)})
    reg.index.name = "date"
    allf = allf.merge(reg.reset_index(), on="date", how="left")
    allf.to_pickle(f"{S}/bt/features.pkl")
    print(allf.shape, allf["date"].min(), allf["date"].max())
