# Pamięć badań – Skaner GPW

Plik czytają agenci przed każdą pracą i uzupełniają po niej. Zasada: **nie testujemy drugi raz tego, co już tu jest**, chyba że są nowe dane albo nowy pomysł na wariant.

## Protokół testów (obowiązkowy)
- Decyzja na zamknięciu dnia t, wejście na otwarciu t+1 (albo zlecenie z limitem). Koszt 0,4% na transakcję (GPW).
- Filtr płynności: mediana obrotu 20 sesji ≥ 200 tys. zł, cena ≥ 1 zł. Jedna pozycja naraz na spółkę na regułę.
- Take-profit / stop symulowane na świecach godzinowych; przy remisie TP/stop liczymy stop.
- Parametry wybierane tylko na okresie treningowym, wynik raportowany na teście (dane spoza dopasowania) + wynik kwartalny.
- **Zawsze porównanie z losowym wejściem przy tym samym wyjściu** – przy TP 2–3% nawet losowe wejście ma ~70% winrate.
- Uwaga na przeuczenie: im więcej wariantów, tym ostrzej oceniać. Min. ~40 transakcji w treningu.

## Reguły w skanerze (potwierdzone)
| Reguła | Definicja | Wyjście | Wynik testów |
|---|---|---|---|
| 🔥 Panika | RSI2 indeksu równowagowego płynnych spółek < 10 i spółka −10% w 5 sesji | limit +3%, najpóźniej 10 sesji, bez stopu | ~95% zyskownych, śr. +2,5% w ~3 dni; ~20 epizodów w 2 lata |
| 🚀 Wystrzał | +8% przy wolumenie ≥ 2,5× średniej 20d → limit L = C − 0,618·(C − C_pre), ważny 15 sesji | limit +2%, najpóźniej 10 sesji | ~90% zyskownych, śr. +1,5%; rzadkie straty do −30% |
| 📉 5 spadków | 5 spadkowych zamknięć z rzędu, kurs nad SMA100 | RSI2 > 70 lub 7 sesji | +1,1–1,5% |
| 📈 Wybicie | nowy szczyt zamknięcia 120 sesji, wolumen ≥ 1,5× mediany, nad SMA200 | trzymaj 10 sesji (TP szkodzi) | +1,5–2%, ~50% zyskownych |
| 📉 RSI2 | RSI2 < 5 nad SMA200 | RSI2 > 70 lub 7 sesji | +0,7% |
| 🌀 CHOP | CHOP był > 60 w 10 sesjach, teraz < 50, kurs w trendzie, RSI2 rynku < 30 | limit +3%, 10 sesji | ~73% zyskownych, +0,5–1%, pewność umiarkowana |
| 👔 Insiderzy | zakup członka zarządu ≥ 100 tys. zł (14 dni) | – | +1% vs rynek w 10 dni; po spadku kursu −3% (ostrzeżenie) |

Ryzyko: ATR > 5% dziennie → pół pozycji (co 10. transakcja traci >10%). CHOP i RSI2 przy ATR > 5% nie trafiają do TOP 5. Stopy −5%/−8% pogarszały każdą regułę.

## Przetestowane – NIE działa (nie powtarzać bez nowego pomysłu)
- Stoch RSI zakręcający z dołu (1D, 4H, tygodniowy, poziomy <10/<20/<30, przecięcie K>D) – gorzej niż losowo.
- Odbicie od SMA200 + zakręt Stoch RSI; „naładowany” CHOP ≥ 60 sam; zwężenie zakresu (ATR spada) + CHOP; Bollinger squeeze.
- Zaokrąglone dno (round bottom) – w trakcie miski −0,4%, wybicie ponad krawędź miski −2% (pułapka).
- Gonienie dzień po wystrzale (−1 do −3%), kupno po krachu na wolumenie (−3,9%), wybicie drugiej fali.
- Odbicia od SMA na 1H; ciasny stop na 10-dniowym dołku; wyjście na Stoch RSI 4H ≥ 80.
- TP przy wybiciu (szkodzi), TP przy RSI2/5 spadkach (nic nie daje), TP zależny od ATR (nie lepszy od stałego %).
- Wolumen: dotknięcie POC/VAL, VWAP 20d, AVWAP od wystrzału, udział fixingu, OBV/dywergencje – średnia ~0.
- Filtr wielkości spółki: małe spółki NIE są bardziej stratne w % strat >10%, a zarabiają najwięcej – nie wycinać.

## Słabe ślady (do obserwacji na żywo)
- Profil wolumenu: cena w „dziurze” profilu 60 sesji nad POC, TP 5% – +0,4–0,6%, przewaga nad losowym 8/8 kwartałów.
- Wybicie ponad VAH60 przy wolumenie > 2× – +0,5%.
- Wysychanie wolumenu na korekcie, potem wzrost na wolumenie – mało transakcji.

## Wpływ USA na GPW (badanie 11.2026, 550 sesji)
- Wczorajszy S&P 500 silnie wpływa na lukę na otwarciu GPW (korelacja ~0,45), ale prawie wcale na sesję po otwarciu (~0,05).
- Po spadku S&P > 2%: otwarcie GPW średnio −0,5 do −0,7%, potem w ciągu dnia brak dalszego spadku (mniejsze spółki lekko odrabiają).
- VIX: korelacja z luką −0,40. Powiązania sektorowe (SMH→CDR, XLE→PKN, XLF→banki) słabsze niż sam S&P.
- Wniosek: po złej nocy w USA nie sprzedawać na otwarciu; wejścia „na otwarciu” można ustawiać limitem nieco niżej.

## Rynek USA jako miejsce gry (badanie 11.2026)
- Proste przewagi z GPW w USA w większości nie działają (wybicia ujemne, RSI2/IBS +0,1–0,4%).
- „SPY RSI2 < 10 + spółka −10% w 5 dni nad SMA200”: przewaga ~+0,5%, krucha; przy koszcie 1% (konto PLN w XTB) strata.
- Wystrzał z limitem w USA: przewaga pozorna (artefakt porównania); ślad tylko przy wystrzałach ≥ 15%.
- Decyzja: skupiamy się na GPW, USA tylko jako tło.

## Kolejka hipotez do zbadania (agent badawczy bierze pierwszą niezbadaną)
1. Czy skok VIX / spadek S&P > 2% dzień wcześniej zapowiada 🔥 panikę na GPW (wczesne ostrzeżenie)?
2. Reguła dogrywki: spółka +8% o 16:00 → kupno na fixingu zamknięcia, sprzedaż następnego ranka (wymaga danych 15-min/godzinowych).
3. Efekt dnia tygodnia / początku miesiąca na GPW (napływy do OFE/PPK, wypłaty).
4. Reakcja na raporty kwartalne: luka po raporcie i dryf w kolejnych 5–10 sesjach.
5. Dywidendy: zachowanie kursu przed dniem odcięcia i po nim.
6. Wejście panika/CHOP na zamknięciu dnia sygnału (fixing) zamiast na otwarciu t+1.
7. Rotacja sektorowa: czy najsilniejszy sektor z 1–3 miesięcy dalej wygrywa przez kolejny miesiąc.

## Dziennik prac (najnowsze na górze)
- 2026-11-13: po sesji – cron 17:20 się nie uruchomił (był tylko skan 16:37 sprzed zamknięcia), ręczny skan 18:16 OK; 0 zamkniętych, 7 otwartych wybić (śr. ~0%); RSI2 rynku 88.
- 2026-11-12: po sesji – skan 17:09 OK, 8 sygnałów w dzienniku (4 wystrzał, 4 wybicie), 0 zamkniętych; RSI2 rynku 95.
- 2026-11-12: utworzono plik; dziennik sygnałów na żywo w `docs/dziennik_sygnalow.csv`.
