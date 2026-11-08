"""
SKANER GPW v3 – reguły przetestowane na 717 spółkach GPW/NC (08.2024–11.2026)

Moduły (każdy podaje: gdzie kupić, gdzie sprzedać, stop awaryjny):
  🔥 PANIKA       indeks małych spółek mocno wyprzedany (RSI2<10) + spółka -10% w 5 dni
  🚀 WYSTRZAŁ     skok >=8% na wolumenie >=2,5x -> zlecenie z limitem na 61,8% korekty
  📉 5 SPADKÓW    5 spadkowych sesji z rzędu, kurs nad SMA100
  📉 RSI2<5       mocne wyprzedanie w trendzie (kurs nad SMA200)
  📈 WYBICIE      nowy szczyt zamknięcia ze 120 sesji, wolumen >=1,5x, nad SMA200
  🌀 CHOP+STOCH   rozładowanie konsolidacji + zakręt Stoch RSI (słabsza przewaga)
  ⛔ OSTRZEŻENIA  krach na wolumenie, gonienie wystrzału
  ⭐              spółka historycznie dobrze reaguje na te sygnały

Uruchomienie:  python skaner.py                 (otwiera raport w przeglądarce)
               python skaner.py --out docs/index.html --no-open   (GitHub Actions)
Wymaga: pip install yfinance pandas numpy
Narzędzie pomocnicze, nie rekomendacja inwestycyjna.
"""
import argparse
import datetime as dt
import html
import os
import sys
import warnings
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ======================= USTAWIENIA =======================
MIN_OBROT = 200_000          # mediana dziennego obrotu z 20 sesji [zł]
SPIKE_RET, SPIKE_VOL, SPIKE_OKNO = 0.08, 2.5, 15
EXIT_K = 80                  # dzienny Stoch RSI >= 80 -> strefa realizacji
# wyniki z testów (średnio na transakcję po kosztach 0,4%) – pokazywane na kartach
STATY = {
    "panika":   "test: śr. +3,5%/transakcję, ~70% zyskownych (rzadkie, kilkanaście razy w roku)",
    "wystrzal": "test: śr. ok. +2%/transakcję, ~60% zyskownych (realnie licz ok. +1%)",
    "5spadkow": "test: śr. +1,1–1,5%/transakcję, 63–69% zyskownych",
    "rsi2":     "test: śr. +0,7%/transakcję, ~65% zyskownych",
    "wybicie":  "test: śr. +1,2–1,8%/transakcję, ~50% zyskownych (zysk z nielicznych dużych ruchów)",
    "chop":     "test: śr. +0,1–0,5%/transakcję – najsłabsza przewaga",
}
PRIORYTET = {"panika": 100, "wystrzal": 90, "5spadkow": 70, "wybicie": 65, "rsi2": 60, "chop": 30}
# ==========================================================

TICKERY = """
11B 1AT ABE ACP ACT AGO ALE ALR AMC ANR APR APT ART ASB ASE AST ATC ATR ATT BCX BDF BDX
BFT BHW BLO BMC BNP BRS CAR CBF CDR CIG CLD CLN CMP COG CPS CRI CRJ CRQ CTX DAD DAT DBC
DIA DIG DNP DOM DVL EAT EBP ELT ENA ENG ENT EUR FRO GNS GPP GPW GRN GRX HUG ICE ING JSW
KGH KGN KPL KRU KTY LBW LMU LPP LWB MBK MBR MDG MDI MDV MIL MOC MOL MQR MRB MRC MUR NEU
NWG ODL OML OPL OPN PAS PBX PCO PCR PEO PEP PGE PKN PKO PKP PLW PXM PZU QRS RBW ROB RVU
S2B SCP SCW SEL SGN SLV SNT STX TEN TOA TOR TPE TRK TRN TXT UNT VGO VOT VOX VRC WAS WLT
WPL XTB XTP ZAB ZRE NTT SEV APE
""".split()

SEKTORY = {
    "Banki": "PKO PEO MBK ALR SPL ING MIL BHW",
    "Finanse": "PZU KRU GPW XTB VOT",
    "Energetyka": "PGE TPE ENA PEP KGN GRN",
    "Elektro / zasilanie": "APE ELT",
    "Surowce i górnictwo": "KGH JSW LWB",
    "Paliwa i chemia": "PKN ATT PCR",
    "IT sprzęt (AI, pamięci)": "ASB ABE ACT NTT",
    "IT i software": "ACP TXT CBF SEV ASE DAT ICE SGN WAS CMP 1AT",
    "Gry": "CDR TEN 11B PLW HUG CIG BLO CRJ",
    "Biotech": "SLV RVU SCP MOL CLN GNS",
    "Zdrowie i medtech": "NEU MRC SNT VOX MDG DIA",
    "Handel": "DNP ALE PCO EUR APR CAR AMC ZAB",
    "Odzież": "LPP CCC VRG ANR",
    "Nieruchomości": "DOM ECH ARH DVL",
    "Budownictwo": "BDX PXM TOR PBX MRB TRK",
    "Przemysł i obronność": "KTY STP BRS ATC LBW",
    "Kosmos": "CRI SCW",
    "Telekom i media": "CPS OPL WPL GPP AGO",
    "Turystyka i usługi": "RBW ENT BFT MBR",
}
SEKTOR_SPOLKI = {t: s for s, l in SEKTORY.items() for t in l.split()}

# ---- 👔 zakupy insiderów (Bankier.pl / Notoria) ----
# Test 2024-2026: zarząd kupuje za >=100 tys. zł -> ok. +1% ponad rynek w 10 sesji, 55% zyskownych.
# UWAGA: zakup zarządu PO spadku kursu (>5% w 20 sesji) wypadał źle (-3% vs rynek) -> ostrzeżenie.
INSIDER_MIN_ZL = 100_000
INSIDER_DNI = 14
BANKIER_TICKER = {
    "11BIT": "11B", "ATAL": "1AT", "ABPL": "ABE", "ASSECOPOL": "ACP", "ACTION": "ACT", "AGORA": "AGO",
    "ALLEGRO": "ALE", "ALIOR": "ALR", "AMICA": "AMC", "ANSWEAR": "ANR", "AUTOPARTN": "APR", "APATOR": "APT",
    "ARTIFEX": "ART", "ASBIS": "ASB", "ASSECOSEE": "ASE", "ASTARTA": "AST", "ARCTIC": "ATC", "ATREM": "ATR",
    "GRUPAAZOTY": "ATT", "BIOCELTIX": "BCX", "BUDIMEX": "BDX", "BENEFIT": "BFT", "HANDLOWY": "BHW",
    "BLOOBER": "BLO", "BUMECH": "BMC", "BNPPPL": "BNP", "BORYSZEW": "BRS", "INTERCARS": "CAR",
    "CYBERFLKS": "CBF", "CDPROJEKT": "CDR", "CIGAMES": "CIG", "CLOUD": "CLD", "CLNPHARMA": "CLN", "COMP": "CMP",
    "COGNOR": "COG", "CYFRPLSAT": "CPS", "CREOTECH": "CRI", "CREEPYJAR": "CRJ", "CAPTORTX": "CTX",
    "DADELO": "DAD", "DATAWALK": "DAT", "DEBICA": "DBC", "DIAG": "DIA", "DIGITANET": "DIG", "DINOPL": "DNP",
    "DOMDEV": "DOM", "DEVELIA": "DVL", "AMREST": "EAT", "ELEKTROTI": "ELT", "ENEA": "ENA", "ENERGOINS": "ENG",
    "ENTER": "ENT", "EUROCASH": "EUR", "FERRO": "FRO", "GENOMTEC": "GNS", "GRUPRACUJ": "GPP", "GPW": "GPW",
    "GRENEVIA": "GRN", "GREENX": "GRX", "HUUUGE": "HUG", "ICECODE": "ICE", "INGBSK": "ING", "JSW": "JSW",
    "KGHM": "KGH", "KOGENERA": "KGN", "KINOPOL": "KPL", "KRUK": "KRU", "KETY": "KTY", "LUBAWA": "LBW",
    "LPP": "LPP", "BOGDANKA": "LWB", "MBANK": "MBK", "MOBRUK": "MBR", "MEDICALG": "MDG", "MDIENERGIA": "MDI",
    "MILLENNIUM": "MIL", "MOLECURE": "MOL", "MIRBUD": "MRB", "MERCATOR": "MRC", "MURAPOL": "MUR",
    "NEUCA": "NEU", "NEWAG": "NWG", "ODLEWNIE": "ODL", "ORANGEPL": "OPL", "OPONEO.PL": "OPN", "PASSUS": "PAS",
    "PEKABEX": "PBX", "PEPCO": "PCO", "PCCROKITA": "PCR", "PEKAO": "PEO", "PEP": "PEP", "PGE": "PGE",
    "PKNORLEN": "PKN", "PKOBP": "PKO", "PKPCARGO": "PKP", "PLAYWAY": "PLW", "POLIMEXMS": "PXM", "PZU": "PZU",
    "QUERCUS": "QRS", "RAINBOW": "RBW", "RYVU": "RVU", "SCPFL": "SCP", "SCANWAY": "SCW", "SELENAFM": "SEL",
    "SYGNITY": "SGN", "SELVITA": "SLV", "SYNEKTIK": "SNT", "STALEXP": "STX", "TSGAMES": "TEN", "TOYA": "TOA",
    "TORPOL": "TOR", "TAURONPE": "TPE", "TRAKCJA": "TRK", "TEXT": "TXT", "UNIMOT": "UNT", "VIGOPHOTN": "VGO",
    "VOTUM": "VOT", "VOXEL": "VOX", "VERCOM": "VRC", "WASKO": "WAS", "WIELTON": "WLT", "WIRTUALNA": "WPL",
    "XTB": "XTB", "XTPL": "XTP", "ZABKA": "ZAB", "NTTSYSTEM": "NTT", "SEVENET": "SEV", "APSENERGY": "APE",
}


def pobierz_insiderow():
    """Zakupy insiderów z ostatnich dni (zarząd, >= INSIDER_MIN_ZL). Zwraca {ticker: [dict]}."""
    import json
    import urllib.request
    out = {}
    try:
        req = urllib.request.Request(
            "https://api.bankier.pl/quotes/public/insiders-table/?offset=0&limit=300&transaction_type=kupno",
            headers={"User-Agent": "Mozilla/5.0 (skaner-gpw)", "Accept": "application/json"})
        dane = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    except Exception as e:
        print("insiderzy: nie udało się pobrać –", e)
        return out
    granica = (dt.date.today() - dt.timedelta(days=INSIDER_DNI)).isoformat()
    for x in dane.get("results", []):
        t = BANKIER_TICKER.get(x.get("symbol", ""))
        funkcja = (x.get("insider_function") or "").lower()
        if not t or "zarząd" not in funkcja or (x.get("message_date") or "") < granica:
            continue
        out.setdefault(t, []).append(dict(data=x["message_date"], wart=float(x.get("value") or 0),
                                          kto=x.get("insider_function") or ""))
    # tylko łączne zakupy >= progu
    return {t: v for t, v in out.items() if sum(i["wart"] for i in v) >= INSIDER_MIN_ZL}


# ---------------------- wskaźniki ----------------------
def rsi_parts(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return up, dn, 100 - 100 / (1 + up / dn.replace(0, np.nan))


def rsi(c, n):
    return rsi_parts(c, n)[2]


def stoch_rsi(c):
    r = rsi(c, 14)
    lo, hi = r.rolling(14).min(), r.rolling(14).max()
    k = (100 * (r - lo) / (hi - lo).replace(0, np.nan)).rolling(3).mean()
    return k, k.rolling(3).mean()


def tr(df):
    pc = df["Close"].shift()
    return pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)


def chop(df, n=14):
    rng = df["High"].rolling(n).max() - df["Low"].rolling(n).min()
    return 100 * np.log10(tr(df).rolling(n).sum() / rng.replace(0, np.nan)) / np.log10(n)


def zl(x):
    if x is None or not np.isfinite(x):
        return "-"
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") + " zł"


def pct(x, plus=True):
    return (f"{x:+.1f}" if plus else f"{x:.1f}").replace(".", ",") + "%"


def data_za(dfd, sesji):
    """przybliżona data za N sesji (dni robocze)"""
    return (dfd.index[-1] + pd.offsets.BDay(sesji)).strftime("%d.%m")


# ---------------------- dane ----------------------
def pobierz(symbole, interval, period):
    out = {}
    for i in range(0, len(symbole), 40):
        part = symbole[i:i + 40]
        try:
            raw = yf.download(part, interval=interval, period=period, group_by="ticker",
                              progress=False, auto_adjust=True, threads=True)
        except Exception as e:
            print("błąd pobierania:", e)
            continue
        for s in part:
            try:
                df = raw[s] if isinstance(raw.columns, pd.MultiIndex) else raw
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if len(df):
                    out[s] = df
            except Exception:
                pass
    print(f"pobrano {interval}: {len(out)}/{len(symbole)}")
    return out


def to_4h(h):
    if h is None or len(h) < 100:
        return None
    h = h.copy()
    if h.index.tz is None:
        h.index = h.index.tz_localize("UTC")
    h.index = h.index.tz_convert("Europe/Warsaw")
    return h.resample("4h", offset="1h").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()


# ---------------------- mini-backtest per spółka (⭐) ----------------------
def historia_sygnalow(D, koniec_bez=20):
    """Średni wynik reguł na tej spółce w przeszłości (bez ostatnich 20 sesji)."""
    D = D.iloc[:-koniec_bez] if len(D) > koniec_bez + 150 else None
    if D is None:
        return None, 0
    o, hi, lo, c, v = (D[x].values for x in ("Open", "High", "Low", "Close", "Volume"))
    n = len(c)
    r2 = rsi(D["Close"], 2).values
    s100 = D["Close"].rolling(100).mean().values
    s200 = D["Close"].rolling(200).mean().values
    trend = np.where(np.isfinite(s200), c > s200, c > s100)
    vmed = pd.Series(v).rolling(20).median().shift(1).values
    vavg = pd.Series(v).rolling(20).mean().shift(1).values
    hh = pd.Series(c).rolling(120).max().shift(1).values
    down = pd.Series(np.r_[False, c[1:] < c[:-1]]).rolling(5).sum().values
    ret = np.r_[np.nan, c[1:] / c[:-1] - 1]
    wyn, busy = [], -1
    for t in range(130, n - 8):
        if t <= busy:
            continue
        x = None
        if (r2[t] < 5 and trend[t]) or (down[t] >= 5 and np.isfinite(s100[t]) and c[t] > s100[t]):
            for d in range(t + 1, t + 8):
                if r2[d] > 70 or d == t + 7:
                    x = (c[d] / o[t + 1] - 1, d); break
        elif np.isfinite(hh[t]) and c[t] > hh[t] and v[t] >= 1.5 * vmed[t] and trend[t]:
            x = (c[t + 7] / o[t + 1] - 1, t + 7)
        elif ret[t] >= SPIKE_RET and vavg[t] > 0 and v[t] >= SPIKE_VOL * vavg[t]:
            L = c[t] - 0.618 * (c[t] - c[t - 1])
            for j in range(t + 1, min(t + 16, n - 6)):
                if lo[j] <= L:
                    e = min(o[j], L)
                    for d in range(j, j + 6):
                        if d > j and hi[d] >= hi[t]:
                            x = (max(o[d], hi[t]) / e - 1, d); break
                        if d == j + 5:
                            x = (c[d] / e - 1, d); break
                    break
        if x:
            wyn.append(x[0] - 0.004)
            busy = x[1]
    if not wyn:
        return None, 0
    return float(np.mean(wyn) * 100), len(wyn)


# ---------------------- analiza spółki ----------------------
def analiza(t, D, H, panika_rynku):
    if D is None or len(D) < 130:
        return None
    o, hi, lo, c, v = (D[x] for x in ("Open", "High", "Low", "Close", "Volume"))
    close = float(c.iloc[-1])
    obrot = float((c * v).tail(20).median())
    if obrot < MIN_OBROT or close < 1:
        return None
    atr = float(tr(D).rolling(14).mean().iloc[-1])
    sma100, sma200, sma50 = (float(c.rolling(n).mean().iloc[-1]) for n in (100, 200, 50))
    nad200 = np.isfinite(sma200) and close > sma200
    trend_ok = nad200 if np.isfinite(sma200) else (np.isfinite(sma100) and close > sma100)
    up2, dn2, r2s = rsi_parts(c, 2)
    r2 = float(r2s.iloc[-1])
    au, ad = float(up2.iloc[-1]), float(dn2.iloc[-1])
    # cena zamknięcia, przy której RSI2 jutro przebije 70 (cel wyjścia)
    cel_rsi2 = close + max(0.0, (7 / 3) * ad - au)
    k, d = stoch_rsi(c)
    k1, d1, k0 = float(k.iloc[-1]), float(d.iloc[-1]), float(k.iloc[-2])
    ch = chop(D)
    ch1 = float(ch.iloc[-1])
    ret = c.pct_change()
    vavg = v.rolling(20).mean().shift(1)
    vmed = v.rolling(20).median().shift(1)
    ret5 = float(close / c.iloc[-6] - 1) * 100
    r60 = float(close / c.iloc[-61] - 1) * 100

    mod, ostrz = [], []
    stop_awaryjny = close - 2 * atr

    # 🔥 PANIKA
    if panika_rynku and ret5 <= -10:
        mod.append(dict(typ="panika", tytul="🔥 PANIKA NA RYNKU – odbicie",
            kup=f"jutro na otwarciu (do ok. {zl(close * 1.02)})",
            sprzedaj=f"gdy RSI2 &gt; 70 – dziś to zamknięcie ≥ {zl(cel_rsi2)}; najpóźniej {data_za(D, 7)}",
            stop=f"awaryjny {zl(stop_awaryjny)}",
            opis=f"Indeks małych spółek mocno wyprzedany, spółka {pct(ret5)} w 5 sesji."))

    # 🚀 WYSTRZAŁ – ostatni skok w oknie
    n = len(c)
    for s in range(n - 1, max(n - 1 - SPIKE_OKNO, 21), -1):
        if ret.iloc[s] >= SPIKE_RET and vavg.iloc[s] > 0 and v.iloc[s] >= SPIKE_VOL * vavg.iloc[s]:
            Cs, Cpre, Hs = float(c.iloc[s]), float(c.iloc[s - 1]), float(hi.iloc[s])
            gain = Cs - Cpre
            L618, L50 = Cs - 0.618 * gain, Cs - 0.5 * gain
            dni = n - 1 - s
            wyp = [j for j in range(s + 1, n) if lo.iloc[j] <= L618]
            odd = (Cs - close) / gain * 100
            odd_txt = f"Oddane {odd:.0f}% skoku." if odd >= 0 else "Kurs wciąż wyżej niż w dniu skoku."
            info = (f"Wystrzał {D.index[s]:%d.%m} ({dni} ses. temu): {pct(ret.iloc[s] * 100)} przy "
                    f"{v.iloc[s] / vavg.iloc[s]:.1f}× wolumenie. {odd_txt}")
            if close < Cpre - 0.5 * atr:
                ostrz.append("⛔ Po wystrzale kurs spadł poniżej ceny sprzed skoku – historia się skończyła, odpuść.")
            elif wyp:
                j = wyp[0]
                po = n - 1 - j
                if po <= 5:
                    e = min(float(o.iloc[j]), L618)
                    mod.append(dict(typ="wystrzal", tytul="🚀 PO WYSTRZALE – zlecenie wypełnione",
                        kup=f"wypełnione {D.index[j]:%d.%m} po ok. {zl(e)} ({pct((close / e - 1) * 100)} od wejścia)",
                        sprzedaj=f"z limitem {zl(Hs)} (szczyt dnia wystrzału) albo na zamknięciu {data_za(D, 5 - po)}",
                        stop=f"awaryjny {zl(Cpre - 0.5 * atr)}", opis=info, aktywny=False))
            elif dni <= SPIKE_OKNO:
                odl = (close / L618 - 1) * 100
                mod.append(dict(typ="wystrzal", tytul=("🚀 PO WYSTRZALE – nie goń! Ustaw limit" if dni == 0
                                                      else "🚀 PO WYSTRZALE – czekaj na limit"),
                    kup=f"zlecenie z limitem <b>{zl(L618)}</b> (61,8% korekty; śmielej: {zl(L50)}) · kurs jest {pct(odl)} nad limitem",
                    sprzedaj=f"z limitem {zl(Hs)} (szczyt dnia wystrzału) albo po 5 sesjach od zakupu",
                    stop=f"awaryjny {zl(Cpre - 0.5 * atr)} (pod ceną sprzed skoku)",
                    opis=info + f" Zlecenie ważne do ok. {data_za(D, SPIKE_OKNO - dni)}.", odl=odl, aktywny=True))
            break

    # 📉 5 SPADKÓW
    spadki = int((c.diff().tail(5) < 0).sum())
    if spadki == 5 and np.isfinite(sma100) and close > sma100:
        mod.append(dict(typ="5spadkow", tytul="📉 5 SPADKÓW Z RZĘDU w trendzie",
            kup=f"jutro na otwarciu (do ok. {zl(close * 1.01)})",
            sprzedaj=f"gdy RSI2 &gt; 70 – dziś to zamknięcie ≥ {zl(cel_rsi2)}; najpóźniej {data_za(D, 7)}",
            stop=f"awaryjny {zl(stop_awaryjny)}", opis=f"Kurs {pct((close / sma100 - 1) * 100)} nad SMA100."))

    # 📉 RSI2 < 5 w trendzie
    if r2 < 5 and trend_ok and not any(m["typ"] in ("5spadkow", "panika") for m in mod):
        mod.append(dict(typ="rsi2", tytul="📉 RSI2 &lt; 5 w trendzie",
            kup=f"jutro na otwarciu (do ok. {zl(close * 1.01)})",
            sprzedaj=f"gdy RSI2 &gt; 70 – dziś to zamknięcie ≥ {zl(cel_rsi2)}; najpóźniej {data_za(D, 7)}",
            stop=f"awaryjny {zl(stop_awaryjny)}", opis=f"RSI2 = {r2:.1f}, kurs nad SMA200."))

    # 📈 WYBICIE na szczyt 120 sesji
    hh = float(c.iloc[-121:-1].max())
    if close > hh and v.iloc[-1] >= 1.5 * vmed.iloc[-1] and nad200:
        mod.append(dict(typ="wybicie", tytul="📈 WYBICIE na szczyt ze 120 sesji",
            kup=f"jutro na otwarciu (do ok. {zl(close * 1.02)})",
            sprzedaj=f"po 7 sesjach ({data_za(D, 7)}) albo stop kroczący: najwyższe zamknięcie − 2×ATR",
            stop=f"stop kroczący, dziś {zl(close - 2 * atr)}",
            opis=f"Poprzedni szczyt {zl(hh)}, wolumen {v.iloc[-1] / vmed.iloc[-1]:.1f}× mediany."))

    # 🌀 CHOP + STOCH (nowa wersja)
    k4 = d4 = None
    t4 = False
    H4 = to_4h(H)
    if H4 is not None and len(H4) > 60:
        kk4, dd4 = stoch_rsi(H4["Close"])
        k4, d4 = float(kk4.iloc[-1]), float(dd4.iloc[-1])
        t4 = (kk4.tail(8) < 20).any() and kk4.iloc[-1] > kk4.iloc[-2] and k4 > d4
    t1 = (k.tail(6) < 30).any() and k1 > k0 and k1 > d1
    rozl = ch.tail(10).max() > 58 and ch1 < 50
    if rozl and (t1 or t4) and nad200:
        mod.append(dict(typ="chop", tytul="🌀 CHOP rozładowanie + zakręt Stoch RSI",
            kup=f"jutro na otwarciu (do ok. {zl(close * 1.01)})",
            sprzedaj=f"gdy dzienny Stoch RSI ≥ {EXIT_K} albo po 5 sesjach ({data_za(D, 5)})",
            stop=f"awaryjny {zl(stop_awaryjny)}",
            opis=f"CHOP {ch1:.1f} (był &gt; 58), zakręt na {'1D' if t1 else ''}{' i ' if t1 and t4 else ''}{'4H' if t4 else ''}."))

    # ⛔ ostrzeżenia
    for j in range(n - 3, n):
        if ret.iloc[j] <= -0.10 and vavg.iloc[j] > 0 and v.iloc[j] >= 3 * vavg.iloc[j]:
            ostrz.append(f"⛔ Krach {D.index[j]:%d.%m} ({pct(ret.iloc[j] * 100)} na wolumenie) – nie łap noża (w teście średnio −3,9%).")
            break
    if ret.iloc[-1] >= SPIKE_RET and v.iloc[-1] >= SPIKE_VOL * (vavg.iloc[-1] or 1):
        ostrz.append("⛔ Dziś wystrzał – NIE kupuj jutro rano (gonienie traci 1–3%). Ustaw limit na 61,8% korekty.")

    # 👔 insiderzy
    ins = INSIDERZY.get(t)
    insider = None
    if ins:
        suma = sum(i["wart"] for i in ins)
        ost = max(i["data"] for i in ins)
        ret20 = float(close / c.iloc[-21] - 1) * 100
        tys = f"{suma / 1000:,.0f}".replace(",", " ")
        if ret20 < -5:
            ostrz.append(f"⚠️ Zarząd kupił akcje ({ost[8:10]}.{ost[5:7]}, {tys} tys. zł) po spadku kursu "
                         f"({pct(ret20)} w 20 sesji) – w teście takie zakupy NIE pomagały (średnio −3% vs rynek).")
        else:
            insider = f"👔 Zarząd kupił akcje: {tys} tys. zł (ostatnio {ost[8:10]}.{ost[5:7]}) – w teście ok. +1% ponad rynek w 2 tyg."

    wyjscie = k1 >= EXIT_K
    sr_hist, n_hist = historia_sygnalow(D)
    return dict(spolka=t, kurs=close, atr=atr / close * 100, obrot=obrot, mod=mod, ostrz=ostrz,
                wyjscie=wyjscie, k1=k1, k4=k4, r2=r2, ch1=ch1, nad200=nad200, r60=r60,
                sektor=SEKTOR_SPOLKI.get(t, "Inne"), sr_hist=sr_hist, n_hist=n_hist, insider=insider)


# ---------------------- raport ----------------------
CSS = """
:root{--bg:#0f1115;--card:#171a21;--tx:#e6e8ee;--mut:#8b92a3;--ln:#262a33;--acc:#3ddc97;--warn:#f5b84b;--bad:#f06a6a;--blue:#7aa2ff}
@media (prefers-color-scheme: light){:root{--bg:#f6f7f9;--card:#fff;--tx:#151820;--mut:#667;--ln:#e3e5ea;--acc:#12a36b;--warn:#c98a10;--bad:#d84a4a;--blue:#3a64d8}}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.45 system-ui,Segoe UI,Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:18px 14px}
h1{margin:0 0 4px;font-size:21px} .sub{color:var(--mut);font-size:13px;margin-bottom:14px}
.box{padding:11px 13px;border-radius:12px;margin:0 0 12px;border:1px solid var(--ln);font-size:14.5px}
.ok{background:rgba(61,220,151,.10)} .warnb{background:rgba(245,184,75,.13)} .badb{background:rgba(240,90,90,.14)}
.chips{display:flex;gap:6px;overflow-x:auto;padding-bottom:6px;margin-bottom:12px}
.chip{flex:none;background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:6px 11px;font-size:13px;white-space:nowrap}
.chip.top{border-color:var(--acc)} .chip.top b{color:var(--acc)}
.ctl{display:flex;flex-wrap:wrap;gap:7px;margin:4px 0 14px}
.ctl button{background:var(--card);color:var(--tx);border:1px solid var(--ln);border-radius:20px;padding:8px 13px;font:inherit;font-size:14px}
.ctl button.on{background:var(--acc);border-color:var(--acc);color:#05140d;font-weight:700}
.k{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:13px;margin-bottom:11px}
.kh{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.kh a{font-size:20px;font-weight:800;color:var(--tx);text-decoration:none} .kh a:hover{color:var(--acc)}
.kh .kurs{margin-left:auto;color:var(--mut)} .star{color:#f5c84b;font-size:13px}
.tag{font-size:11.5px;padding:2px 8px;border-radius:10px;background:rgba(127,127,127,.14);color:var(--mut)}
.mod{margin-top:10px;padding:10px 11px;border-radius:11px;border-left:4px solid var(--acc);background:rgba(61,220,151,.07)}
.mod.wystrzal{border-color:var(--blue);background:rgba(122,162,255,.08)} .mod.panika{border-color:var(--bad);background:rgba(240,90,90,.08)}
.mod.chop{border-color:var(--mut);background:rgba(127,127,127,.07)}
.mod h3{margin:0 0 6px;font-size:15px}
.plan{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:14px}
.plan .l{color:var(--mut)} .op{color:var(--mut);font-size:13px;margin-top:6px}
.ost{margin-top:9px;padding:8px 10px;border-radius:10px;background:rgba(240,90,90,.12);color:var(--bad);font-size:13.5px}
.ins{margin-top:9px;padding:8px 10px;border-radius:10px;background:rgba(122,162,255,.12);color:var(--blue);font-size:13.5px}
.ex{margin-top:9px;padding:8px 10px;border-radius:10px;background:rgba(245,184,75,.13);font-size:13.5px}
.info{color:var(--mut);font-size:12.5px;margin-top:8px}
.leg{color:var(--mut);font-size:12.5px;line-height:1.6;margin-top:18px}
"""


INSIDERZY = {}


def karta(r):
    tv = f"https://www.tradingview.com/chart/?symbol=GPW:{r['spolka']}"
    typy = (" ".join(m["typ"] for m in r["mod"]) + (" ostrz" if r["ostrz"] else "") + (" exit" if r["wyjscie"] else "")
            + (" insider" if r.get("insider") else ""))
    star = '<span class="star">⭐ dobrze reaguje</span>' if r.get("gwiazda") else ""
    mods = ""
    for m in r["mod"]:
        mods += (f'<div class="mod {m["typ"]}"><h3>{m["tytul"]}</h3><div class="plan">'
                 f'<span class="l">Kup</span><span>{m["kup"]}</span>'
                 f'<span class="l">Sprzedaj</span><span>{m["sprzedaj"]}</span>'
                 f'<span class="l">Stop</span><span>{m["stop"]}</span></div>'
                 f'<div class="op">{m["opis"]}<br><i>{STATY[m["typ"]]}</i></div></div>')
    ost = "".join(f'<div class="ost">{html.escape(x)}</div>' for x in r["ostrz"])
    if r.get("insider"):
        ost = f'<div class="ins">{html.escape(r["insider"])}</div>' + ost
    ex = (f'<div class="ex">🔔 Dzienny Stoch RSI = {r["k1"]:.0f} (≥ {EXIT_K}) – jeśli masz pozycję, to strefa realizacji zysku.</div>'
          if r["wyjscie"] else "")
    hist = (f" · historia sygnałów: {r['sr_hist']:+.1f}% śr. z {r['n_hist']}".replace(".", ",")
            if r["sr_hist"] is not None else "")
    sek = r["sektor"] + (f" (#{r['sek_msc']})" if r.get("sek_msc") else "")
    return (f'<div class="k" data-typy="{typy}"><div class="kh"><a href="{tv}" target="_blank">{r["spolka"]}</a>'
            f'{star}<span class="tag">{html.escape(sek)}</span><span class="kurs">{zl(r["kurs"])}</span></div>'
            f'{mods}{ost}{ex}<div class="info">ATR {r["atr"]:.1f}% · RSI2 {r["r2"]:.0f} · Stoch RSI 1D {r["k1"]:.0f}'
            f'{" · 4H " + format(r["k4"], ".0f") if r["k4"] is not None else ""} · CHOP {r["ch1"]:.0f} · '
            f'{"nad" if r["nad200"] else "pod"} SMA200{hist}</div></div>')


def raport(wyniki, plik, rynek, sektory, panika):
    from zoneinfo import ZoneInfo
    teraz = dt.datetime.now(ZoneInfo("Europe/Warsaw")).strftime("%d.%m.%Y %H:%M")
    akt = [r for r in wyniki if r["mod"] or r["ostrz"] or r["wyjscie"] or r.get("insider")]
    akt.sort(key=lambda r: (-max([PRIORYTET[m["typ"]] for m in r["mod"]] or [0]),
                            -(1 if r.get("insider") else 0), -(1 if r.get("gwiazda") else 0), r["spolka"]))
    n_ins = sum(1 for r in akt if r.get("insider"))
    chipy = "".join(f'<span class="chip{" top" if i < 3 else ""}">{i + 1}. {html.escape(s)} <b>{m:+.1f}%</b></span>'
                    for i, (s, m) in enumerate(sektory))
    pan = ('<div class="box badb">🔥 <b>PANIKA NA MAŁYCH SPÓŁKACH</b> (RSI2 indeksu &lt; 10) – historycznie najlepszy moment '
           'na odbicia. Sprawdź karty z 🔥.</div>' if panika else "")
    rk = {"ok": "ok", "warn": "warnb", "bad": "badb"}[rynek[0]]
    licz = {t: sum(1 for r in akt if any(m["typ"] == t for m in r["mod"])) for t in PRIORYTET}
    btn = "".join(f'<button data-f="{t}">{lab} ({licz[t]})</button>' for t, lab in
                  (("panika", "🔥 Panika"), ("wystrzal", "🚀 Wystrzał"), ("5spadkow", "📉 5 spadków"),
                   ("rsi2", "📉 RSI2"), ("wybicie", "📈 Wybicie"), ("chop", "🌀 CHOP")))
    strona = f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Skaner GPW</title><style>{CSS}</style></head>
<body><div class="wrap"><h1>Skaner GPW</h1>
<div class="sub">Stan na {teraz} · przeskanowano {len(wyniki)} płynnych spółek · sygnałów: {len(akt)} · kliknij spółkę = wykres</div>
<div class="box {rk}">{rynek[1]}</div>{pan}
<div class="chips">{chipy}</div>
<div class="ctl"><button class="on" data-f="">Wszystkie</button>{btn}
<button data-f="insider">👔 Insiderzy ({n_ins})</button><button data-f="exit">🔔 Do realizacji</button><button data-f="ostrz">⛔ Ostrzeżenia</button><button data-f="star">⭐</button></div>
<div id="cards">{''.join(karta(r) for r in akt) or '<div class="box">Dziś brak sygnałów.</div>'}</div>
<div class="leg"><b>Jak czytać:</b> „Kup jutro na otwarciu” = zlecenie na otwarcie następnej sesji, najwyżej do podanej ceny.
„Zlecenie z limitem” = kupno tylko jeśli kurs spadnie do tej ceny (ustaw w XTB zlecenie z limitem). Stop awaryjny jest szeroki celowo –
w testach ciasne stopy pogarszały wynik. Wyniki „test:” to średnie z danych 08.2024–11.2026 po kosztach 0,4%; realnie licz na mniej.
Nie wchodź na 3 sesje przed raportem okresowym spółki. 👔 = członek zarządu kupił akcje za ≥ 100 tys. zł w ostatnich
{INSIDER_DNI} dniach (dane: Bankier.pl/Notoria) – to dodatkowy plus, nie samodzielny sygnał. ⭐ =spółka w najlepszych 20% pod względem historycznych wyników tych sygnałów.<br>
Narzędzie pomocnicze, nie rekomendacja inwestycyjna. Zawsze sprawdź wykres.</div></div>
<script>
let f='';document.querySelectorAll('.ctl button').forEach(b=>b.onclick=()=>{{
document.querySelectorAll('.ctl button').forEach(x=>x.classList.remove('on'));b.classList.add('on');f=b.dataset.f;
document.querySelectorAll('.k').forEach(k=>{{const t=k.dataset.typy+(k.querySelector('.star')?' star':'');k.style.display=(!f||t.split(' ').includes(f))?'':'none';}});}});
</script></body></html>"""
    Path(plik).parent.mkdir(parents=True, exist_ok=True)
    Path(plik).write_text(strona, encoding="utf-8")


# ---------------------- start ----------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="raport_gpw.html")
    ap.add_argument("--no-open", action="store_true")
    args, _ = ap.parse_known_args()

    symbole = [f"{t}.WA" for t in TICKERY]
    INSIDERZY.update(pobierz_insiderow())
    print(f"insiderzy: {len(INSIDERZY)} spółek z zakupami zarządu w ostatnich {INSIDER_DNI} dniach")
    D = pobierz(symbole, "1d", "2y")
    H = pobierz(symbole, "1h", "1y")

    # rynek: indeks równowagowy płynnych spółek (zastępuje sWIG80)
    rets = []
    for s, df in D.items():
        if len(df) > 150 and (df["Close"] * df["Volume"]).tail(20).median() >= MIN_OBROT:
            rets.append(df["Close"].pct_change().rename(s))
    R = pd.concat(rets, axis=1)
    R.index = pd.to_datetime(R.index).tz_localize(None) if getattr(R.index, "tz", None) else R.index
    idx = (1 + R.mean(axis=1).fillna(0)).cumprod()
    idx_r2 = float(rsi(idx, 2).iloc[-1])
    panika = idx_r2 < 10
    s200, s50 = idx.rolling(200).mean(), idx.rolling(50).mean()
    if idx.iloc[-1] > s200.iloc[-1]:
        rynek = ("ok", "🟢 Rynek (średnia płynnych spółek) nad SMA200 – gramy normalnie.")
    elif s50.iloc[-1] > s50.iloc[-11]:
        rynek = ("warn", "🟡 Rynek pod SMA200, ale SMA50 rośnie – mniejsze pozycje.")
    else:
        rynek = ("bad", "🔴 Rynek pod SMA200 i SMA50 spada – ostrożnie, połowa stawki. (Wyjątek: tryb 🔥 paniki.)")
    rynek = (rynek[0], rynek[1] + f" RSI2 rynku: {idx_r2:.0f}.")

    # sektory
    mom = {}
    for s, df in D.items():
        t = s[:-3]
        if len(df) > 61:
            c = df["Close"]
            m = 0.5 * (c.iloc[-1] / c.iloc[-21] - 1) + 0.5 * (c.iloc[-1] / c.iloc[-61] - 1)
            mom.setdefault(SEKTOR_SPOLKI.get(t, "Inne"), []).append(m * 100)
    sektory = sorted(((k, float(np.median(v))) for k, v in mom.items() if k != "Inne"), key=lambda x: -x[1])
    msc = {k: i + 1 for i, (k, _) in enumerate(sektory)}

    ostatnia = max(df.index[-1] for df in D.values())
    wyniki = []
    for s in symbole:
        t = s[:-3]
        df = D.get(s)
        if df is None or df.index[-1] < ostatnia - pd.Timedelta(days=6):
            continue  # brak świeżych notowań (zawieszona / wycofana)
        try:
            r = analiza(t, df, H.get(s), panika)
        except Exception as e:
            print(f"  {t}: błąd {e}")
            continue
        if r:
            r["sek_msc"] = msc.get(r["sektor"])
            wyniki.append(r)

    # ⭐ najlepsze 20% spółek wg historii sygnałów (min. 4 sygnały)
    hist = sorted([r for r in wyniki if r["n_hist"] >= 4 and r["sr_hist"] is not None], key=lambda r: -r["sr_hist"])
    for r in hist[:max(1, len(hist) // 5)]:
        r["gwiazda"] = True

    print(f"\nPrzeskanowano {len(wyniki)} spółek. {rynek[1]}{'  🔥 PANIKA!' if panika else ''}")
    for r in wyniki:
        if r["mod"]:
            print(f"  {r['spolka']:>4} {'⭐' if r.get('gwiazda') else '  '} " + " | ".join(m['tytul'] for m in r['mod']))
    raport(wyniki, args.out, rynek, sektory, panika)
    print("\nRaport:", os.path.abspath(args.out))

    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            from IPython.display import HTML, display
            display(HTML(Path(args.out).read_text(encoding="utf-8")))
            return
    except ImportError:
        pass
    if not args.no_open:
        webbrowser.open(Path(args.out).resolve().as_uri())


if __name__ == "__main__":
    main()
