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

## Psychologia inwestorów – badanie 14.11.2026 (386 spółek, dzienne 2013–2026, trening 2013–21 / test 2022–26)
Metoda: wejście na otwarciu t+1, koszt 0,4%, „przewaga” = wynik minus średnia wszystkich płynnych spółek kupionych tego samego dnia. Skrypty: `badania/skrypty/2026-11-14_psychologia_*.py` (dane: yfinance, auto_adjust=False; uwaga – lista to spółki notowane dziś, więc wyniki bezwzględne są lekko zawyżone).

**Potwierdzenie starych reguł na 14 latach (pierwotne testy miały 2 lata):** RSI2<5 nad SMA200: 63% zyskownych, +0,9% / +0,6% (trening/test), 14/14 lat; 5 spadków nad SMA100: 65%, +1,1% / +1,0%, 13/14 lat; wybicie 120 sesji + wolumen: +1,5% / +1,2% w 10 sesji, 13/14 lat.

**Działa:**
- **Kotwica 52 tygodni (anchoring).** Nowy szczyt 52 tyg. + wolumen ≥1,5×: +1,6% / +1,2% w 10 sesji, +2,3% / +2,3% w 20 sesji; przewaga +1,9 pkt, 14/14 lat; ~52% zyskownych (zysk z dużych ruchów), 12% transakcji traci >10%. Wybicie 120 sesji, które NIE jest szczytem 52 tyg.: tylko +0,4% / +0,8%, nieistotne → cała siła reguły 📈 pochodzi ze szczytu 52 tyg.
- **Nowy dołek 52 tyg. = nie łapać.** Przewaga −1,5 / −1,0 pkt w 10 sesji i −2,7 / −1,8 pkt w 20 sesji (1/14 lat na plus), także z RSI2<5.
- **RSI2<5 nad SMA200 działa dużo lepiej, gdy kurs jest ≥10% pod szczytem 52 tyg.:** +1,5% / +0,9% (65% zyskownych, 14/14 lat) vs +0,3% / +0,35% blisko szczytu. Dla 5 spadków podobnie (+1,5/+1,1 vs +0,7/+1,0).
- **Wybicia: wejście na zamknięciu dnia sygnału zamiast na otwarciu t+1 daje +0,2–0,5 pkt** (noc po wybiciu jest dodatnia). Przy RSI2 / 5 spadkach bez różnicy.
- **Noc vs sesja:** średnio cały zysk rynku powstaje w nocy (zamknięcie→otwarcie +0,13%/dzień), a w trakcie sesji rynek traci (−0,08%/dzień, wt–czw najgorzej); stabilne w obu okresach. Po wystrzale (+8%, wolumen 2,5×): noc +1,5% / +0,9%, następna sesja −0,6% → kupowanie rano po wystrzale to płacenie za emocje tłumu.
- **Kalendarz:** poniedziałek najlepszy dzień (+0,14%, oba okresy); pierwsze 3 sesje miesiąca +0,15%/dzień vs +0,02% w reszcie; sesja przed świętem +0,2% (mała próba). Za małe na samodzielną grę, dobre do wyboru momentu.
- **Przełom roku:** 27.12 → 15.01 wszystkie płynne spółki średnio +3,5% (10/13 lat na plus), 20% najgorszych spółek roku +4,6% (12/13 lat na plus). Okres 15.11 → 15.12 słaby: −1,2% (4/12 lat na plus). Tylko 13 obserwacji – sezonowość, nie pewnik.

**Efekt loterii (ostrzeżenie):** 20% najbardziej zmiennych spółek przegrywa z rynkiem o ~0,7 pkt na 20 sesji (2/14 lat na plus); 10% spółek z największym jednodniowym skokiem w ostatnich 20 sesjach: −0,6 / −0,9 pkt. Zmienne spółki opłacają się tylko z sygnałem (np. szczyt 52 tyg. przy ATR ≥5%: +6% w 20 sesji, ale mała próba i duży rozrzut).

**Nie działa:** okrągłe ceny (przebicia i odbicia identyczne jak przy losowych poziomach „placebo”); serie 4–6 wzrostów z rzędu (brak efektu); powrót kursu „na zero” do średniego kosztu zakupu po stracie >20% (lekko ujemny, mała próba, nieistotny); cofnięcie RSI2<10 tuż przy szczycie 52 tyg. (przewaga +0,5 pkt, ale wynik po kosztach ~+0,2%).

**Słaby ślad:** luka paniki – gdy cały rynek otwiera się ≤ −1,5% (24 dni w 13 lat), spółki z luką ≤ −4% kupione na otwarciu dają po 2 sesjach +1,3% / +4,3% (61–78% zyskownych); tego samego dnia do zamknięcia wynik niestabilny.

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
4. Reakcja na raporty kwartalne: luka po raporcie i dryf w kolejnych 5–10 sesjach.
5. Dywidendy: zachowanie kursu przed dniem odcięcia i po nim.
6. Wejście panika/CHOP na zamknięciu dnia sygnału (fixing) zamiast na otwarciu t+1 – dla wybić/RSI2/5 spadków zbadane 14.11.2026 (patrz sekcja „Psychologia”), zostaje panika i CHOP na danych godzinowych.
7. Rotacja sektorowa: czy najsilniejszy sektor z 1–3 miesięcy dalej wygrywa przez kolejny miesiąc.
8. Luka paniki na otwarciu (rynek ≤ −1,5%): potwierdzić na danych godzinowych, o której najlepiej kupować i kiedy wychodzić.
9. Przełom roku: czy efekt 27.12→15.01 jest silniejszy dla małych spółek / przegranych roku po odjęciu rynku; jak wyglądał w latach 2005–2012.

## Dziennik prac (najnowsze na górze)
- 2026-11-14: badanie „psychologia inwestorów” na 14 latach danych dziennych (kotwica 52 tyg., loteria, okrągłe ceny, kalendarz, noc/sesja, przełom roku); hipoteza nr 3 (dni tygodnia) zamknięta.
- 2026-11-13: po sesji – cron 17:20 się nie uruchomił (był tylko skan 16:37 sprzed zamknięcia), ręczny skan 18:16 OK; 0 zamkniętych, 7 otwartych wybić (śr. ~0%); RSI2 rynku 88.
- 2026-11-12: po sesji – skan 17:09 OK, 8 sygnałów w dzienniku (4 wystrzał, 4 wybicie), 0 zamkniętych; RSI2 rynku 95.
- 2026-11-12: utworzono plik; dziennik sygnałów na żywo w `docs/dziennik_sygnalow.csv`.
