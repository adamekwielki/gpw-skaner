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
| 📉 Mocne cofnięcie (od 15.11.2026) | RSI2 < 10, kurs nad SMA200, spółka −8% lub więcej w 5 sesji (bez paniki rynku) | limit +3%, najpóźniej 10 sesji, bez stopu | 14 lat: 85% / 82% zyskownych, śr. +1,1% / +0,5% (trening/test), 13/14 lat na plus; 5% transakcji traci >10%; losowe wejście z tym wyjściem: 64%, −0,4% |

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

## Zmiany w skanerze 15.11.2026 (po badaniu na 14 latach)
- 📈 Wybicie: pełną rangę ma tylko wybicie na roczny szczyt (52 tyg.); wybicie 120 sesji, które nie jest rocznym szczytem, jest oznaczone „słabsze” (−18 pkt, poza TOP 5). Trzymanie 10–20 sesji.
- 📉 RSI2: +6 pkt, gdy kurs ≥10% pod rocznym szczytem; tuż pod szczytem „słabsze” (poza TOP 5).
- 🚀 Wystrzał: dwa limity po pół pozycji – 38,2% i 61,8% korekty. Na 14 latach (TP +2%, 10 sesji): limit 38,2% wypełnia się w 74% przypadków (84–85% zyskownych, +1,4% / +1,0%), limit 61,8% w 59% (87% / 86%, +1,4% / +1,4%), limit 50% w 65% (+1,3% / +1,0%). Dziennik na żywo dalej liczy tylko limit 61,8%.
- ⚠️ Ostrzeżenie „nowy dołek 52 tyg.” (ostatnie 20 sesji), ramka sezonowa (15.11–15.12 słabo, 27.12–15.01 mocno), wyszukiwarka „Moje spółki” z oceną dla posiadacza.
- Sprawdzone i odrzucone jako nowa reguła: cofnięcie po świeżym szczycie 52 tyg. (RSI2 < 15): 66–80% zyskownych z TP, ale średnio tylko +0,1–0,3%. TP dla RSI2 / 5 spadków: winrate 76–85%, ale średnia spada do +0,3–0,7% (wyjście RSI2 > 70 lepsze).
- Harmonogram: cron GitHuba spóźnia się nawet o kilka godzin (13.11: skan z 17:20 ruszył o 23:00) – skan po sesji i poranny uruchamiają agenci przez workflow_dispatch.

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

## USA → 🔥 panika na GPW – badanie 15.11.2026 (hipoteza 1; 140 spółek z TICKERY, dzienne 2013–2026, trening 2013–21 / test 2022–26)
Skrypt: `badania/skrypty/2026-11-15_usa_panika.py`. Panika = RSI2 indeksu równowagowego < 10; sygnał USA dla sesji t = ostatnia sesja USA przed t. TP +3% na High dziennym, 10 sesji, koszt 0,4%.
- **Jako ostrzeżenie – słabe.** Po S&P < −2% szansa, że tego samego dnia RSI2 rynku spadnie < 10, rośnie z ~7% do 15% / 19% (trening/test), a w ciągu 3 sesji z ~18% do ~38%. Gdy rynek już słaby (RSI2 < 30): 35% / 45% vs 29% / 25%. Ale tylko ~5% początków paniki poprzedza spadek S&P > 2% lub VIX +20% – paniki na GPW są w większości „domowe”. VIX > 30 sam nic nie mówi.
- **Jako filtr reguły – NIE działa.** 🔥 panika z sygnałem z USA w 3 dni: −0,16% / +0,82% (2020 i 2022 ciągną w dół, 9% transakcji traci >10%); bez sygnału z USA: +0,33% / +0,89%. Nie dodawać.
- **Wczesne wejście (open t po S&P < −2%, spółka już −10%/5d): +0,31% / +0,71%**, 23/30 kwartałów – tyle samo co obecna reguła, nie lepiej.
- **Słaby ślad (ten sam co „luka paniki”):** S&P < −2% i średnia luka otwarcia płynnych spółek < −1% → kupno wszystkiego na otwarciu, TP +3%/10 sesji: +0,8% / +1,6% na transakcję vs losowy dzień −0,4% / −0,3%, 11/12 kwartałów. Ale tylko 21 dni w 13 lat (5 w teście), średnia po dniach ~+0,2% przez 6.03.2020 (−14,6%); bez tego ~+0,9%. Luka ≥ −1% przy tym samym S&P: nic (+0,0%). Wniosek praktyczny: po złej nocy w USA nie sprzedawać na otwarciu, a duża luka w dół to raczej okazja niż sygnał ucieczki – ale za mało danych na regułę.
- Przy okazji: 🔥 panika (obecna definicja) na 14 latach: 84% / 85% zyskownych, +0,29% / +0,86%, 10/14 lat i 36/55 kwartałów na plus, przewaga nad losowym dniem +0,7 / +1,2 pkt, 7% transakcji traci >10% → dodatnia, ale daleko od „95%, +2,5%” (hipoteza 10).

## 🌙 Dogrywka (hipoteza 2) – badanie 22.11.2026
Skrypty: `badania/skrypty/2026-11-22_dogrywka*.py`. Dane: godzinowe yfinance (137 spółek z TICKERY, 22.01.2024–18.11.2026; trening < 1.06.2025, test ≥ 1.06.2025) + przybliżenie na dziennych 2013–2026 (trening 2013–21 / test 2022–26). Sygnał: kurs o 16:00 (zamknięcie świecy 15:00) ≥ +8% do wczorajszego zamknięcia → kupno po kursie zamknięcia (fixing), sprzedaż następnego dnia. Koszt 0,4%. Przewaga = wynik − średnia wszystkich płynnych spółek kupionych na fixingu tego samego dnia (losowe wejście, to samo wyjście; losowe daje −0,2 do −0,3% po koszcie).
- **Godzinowe, +8% o 16:00 (n = 144 / 255):** sprzedaż na otwarciu t+1: +0,08% / +0,22%, 42% / 48% zyskownych, przewaga +0,37 / +0,38 pkt; **sprzedaż o 10:00 t+1: +0,32% / +0,54%, przewaga +0,62 / +0,83 pkt**; zamknięcie t+1: +0,02% / +0,44%; zamknięcie t+2: +0,74% / +0,87% (większy rozrzut). Przewaga dodatnia w 11/12 kwartałów (otwarcie) i 10/12 (10:00), ale wynik bezwzględny > 0 tylko w 8/12 kwartałów – cały 2024 ≈ 0 lub lekko pod kreską.
- Progi: im większy skok, tym lepiej – +10%: wyjście 10:00 +0,62% / +0,84%; +15%: +1,5% / +3,3% (mała próba 16 / 40). Pasmo +5–8% ≈ nic (+0,0%). Wolumen ≥ 2,5× do 16:00 nie poprawia stabilnie. Spółka, która o 16:00 jest > 3% pod szczytem dnia, gorsza na zamknięciu t+1.
- **Dzienne 2013–2026 (dzień ≥ +8%, n = 1262 / 1095):** noc (zamknięcie → otwarcie t+1) +0,63% / +0,34% po koszcie, przewaga +0,68 / +0,55 pkt, **13/14 lat z przewagą, 10/14 lat na plus po koszcie**; bez 2020: +0,25%, przewaga +0,51. Mediana ~0, tylko ~2% nocy traci > 5% (najgorsza w godzinowych −16%, LWB 7.04.2026). Kontrola: spółki −8% o 16:00 – brak efektu.
- Cena między 16:00 a fixingiem średnio bez zmian (+0,02%) – decyzja o 16:00 nic nie traci.
- **Ocena: działa, ale cienko.** Przewaga nad losowym wejściem stabilna (oba okresy, oba źródła danych), wynik netto +0,2–0,5% na noc przy ~45–50% zyskownych – opłaca się tylko przy niskim koszcie i wielu małych transakcjach. Pewność umiarkowana (2,9 roku danych godzinowych, lista spółek dzisiejsza). Do sprawdzenia przez Adama: czy XTB przyjmuje zlecenia na fazę zamknięcia (16:50–17:00) / dogrywki (17:00–17:05).

## Kolejka hipotez do zbadania (agent badawczy bierze pierwszą niezbadaną)
4. Reakcja na raporty kwartalne: luka po raporcie i dryf w kolejnych 5–10 sesjach.
5. Dywidendy: zachowanie kursu przed dniem odcięcia i po nim.
6. Wejście panika/CHOP na zamknięciu dnia sygnału (fixing) zamiast na otwarciu t+1 – dla wybić/RSI2/5 spadków zbadane 14.11.2026 (patrz sekcja „Psychologia”), zostaje panika i CHOP na danych godzinowych.
7. Rotacja sektorowa: czy najsilniejszy sektor z 1–3 miesięcy dalej wygrywa przez kolejny miesiąc.
8. Luka paniki na otwarciu (rynek ≤ −1,5%): potwierdzić na danych godzinowych, o której najlepiej kupować i kiedy wychodzić.
9. Przełom roku: czy efekt 27.12→15.01 jest silniejszy dla małych spółek / przegranych roku po odjęciu rynku; jak wyglądał w latach 2005–2012.
10. 🔥 Panika na 14 latach wypada dużo słabiej niż w pierwotnym teście 2-letnim (84–85% zyskownych, śr. +0,3% / +0,9%, 36/55 kwartałów na plus vs „~95%, +2,5%”) – sprawdzić na danych godzinowych i szukać filtra (głębsze RSI2 rynku < 5, spółka −15%, RSI2 spółki, odległość od szczytu 52 tyg.), zanim uznamy ją za najsilniejszą regułę.
11. 🌙 Dogrywka – filtry nocy: czy wynik zależy od sesji w USA po 17:00 (S&P od 17:00 do zamknięcia), od siły całego rynku tego dnia i od ESPI/raportu w dniu skoku; oraz czy łączenie z 🚀 wystrzałem (sprzedaż rano, potem limit 38,2/61,8%) poprawia łączny wynik.

## Dziennik prac (najnowsze na górze)
- 2026-11-22: badanie hipotezy 2 (🌙 dogrywka: +8% o 16:00 → fixing → sprzedaż rano): przewaga nad losowym +0,4–0,8 pkt w obu okresach, 11/12 kwartałów, 13/14 lat (dzienne), ale netto tylko +0,2–0,5% na noc, ~45–50% zyskownych → „działa, cienko”; propozycja etykiety w skanie przedsesyjnym 16:xx w raporcie. Na żywo (stan 20.11): 7/7 zamkniętych zyskownych (+2,6%), 29 otwartych śr. −5%.
- 2026-11-20: po sesji – cron 17:17 i ręczny skan 18:15 OK; 2 zamknięte (🔥 VOT, SLV: +2,6%), na żywo 7/7 zyskownych, ale 29 otwartych śr. −4,7% (3 na plusie; CRQ −13,9%, BMC −10,7%); przecena: średnia równowagowa −3,0%, ETF WIG20TR −4,6%, RSI2 rynku 1; 15 nowych 🔥 paniki, pierwsze 4× 📉 mocne cofnięcie (MIL, MBK, KTY, PKO); TOP 5: ICE, KGH, OML, SEV, RVU.
- 2026-11-20: Yahoo zgubił dzienną świecę 19.11 → nocny i poranny skan pokazały TOP 5 z 18.11. Skaner: odtwarza brakujące sesje z danych godzinowych, pokazuje na górze datę danych („kupno na otwarciu dd.mm”), przy nieaktualnych danych czerwony baner, brak alertów i zapisu do dziennika; w trakcie sesji baner „sygnały wstępne”.
- 2026-11-19: po sesji – cron 17:43 i ręczny skan 18:16 OK; 3 zamknięte (🔥 KGH, BMC, 🌀 ASB: każda +2,6%), na żywo razem 5/5 zyskownych; otwarte wybicia śr. −1,3% (12.11) / −0,8% (18.11), CHOP −1,8%; RSI2 rynku 6, WIG −0,6%; 8 sygnałów 🔥 paniki; TOP 5: KGH, BMC, CRQ, S2B, VOT.
- 2026-11-18: debata agentów – BMC (🔥 panika, TOP 2): **poważne zastrzeżenia** – aktywne ostrzeżenie „nowy dołek 52 tyg.”, ujemny kapitał, raport III kw. przesunięty bez daty (termin ok. 29.11 w oknie), 3 niewyjaśnione ESPI z 17.11. KGH bez zastrzeżeń, CRQ z zastrzeżeniami (raport w oknie).
- 2026-11-18: po sesji – cron 17:40 i ręczny skan 18:15 OK; 2 zamknięte (🌀 CHOP MDV, ALE: +2,6% w 1 dzień); 8 otwartych wybić (śr. −0,7%), 5 otwartych CHOP (śr. −1,2%); **RSI2 rynku 9 → pierwsze sygnały 🔥 paniki** (CRI, KGH, BMC, CRQ); WIG −0,5%; TOP 5: KGH, BMC, CRQ, TOA, EUR.
- 2026-11-17: po sesji – cron 17:59 i ręczny skan 18:16 OK; 0 zamkniętych, 8 otwartych wybić (śr. −0,4%), 7 nowych 🌀 CHOP; RSI2 rynku 11 (tuż nad progiem paniki), WIG −1,5%; TOP 5: WAS, TOA, EUR, ACT, KTY. Dziennik nie śledzi nowego wystrzału WAS z 16.11 (stary wpis z limitem 6,51).
- 2026-11-16: po sesji – ręczny skan 18:15 OK; 0 zamkniętych, 8 otwartych wybić (śr. −0,1%), 4 limity 🚀 czekają; RSI2 rynku 48 (z 88); TOP 5 tylko 3 pozycje (EUR, TOA, DAT); WAS nowy wystrzał +14,8%.
- 2026-11-15: badanie hipotezy 1 (USA → panika na GPW): ostrzeżenie słabe (2–3× większa szansa paniki, ale tylko ~5% panik poprzedzonych przez USA), filtr nie działa; ślad „S&P −2% + luka < −1%”; panika na 14 latach słabsza niż sądziliśmy → hipoteza 10. Na żywo: 0 zamkniętych transakcji.
- 2026-11-15: skaner – wyszukiwarka „Moje spółki”, nowa reguła 📉 mocne cofnięcie, kotwica 52 tyg. w wybiciach i RSI2, dwa limity po wystrzale, ostrzeżenie o dołku 52 tyg., ramka sezonowa; dziennik nie dubluje trwających sygnałów.
- 2026-11-14: badanie „psychologia inwestorów” na 14 latach danych dziennych (kotwica 52 tyg., loteria, okrągłe ceny, kalendarz, noc/sesja, przełom roku); hipoteza nr 3 (dni tygodnia) zamknięta.
- 2026-11-13: po sesji – cron 17:20 się nie uruchomił (był tylko skan 16:37 sprzed zamknięcia), ręczny skan 18:16 OK; 0 zamkniętych, 7 otwartych wybić (śr. ~0%); RSI2 rynku 88.
- 2026-11-12: po sesji – skan 17:09 OK, 8 sygnałów w dzienniku (4 wystrzał, 4 wybicie), 0 zamkniętych; RSI2 rynku 95.
- 2026-11-12: utworzono plik; dziennik sygnałów na żywo w `docs/dziennik_sygnalow.csv`.
