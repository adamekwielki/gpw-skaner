# Pobieranie danych do hipotezy 2 (dogrywka): godzinowe 730 dni + dzienne od 2012 dla TICKERY ze skaner.py
import pickle, time, sys, pandas as pd, yfinance as yf
s=open("skaner.py").read(); TIC=s.split('TICKERY = """')[1].split('"""')[0].split()
out_h, out_d = {}, {}
for i in range(0,len(TIC),40):
    ch=[t+".WA" for t in TIC[i:i+40]]
    for kind,kw,store in (("h",dict(period="730d",interval="1h"),out_h),("d",dict(start="2012-01-01"),out_d)):
        for k in range(3):
            try: df=yf.download(ch,auto_adjust=False,group_by="ticker",progress=False,threads=True,**kw); break
            except Exception as e: print("retry",e); time.sleep(10)
        for t in ch:
            try:
                d=df[t].dropna(subset=["Close"])
                if len(d)>50: store[t[:-3]]=d[["Open","High","Low","Close","Volume"]].astype(float)
            except Exception: pass
        time.sleep(2)
    print(i,len(out_h),len(out_d),flush=True)
pickle.dump(dict(h=out_h,d=out_d),open(sys.argv[1] if len(sys.argv)>1 else "dogrywka.pkl","wb"))
