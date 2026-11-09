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
    "panika":   "test: ~95% zyskownych, śr. +2,5% w ~3 dni (rzadkie, kilkanaście razy w roku)",
    "wystrzal": "test: ~90% zyskownych, śr. +1,5% (rzadkie duże straty – mała pozycja)",
    "5spadkow": "test: śr. +1,1–1,5%/transakcję, 63–69% zyskownych",
    "rsi2":     "test: śr. +0,7%/transakcję, ~65% zyskownych",
    "wybicie":  "test: śr. +1,5–2%/transakcję, ~50% zyskownych (zysk z nielicznych dużych ruchów)",
    "chop":     "test: ~73% zyskownych, śr. +0,5–1% (tylko gdy rynek wyprzedany)",
}
PRIORYTET = {"panika": 100, "wystrzal": 90, "5spadkow": 70, "wybicie": 65, "rsi2": 60, "chop": 55}
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
def analiza(t, D, H, panika_rynku, r2_rynku=50.0):
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
            sprzedaj=f"od razu zlecenie z limitem <b>+3% od ceny zakupu</b> (przy zakupie po {zl(close)} → {zl(close * 1.03)}); jeśli nie wejdzie – na zamknięciu {data_za(D, 10)}",
            stop="bez stopu (w testach stopy szkodziły) – trzymaj małą pozycję",
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
                        sprzedaj=f"z limitem <b>{zl(e * 1.02)}</b> (+2% od wejścia) albo na zamknięciu {data_za(D, 10 - po)}",
                        stop=f"awaryjny {zl(Cpre - 0.5 * atr)}", opis=info, aktywny=False))
            elif dni <= SPIKE_OKNO:
                odl = (close / L618 - 1) * 100
                mod.append(dict(typ="wystrzal", tytul=("🚀 PO WYSTRZALE – nie goń! Ustaw limit" if dni == 0
                                                      else "🚀 PO WYSTRZALE – czekaj na limit"),
                    kup=f"zlecenie z limitem <b>{zl(L618)}</b> (61,8% korekty; śmielej: {zl(L50)}) · kurs jest {pct(odl)} nad limitem",
                    sprzedaj=f"z limitem <b>+2% od ceny zakupu</b> (przy {zl(L618)} → {zl(L618 * 1.02)}) albo po 10 sesjach od zakupu",
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
            sprzedaj=f"po 10 sesjach ({data_za(D, 10)}) albo stop kroczący: najwyższe zamknięcie − 2×ATR",
            stop=f"stop kroczący, dziś {zl(close - 2 * atr)}",
            opis=f"Poprzedni szczyt {zl(hh)}, wolumen {v.iloc[-1] / vmed.iloc[-1]:.1f}× mediany."))
        if atr / close * 100 > 5:
            ostrz.append(f"⚠️ Duża zmienność ({atr / close * 100:.1f}% dziennie) – wybicie to tu loteria: w testach co 5. "
                         "transakcja traciła ponad 10%. Najwyżej pół pozycji.".replace(".", ",", 1))

    # 🌀 CHOP rozładowanie przy wyprzedanym rynku (k4 tylko informacyjnie)
    k4 = None
    H4 = to_4h(H)
    if H4 is not None and len(H4) > 60:
        k4 = float(stoch_rsi(H4["Close"])[0].iloc[-1])
    rozl = ch.tail(10).max() > 60 and ch1 < 50
    if rozl and trend_ok and r2_rynku < 30 and not any(m["typ"] == "panika" for m in mod):
        mod.append(dict(typ="chop", tytul="🌀 CHOP rozładowanie + rynek wyprzedany",
            kup=f"jutro na otwarciu (do ok. {zl(close * 1.01)})",
            sprzedaj=f"od razu zlecenie z limitem <b>+3% od ceny zakupu</b> (przy {zl(close)} → {zl(close * 1.03)}); jeśli nie wejdzie – na zamknięciu {data_za(D, 10)}",
            stop="bez stopu (w testach stopy szkodziły) – mała pozycja",
            opis=f"CHOP spadł z {ch.tail(10).max():.0f} do {ch1:.0f}, RSI2 rynku {r2_rynku:.0f} (&lt; 30), kurs w trendzie."))

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
:root{--bg:#0f1115;--card:#171a21;--tx:#eef0f4;--mut:#9aa1b1;--ln:#2a2f3a;--acc:#3ddc97;--warn:#f5b84b;--bad:#f06a6a;--blue:#7aa2ff;--gold:#f5c84b}
@media (prefers-color-scheme: light){:root{--bg:#f4f5f7;--card:#fff;--tx:#12151c;--mut:#5d6474;--ln:#e0e3e9;--acc:#0e9a63;--warn:#b77c08;--bad:#d03f3f;--blue:#3a64d8;--gold:#c99a10}}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,Segoe UI,Arial,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:18px 16px 40px}
h1{margin:0;font-size:22px} .sub{color:var(--mut);font-size:13.5px;margin:2px 0 14px}
h2{font-size:18px;margin:26px 0 10px} h2 small{font-weight:400;color:var(--mut);font-size:13.5px}
.box{padding:11px 14px;border-radius:12px;margin:0 0 10px;border:1px solid var(--ln);font-size:15px}
.ok{background:rgba(61,220,151,.10)} .warnb{background:rgba(245,184,75,.13)} .badb{background:rgba(240,90,90,.14)}
/* TOP 5 */
.top{display:flex;gap:12px;background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:14px;margin-bottom:12px}
.top.r1{border:2px solid var(--acc)}
.nr{flex:none;width:38px;height:38px;border-radius:50%;background:var(--acc);color:#04130c;font-weight:800;font-size:19px;display:grid;place-items:center}
.top:not(.r1) .nr{background:rgba(127,127,127,.18);color:var(--tx)}
.tb{flex:1;min-width:0}
.th{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.th a{font-size:23px;font-weight:800;color:var(--tx);text-decoration:none} .th a:hover{color:var(--acc)}
.th .kurs{margin-left:auto;font-size:17px;font-weight:600}
.sila{color:var(--gold);letter-spacing:1px;font-size:15px}
.tt{font-weight:600;margin:2px 0 10px;color:var(--mut)}
.tg{display:grid;gap:8px}
.tg div{padding:8px 11px;border-radius:10px;background:rgba(127,127,127,.08);font-size:15px}
.tg span{display:inline-block;min-width:82px;font-size:12px;font-weight:800;letter-spacing:.5px}
.tg .kp span{color:var(--acc)} .tg .sp span{color:var(--blue)} .tg .st span{color:var(--bad)}
.tw{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.bd{font-size:12.5px;padding:3px 9px;border-radius:12px;background:rgba(127,127,127,.14);color:var(--mut)}
.bd.g{background:rgba(61,220,151,.14);color:var(--acc)} .bd.b{background:rgba(122,162,255,.15);color:var(--blue)}
.bd.y{background:rgba(245,200,75,.16);color:var(--gold)} .bd.r{background:rgba(240,90,90,.14);color:var(--bad);font-weight:700}
/* lista */
.ctl{display:flex;flex-wrap:wrap;gap:7px;margin:4px 0 12px}
.ctl button{background:var(--card);color:var(--tx);border:1px solid var(--ln);border-radius:20px;padding:7px 12px;font:inherit;font-size:14px;cursor:pointer}
.ctl button.on{background:var(--acc);border-color:var(--acc);color:#05140d;font-weight:700}
.k{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:12px 14px;margin-bottom:10px}
.kh{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.kh a{font-size:19px;font-weight:800;color:var(--tx);text-decoration:none} .kh a:hover{color:var(--acc)}
.kh .kurs{margin-left:auto;font-weight:600}
.tag{font-size:12px;padding:2px 8px;border-radius:10px;background:rgba(127,127,127,.14);color:var(--mut)}
.mod{margin-top:9px;padding:9px 11px;border-radius:11px;border-left:4px solid var(--acc);background:rgba(61,220,151,.07)}
.mod.wystrzal{border-color:var(--blue);background:rgba(122,162,255,.08)} .mod.panika{border-color:var(--bad);background:rgba(240,90,90,.08)}
.mod.chop{border-color:var(--mut);background:rgba(127,127,127,.07)}
.mod h3{margin:0 0 5px;font-size:15px}
.plan{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:14.5px}
.plan .l{color:var(--mut);font-weight:600} .op{color:var(--mut);font-size:13px;margin-top:6px}
.ost{margin-top:8px;padding:8px 10px;border-radius:10px;background:rgba(240,90,90,.12);color:var(--bad);font-size:14px}
.ins{margin-top:8px;padding:8px 10px;border-radius:10px;background:rgba(122,162,255,.12);color:var(--blue);font-size:14px}
.ex{margin-top:8px;padding:8px 10px;border-radius:10px;background:rgba(245,184,75,.13);font-size:14px}
.info{color:var(--mut);font-size:12.5px;margin-top:8px}
details{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:10px 14px;margin:12px 0}
summary{cursor:pointer;font-weight:700;font-size:15.5px}
details[open] summary{margin-bottom:10px}
details .k{border-color:var(--ln);background:var(--bg)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:var(--bg);border:1px solid var(--ln);border-radius:16px;padding:5px 10px;font-size:13.5px}
.chip.top3{border-color:var(--acc)} .chip.top3 b{color:var(--acc)}
.leg{color:var(--mut);font-size:14px;line-height:1.6}
.stopka{color:var(--mut);font-size:12.5px;margin-top:20px;text-align:center}
@media (max-width:560px){.top{padding:12px;gap:9px}.nr{width:30px;height:30px;font-size:16px}.tg span{display:block;min-width:0}.th a{font-size:21px}}
"""

NAZWA = {"panika": "Odbicie po panice na rynku", "wystrzal": "Wejście na korekcie po wystrzale",
         "5spadkow": "5 spadków z rzędu w trendzie", "rsi2": "Mocne wyprzedanie w trendzie (RSI2)",
         "wybicie": "Wybicie na nowy szczyt", "chop": "CHOP rozładowanie przy wyprzedanym rynku"}

INSIDERZY = {}


def ocena(r):
    """Punkty do rankingu TOP 5: siła reguły z testów + dodatki. None = nie do kupna."""
    if any(x.startswith("⛔") for x in r["ostrz"]):
        return None, None
    kup = [m for m in r["mod"] if m.get("aktywny", True)]
    if not kup:
        return None, None
    m = max(kup, key=lambda m: PRIORYTET[m["typ"]])
    p = float(PRIORYTET[m["typ"]])
    if m["typ"] == "wystrzal":  # daleko od limitu = mała szansa wypełnienia
        p -= min(30.0, max(0.0, m.get("odl", 0) - 3) * 3)
    if r.get("insider"):
        p += 8
    if r.get("gwiazda"):
        p += 6
    if r["sr_hist"] is not None and r["n_hist"] >= 3:
        p += max(-6.0, min(6.0, r["sr_hist"] * 2))
    if any(x.startswith("⚠️") for x in r["ostrz"]):
        p -= 8
    if r["wyjscie"]:
        p -= 5
    return p, m


def pozycja(r):
    if r["atr"] > 5:
        return '<span class="bd r">½ pozycji – duża zmienność</span>'
    return '<span class="bd g">pełna pozycja</span>'


def kropki(p):
    n = 3 if p >= 80 else 2 if p >= 55 else 1
    return "★" * n + "☆" * (3 - n)


def karta_top(i, r):
    p, m = r["_p"], r["_m"]
    tv = f"https://www.tradingview.com/chart/?symbol=GPW:{r['spolka']}"
    bd = [f'<span class="bd g">{STATY[m["typ"]].replace("test: ", "w testach: ")}</span>']
    if r.get("insider"):
        bd.append('<span class="bd b">👔 zarząd kupił akcje</span>')
    if r.get("gwiazda"):
        bd.append('<span class="bd y">⭐ spółka dobrze reaguje na sygnały</span>')
    if r["sr_hist"] is not None and r["n_hist"] >= 3:
        bd.append(f'<span class="bd">historia tej spółki: {r["sr_hist"]:+.1f}% śr. z {r["n_hist"]}</span>'.replace(".", ",", 1))
    bd.append(f'<span class="bd">zmienność dzienna {r["atr"]:.1f}%</span>'.replace(".", ","))
    bd.insert(0, pozycja(r))
    ostrz = "".join(f'<div class="ost">{html.escape(x)}</div>' for x in r["ostrz"])
    return (f'<div class="top{" r1" if i == 0 else ""}"><div class="nr">{i + 1}</div><div class="tb">'
            f'<div class="th"><a href="{tv}" target="_blank">{r["spolka"]}</a><span class="sila" title="siła sygnału">{kropki(p)}</span>'
            f'<span class="kurs">{zl(r["kurs"])}</span></div>'
            f'<div class="tt">{m["tytul"].split(" ", 1)[0]} {NAZWA[m["typ"]]} · {html.escape(r["sektor"])}</div>'
            f'<div class="tg"><div class="kp"><span>KUP</span>{m["kup"]}</div>'
            f'<div class="sp"><span>SPRZEDAJ</span>{m["sprzedaj"]}</div>'
            f'<div class="st"><span>STOP</span>{m["stop"]}</div></div>'
            f'{ostrz}<div class="tw">{"".join(bd)}</div><div class="info">{m["opis"]}</div></div></div>')


def karta(r):
    tv = f"https://www.tradingview.com/chart/?symbol=GPW:{r['spolka']}"
    typy = (" ".join(m["typ"] for m in r["mod"]) + (" ostrz" if r["ostrz"] else "") + (" exit" if r["wyjscie"] else "")
            + (" insider" if r.get("insider") else "") + (" star" if r.get("gwiazda") else ""))
    star = '<span class="tag">⭐ dobrze reaguje</span>' if r.get("gwiazda") else ""
    mods = ""
    for m in r["mod"]:
        mods += (f'<div class="mod {m["typ"]}"><h3>{m["tytul"]}</h3><div class="plan">'
                 f'<span class="l">Kup</span><span>{m["kup"]}</span>'
                 f'<span class="l">Sprzedaj</span><span>{m["sprzedaj"]}</span>'
                 f'<span class="l">Stop</span><span>{m["stop"]}</span></div>'
                 f'<div class="op">{m["opis"]} <i>{STATY[m["typ"]]}</i></div></div>')
    ost = "".join(f'<div class="ost">{html.escape(x)}</div>' for x in r["ostrz"])
    if r.get("insider"):
        ost = f'<div class="ins">{html.escape(r["insider"])}</div>' + ost
    ex = (f'<div class="ex">🔔 Dzienny Stoch RSI = {r["k1"]:.0f} – jeśli masz tę spółkę, to strefa realizacji zysku.</div>'
          if r["wyjscie"] else "")
    hist = (f" · historia sygnałów: {r['sr_hist']:+.1f}% śr. z {r['n_hist']}".replace(".", ",")
            if r["sr_hist"] is not None else "")
    sek = r["sektor"] + (f" (#{r['sek_msc']})" if r.get("sek_msc") else "")
    return (f'<div class="k" data-typy="{typy}"><div class="kh"><a href="{tv}" target="_blank">{r["spolka"]}</a>'
            f'{star}<span class="tag">{html.escape(sek)}</span><span class="kurs">{zl(r["kurs"])}</span></div>'
            f'{mods}{ost}{ex}<div class="info">{"<b>½ pozycji</b> · " if r["atr"] > 5 and r["mod"] else ""}Zmienność {r["atr"]:.1f}% · RSI2 {r["r2"]:.0f} · Stoch RSI 1D {r["k1"]:.0f}'
            f'{" · 4H " + format(r["k4"], ".0f") if r["k4"] is not None else ""} · CHOP {r["ch1"]:.0f} · '
            f'{"nad" if r["nad200"] else "pod"} SMA200{hist}</div></div>')


def raport(wyniki, plik, rynek, sektory, panika):
    from zoneinfo import ZoneInfo
    teraz = dt.datetime.now(ZoneInfo("Europe/Warsaw")).strftime("%d.%m.%Y, godz. %H:%M")
    for r in wyniki:
        r["_p"], r["_m"] = ocena(r)
    kupno = sorted([r for r in wyniki if r["_p"] is not None], key=lambda r: (-r["_p"], r["spolka"]))
    poza_top = lambda r: r["_m"]["typ"] in ("chop", "rsi2") and r["atr"] > 5  # w testach niestabilne i ryzykowne
    top = [r for r in kupno if not poza_top(r)][:5]
    reszta = [r for r in kupno if r not in top]
    inne = sorted([r for r in wyniki if r["_p"] is None and (r["mod"] or r["ostrz"] or r["wyjscie"] or r.get("insider"))],
                  key=lambda r: (0 if r["mod"] else 1 if r.get("insider") else 2 if r["ostrz"] else 3, r["spolka"]))
    rk = {"ok": "ok", "warn": "warnb", "bad": "badb"}[rynek[0]]
    pan = ('<div class="box badb">🔥 <b>PANIKA NA MAŁYCH SPÓŁKACH</b> – historycznie najlepszy moment na odbicia.</div>'
           if panika else "")
    if top:
        top_html = "".join(karta_top(i, r) for i, r in enumerate(top))
        if len(top) < 5:
            top_html += f'<div class="box">Dziś tylko {len(top)} {"sygnał" if len(top) == 1 else "sygnały"} kupna – nie dobieraj na siłę.</div>'
    else:
        top_html = '<div class="box">Dziś brak sygnałów kupna. Czekamy – brak pozycji to też pozycja.</div>'
    licz = {t: sum(1 for r in reszta if any(m["typ"] == t for m in r["mod"])) for t in PRIORYTET}
    btn = "".join(f'<button data-f="{t}">{lab} ({licz[t]})</button>' for t, lab in
                  (("panika", "🔥 Panika"), ("wystrzal", "🚀 Wystrzał"), ("5spadkow", "📉 5 spadków"),
                   ("rsi2", "📉 RSI2"), ("wybicie", "📈 Wybicie"), ("chop", "🌀 CHOP")) if licz[t])
    reszta_html = (f'<h2>Pozostałe sygnały kupna <small>({len(reszta)}, od najmocniejszych)</small></h2>'
                   f'<div class="ctl"><button class="on" data-f="">Wszystkie</button>{btn}</div>'
                   f'<div id="cards">{"".join(karta(r) for r in reszta)}</div>') if reszta else ""
    n_ex = sum(1 for r in inne if r["wyjscie"])
    inne_html = (f'<details><summary>⛔ Ostrzeżenia, 🔔 do realizacji i pozostałe ({len(inne)})'
                 f'{f" – {n_ex} do realizacji" if n_ex else ""}</summary>{"".join(karta(r) for r in inne)}</details>'
                 if inne else "")
    chipy = "".join(f'<span class="chip{" top3" if i < 3 else ""}">{i + 1}. {html.escape(s)} <b>{m:+.1f}%</b></span>'
                    for i, (s, m) in enumerate(sektory))
    strona = f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Skaner GPW</title><style>{CSS}</style></head>
<body><div class="wrap"><h1>Skaner GPW</h1>
<div class="sub">Stan na {teraz} · {len(wyniki)} spółek · kliknij nazwę spółki, żeby otworzyć wykres</div>
<div class="box {rk}">{rynek[1]}</div>{pan}
<h2>🏆 TOP 5 na dziś <small>najmocniejsze sygnały kupna wg testów</small></h2>
{top_html}
{reszta_html}
{inne_html}
<details><summary>📊 Najmocniejsze sektory (ostatnie 1–3 miesiące)</summary><div class="chips">{chipy}</div></details>
<details><summary>❓ Jak czytać</summary><div class="leg">
<b>Kolejność TOP 5</b> = siła reguły w testach (🔥 panika &gt; 🚀 wystrzał &gt; 📉 5 spadków &gt; 📈 wybicie &gt; 📉 RSI2 &gt; 🌀 CHOP),
plus dodatkowe punkty za 👔 zakup zarządu, ⭐ i dobrą historię sygnałów na tej spółce. ★★★ = mocny, ★☆☆ = słaby.<br>
<b>Kup jutro na otwarciu</b> = zlecenie na otwarcie następnej sesji, najwyżej do podanej ceny.
<b>Zlecenie z limitem</b> = kupno tylko, jeśli kurs spadnie do tej ceny (w XTB: zlecenie z limitem).<br>
<b>Stop</b>: w testach stopy −5%/−8% pogarszały wynik, dlatego przy 🔥/🚀/🌀 go nie ma – zamiast tego trzymaj małe pozycje (maks. 3–4 naraz). Limit +2/3% ustaw zaraz po zakupie.
<b>½ pozycji</b> = spółka rusza się średnio ponad 5% dziennie – w testach co 10. transakcja traciła tam ponad 10%, więc wchodź mniejszą kwotą. 🌀 CHOP i 📉 RSI2 na takich spółkach nie trafiają do TOP 5.
Wyniki „w testach” to średnie z 08.2024–11.2026 po kosztach 0,4% – realnie licz na mniej.
Nie wchodź na 3 sesje przed raportem okresowym spółki.<br>
👔 = członek zarządu kupił akcje za ≥ 100 tys. zł w ostatnich {INSIDER_DNI} dniach (Bankier.pl). ⭐ = spółka w najlepszych 20% pod względem historycznych wyników sygnałów.
</div></details>
<div class="stopka">Narzędzie pomocnicze, nie rekomendacja inwestycyjna. Zawsze sprawdź wykres.</div></div>
<script>
document.querySelectorAll('.ctl button').forEach(b=>b.onclick=()=>{{
document.querySelectorAll('.ctl button').forEach(x=>x.classList.remove('on'));b.classList.add('on');const f=b.dataset.f;
document.querySelectorAll('#cards .k').forEach(k=>{{k.style.display=(!f||k.dataset.typy.split(' ').includes(f))?'':'none';}});}});
</script></body></html>"""
    Path(plik).parent.mkdir(parents=True, exist_ok=True)
    Path(plik).write_text(strona, encoding="utf-8")


# ---------------------- alerty na telefon (ntfy.sh) ----------------------
STRONA = "https://adamekwielki.github.io/gpw-skaner/"


def _ntfy(topic, tytul, tekst, tagi="chart_with_upwards_trend", prio=4):
    import json, urllib.request
    dane = json.dumps({"topic": topic, "title": tytul, "message": tekst, "tags": [tagi],
                       "priority": prio, "click": STRONA}).encode("utf-8")
    req = urllib.request.Request("https://ntfy.sh/", data=dane, method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()


def alerty(wyniki, panika, plik_stanu="docs/alerty.json"):
    """Wysyła powiadomienie o sygnałach ★★★ (bez powtórek tej samej spółki i reguły przez 5 dni)."""
    import json, re
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("alerty: brak NTFY_TOPIC – pomijam")
        return
    dzis = dt.date.today()
    try:
        stan = json.loads(Path(plik_stanu).read_text(encoding="utf-8"))
    except Exception:
        stan = {}
    stan = {k: v for k, v in stan.items() if (dzis - dt.date.fromisoformat(v)).days < 5}
    czysc = lambda x: re.sub(r"<[^>]+>", "", x).replace("&gt;", ">").replace("&lt;", "<")
    nowe = []
    for r in sorted([r for r in wyniki if r.get("_p") is not None and r["_p"] >= 80], key=lambda r: -r["_p"]):
        m = r["_m"]
        klucz = f'{r["spolka"]}:{m["typ"]}'
        if klucz in stan:
            continue
        stan[klucz] = dzis.isoformat()
        nowe.append(f'{m["tytul"].split(" ", 1)[0]} {r["spolka"]} ★★★ – {NAZWA[m["typ"]]}\n'
                    f'KUP: {czysc(m["kup"])}\nSPRZEDAJ: {czysc(m["sprzedaj"])}')
    try:
        if os.environ.get("NTFY_TEST") == "true":
            _ntfy(topic, "Skaner GPW – test", "Powiadomienia działają. Sygnały ★★★ będą przychodzić tutaj.", "white_check_mark", 3)
            print("alerty: wysłano test")
        if nowe:
            _ntfy(topic, f"Skaner GPW: mocne sygnały ★★★ ({len(nowe)})",
                  ("🔥 PANIKA NA RYNKU!\n\n" if panika else "") + "\n\n".join(nowe[:5]), "rotating_light", 4)
            print(f"alerty: wysłano {len(nowe)}")
        else:
            print("alerty: brak nowych sygnałów ★★★")
        Path(plik_stanu).parent.mkdir(parents=True, exist_ok=True)
        Path(plik_stanu).write_text(json.dumps(stan, indent=0), encoding="utf-8")
    except Exception as e:
        print(f"alerty: błąd wysyłki {e}")


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
            r = analiza(t, df, H.get(s), panika, idx_r2)
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
    alerty(wyniki, panika, str(Path(args.out).parent / "alerty.json"))
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
