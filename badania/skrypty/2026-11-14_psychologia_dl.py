import pickle, time, sys, pandas as pd, yfinance as yf
old=pickle.load(open("daily10y.pkl","rb"))
print("PKN 2012 close w starym pliku:", old["PKN"].Close.iloc[:3].round(2).tolist())
tics=sorted(old.keys()); out={}
for i in range(0,len(tics),50):
    ch=[t+".WA" for t in tics[i:i+50]]
    for k in range(3):
        try:
            df=yf.download(ch,start="2012-01-01",auto_adjust=False,group_by="ticker",progress=False,threads=True); break
        except Exception as e: print("retry",e); time.sleep(10)
    for t in ch:
        try:
            d=df[t].dropna(subset=["Close"])
            if len(d)>50: out[t[:-3]]=d[["Open","High","Low","Close","Adj Close","Volume"]].astype(float)
        except Exception: pass
    print(i,len(out),flush=True); time.sleep(1)
pickle.dump(out,open("daily_raw.pkl","wb"))
x=out["PKN"]; print(x.iloc[:2]); print(x.iloc[-2:])
