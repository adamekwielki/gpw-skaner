"""Jednorazowe pobranie danych z USA do badań (uruchamiane ręcznie z GitHub Actions).

Wynik (folder dane_usa/):
  usa_dzienne.pkl.xz   – {ticker: DataFrame Open/High/Low/Close/Volume}, 10 lat, ceny skorygowane (splity, dywidendy)
  usa_godzinowe.pkl.xz – {ticker: DataFrame ...}, ~730 dni, świece 60 min, indeks = POCZĄTEK świecy, czas Nowy Jork (bez strefy)
  usa_spolki.csv       – ticker, nazwa, sektor, indeks, mediana obrotu (USD)
Uniwersum: S&P 500 + S&P 400 (średnie) + S&P 600 (małe) + Nasdaq-100 + ETF-y rynkowe,
potem filtr płynności (mediana obrotu z 60 dni >= 5 mln USD, cena >= 3 USD).
"""
import io, lzma, pickle, time, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path("dane_usa")
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research script)"}


def wiki(url, kol_ticker, kol_nazwa, kol_sektor, indeks):
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8")
    for t in pd.read_html(io.StringIO(html)):
        cols = [str(c) for c in t.columns]
        if kol_ticker in cols:
            t.columns = cols
            out = pd.DataFrame({"ticker": t[kol_ticker].astype(str).str.strip().str.replace(".", "-", regex=False),
                                "nazwa": t[kol_nazwa] if kol_nazwa in cols else "",
                                "sektor": t[kol_sektor] if kol_sektor in cols else "",
                                "indeks": indeks})
            print(f"{indeks}: {len(out)} spółek")
            return out
    print(f"{indeks}: NIE ZNALEZIONO TABELI")
    return pd.DataFrame(columns=["ticker", "nazwa", "sektor", "indeks"])


def lista():
    W = "https://en.wikipedia.org/wiki/"
    czesci = [
        wiki(W + "List_of_S%26P_500_companies", "Symbol", "Security", "GICS Sector", "SP500"),
        wiki(W + "List_of_S%26P_400_companies", "Symbol", "Security", "GICS Sector", "SP400"),
        wiki(W + "List_of_S%26P_600_companies", "Symbol", "Company", "GICS Sector", "SP600"),
        wiki(W + "Nasdaq-100", "Ticker", "Company", "GICS Sector", "NDX"),
    ]
    L = pd.concat(czesci, ignore_index=True)
    L = L[L.ticker.str.match(r"^[A-Z][A-Z\-]{0,6}$")]
    L = L.groupby("ticker", as_index=False).agg({"nazwa": "first", "sektor": "first",
                                                  "indeks": lambda s: "+".join(sorted(set(s)))})
    etf = pd.DataFrame({"ticker": ["SPY", "QQQ", "IWM", "MDY", "DIA", "^VIX", "XLK", "XLF", "XLE", "XLV",
                                   "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC", "SMH", "XBI"],
                        "nazwa": "ETF/indeks", "sektor": "ETF", "indeks": "ETF"})
    return pd.concat([L, etf], ignore_index=True).drop_duplicates("ticker")


def pobierz(tickers, **kw):
    wynik = {}
    for i in range(0, len(tickers), 60):
        paczka = tickers[i:i + 60]
        for proba in range(3):
            try:
                df = yf.download(paczka, group_by="ticker", auto_adjust=True, progress=False, threads=True, **kw)
                break
            except Exception as e:
                print("błąd, ponawiam:", e)
                time.sleep(20)
        else:
            continue
        for t in paczka:
            try:
                d = df[t] if isinstance(df.columns, pd.MultiIndex) else df
                d = d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            except Exception:
                continue
            if len(d) < 50:
                continue
            if d.index.tz is not None:
                d.index = d.index.tz_convert("America/New_York").tz_localize(None)
            wynik[t] = d.astype({"Open": "float32", "High": "float32", "Low": "float32", "Close": "float32",
                                 "Volume": "float64"})
        print(f"{kw.get('interval', '1d')}: {min(i + 60, len(tickers))}/{len(tickers)}, mam {len(wynik)}")
        time.sleep(2)
    return wynik


def zapisz(obj, nazwa):
    p = OUT / nazwa
    with lzma.open(p, "wb", preset=6) as f:
        pickle.dump(obj, f, protocol=4)
    print(f"zapisano {p} ({p.stat().st_size / 1e6:.1f} MB)")


def main():
    L = lista()
    print("Łącznie kandydatów:", len(L))
    dz = pobierz(L.ticker.tolist(), period="10y", interval="1d")
    # filtr płynności na ostatnich 60 sesjach
    obrot = {t: float((d.Close * d.Volume).tail(60).median()) for t, d in dz.items()}
    L["obrot_usd"] = L.ticker.map(obrot)
    zostaja = [t for t, d in dz.items()
               if t.startswith("^") or L.loc[L.ticker == t, "sektor"].iloc[0] == "ETF"
               or (obrot.get(t, 0) >= 5e6 and float(d.Close.iloc[-1]) >= 3)]
    dz = {t: dz[t] for t in zostaja}
    print("Po filtrze płynności:", len(dz))
    zapisz(dz, "usa_dzienne.pkl.xz")
    godz = pobierz(list(dz.keys()), period="730d", interval="60m")
    zapisz(godz, "usa_godzinowe.pkl.xz")
    L[L.ticker.isin(dz.keys())].to_csv(OUT / "usa_spolki.csv", index=False)
    print("GOTOWE")


if __name__ == "__main__":
    main()
