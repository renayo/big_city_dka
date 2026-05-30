#!/usr/bin/env python3
"""
Realistic Yoga Simulation v2 — Large City (high-intervention) vs Small Town (biological)
"""
import argparse, math, datetime, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from tqdm import tqdm
import swisseph as swe
warnings.filterwarnings("ignore")

# ── Empirical datetime distributions ─────────────────────────────────────────
HOUR_W_LARGE = np.array([
    1.8,1.5,1.3,1.2,1.3,1.8, 2.8,4.5,9.2,8.1,6.0,5.5,
    7.8,6.5,5.8,5.3,4.8,4.2, 3.8,3.4,3.0,2.6,2.2,1.9,
], dtype=float); HOUR_W_LARGE /= HOUR_W_LARGE.sum()

HOUR_W_SMALL = np.array([
    4.8,5.2,5.6,5.9,5.7,5.2, 4.7,4.3,3.9,3.6,3.5,3.7,
    3.8,3.9,4.0,4.0,4.0,4.1, 4.2,4.1,4.1,4.2,4.4,4.7,
], dtype=float); HOUR_W_SMALL /= HOUR_W_SMALL.sum()

DOW_W_LARGE = np.array([1.07,1.12,1.13,1.11,1.09,0.83,0.72], dtype=float)
DOW_W_LARGE /= DOW_W_LARGE.sum()

DOW_W_SMALL = np.array([1.02,1.02,1.03,1.03,1.02,0.96,0.96], dtype=float)
DOW_W_SMALL /= DOW_W_SMALL.sum()

MONTH_W = np.array([7.8,7.2,8.0,8.1,8.4,8.5,8.8,9.0,8.7,8.5,8.2,8.8],dtype=float)
MONTH_W /= MONTH_W.sum()

# ── Cities ────────────────────────────────────────────────────────────────────
LARGE_CITIES = [
    ("New York City","NY",40.7128,-74.0060,8336817,-5),
    ("Los Angeles","CA",34.0522,-118.2437,3979576,-8),
    ("Chicago","IL",41.8781,-87.6298,2693976,-6),
    ("Houston","TX",29.7604,-95.3698,2304580,-6),
    ("Phoenix","AZ",33.4484,-112.074,1608139,-7),
    ("Philadelphia","PA",39.9526,-75.1652,1603797,-5),
    ("San Antonio","TX",29.4241,-98.4936,1434625,-6),
    ("San Diego","CA",32.7157,-117.1611,1386932,-8),
    ("Dallas","TX",32.7767,-96.7970,1304379,-6),
    ("San Jose","CA",37.3382,-121.8863,1021795,-8),
    ("Austin","TX",30.2672,-97.7431,978908,-6),
    ("Jacksonville","FL",30.3322,-81.6557,949611,-5),
]
SMALL_CITIES = [
    ("Flagstaff","AZ",35.1983,-111.6513,76831,-7),
    ("Cheyenne","WY",41.1400,-104.8202,63957,-7),
    ("Bismarck","ND",46.8083,-100.7837,73622,-6),
    ("Missoula","MT",46.8721,-113.9940,75516,-7),
    ("Pocatello","ID",42.8713,-112.4455,56376,-7),
    ("Burlington","VT",44.4759,-73.2121,45012,-5),
    ("Eau Claire","WI",44.8113,-91.4985,68792,-6),
    ("Bowling Green","KY",36.9685,-86.4808,72294,-6),
    ("Morgantown","WV",39.6295,-79.9559,32079,-5),
    ("Laramie","WY",41.3114,-105.5911,32158,-7),
    ("Prescott","AZ",34.5400,-112.4685,45827,-7),
    ("Yuma","AZ",32.6927,-114.6277,97521,-7),
    ("Texarkana","TX",33.4251,-94.0477,36812,-6),
    ("Brunswick","GA",31.1499,-81.4915,23082,-5),
]
NO_DST={"Phoenix","Flagstaff","Prescott","Yuma"}

def _pop_w(c): p=np.array([x[4] for x in c],dtype=float); return p/p.sum()
def _dst(cn,m): return 0 if cn in NO_DST else (1 if 4<=m<=10 else 0)
_DIM=[31,28,31,30,31,30,31,31,30,31,30,31]
def _leap(y): return (y%4==0 and y%100!=0) or y%400==0
def _dim(y,m): return _DIM[m-1]+(1 if m==2 and _leap(y) else 0)

def random_birth_ut(rng, city, hour_w, dow_w):
    cn,_,_,_,_,utc_std=city
    year=int(rng.integers(2010,2023)); mo=int(rng.choice(12,p=MONTH_W))+1
    dow=int(rng.choice(7,p=dow_w))
    # Reject-sample for valid day in this month with target DOW (fast, low rejection)
    for _ in range(100):
        day=int(rng.integers(1,_dim(year,mo)+1))
        if datetime.date(year,mo,day).weekday()==dow: break
    else:
        # Fallback: pick any day if repeated failures (very rare)
        day=int(rng.integers(1,_dim(year,mo)+1))
    hr=int(rng.choice(24,p=hour_w)); mi=int(rng.integers(0,60)); sc=int(rng.integers(0,60))
    dst=_dst(cn,mo); uth=(hr+mi/60+sc/3600)-(utc_std+dst)
    ud,um,uy=day,mo,year
    while uth>=24: uth-=24; ud+=1
    while uth<0:   uth+=24; ud-=1
    if ud>_dim(uy,um): ud=1; um+=1
    if um>12: um=1; uy+=1
    if ud<1:
        um-=1
        if um<1: um=12; uy-=1
        ud=_dim(uy,um)
    return swe.julday(uy,um,ud,uth), datetime.datetime(year,mo,day,hr,mi,sc)

# ── Astro constants ───────────────────────────────────────────────────────────
LAHIRI=swe.SIDM_LAHIRI
GRAHAS=[swe.SUN,swe.MOON,swe.MARS,swe.MERCURY,swe.JUPITER,swe.VENUS,swe.SATURN]
GNAMES=["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]
SIGN_LORD={0:swe.MARS,1:swe.VENUS,2:swe.MERCURY,3:swe.MOON,4:swe.SUN,
           5:swe.MERCURY,6:swe.VENUS,7:swe.MARS,8:swe.JUPITER,
           9:swe.SATURN,10:swe.SATURN,11:swe.JUPITER}
SIGN_NAMES=["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
            "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
KENDRA={0,3,6,9}
SPECIAL_ASP={swe.MARS:{3,7},swe.JUPITER:{4,8},swe.SATURN:{2,9}}
def _asp(pid,sign):
    a={(sign+6)%12}
    for o in SPECIAL_ASP.get(pid,set()): a.add((sign+o)%12)
    return a

YOGA_DEFS={
    "Ruchaka":{"pid":swe.MARS,    "pn":"Mars",    "signs":{0,7,9}},
    "Bhadra": {"pid":swe.MERCURY, "pn":"Mercury", "signs":{2,5}},
    "Hamsa":  {"pid":swe.JUPITER, "pn":"Jupiter", "signs":{3,8,11}},
    "Malavya":{"pid":swe.VENUS,   "pn":"Venus",   "signs":{1,6,11}},
    "Sasa":   {"pid":swe.SATURN,  "pn":"Saturn",  "signs":{6,9,10}},
}

def calc_chart(jd,lat,lon):
    swe.set_sid_mode(LAHIRI,0,0)
    ayam=swe.get_ayanamsa_ut(jd)
    _,ascmc=swe.houses(jd,lat,lon,b'W')
    lagna=int(((ascmc[0]-ayam)%360)//30)
    signs={}; lons={}
    for gid,gn in zip(GRAHAS,GNAMES):
        pos,_=swe.calc_ut(jd,gid,swe.FLG_SWIEPH)
        sid=(pos[0]-ayam)%360
        signs[gn]=int(sid//30); lons[gn]=sid
    sep=abs(lons["Mercury"]-lons["Sun"])
    if sep>180: sep=360-sep
    return {"lagna":lagna,"signs":signs,"lons":lons,
            "combust":sep<=12.0,"ayam":ayam}

def compute_yogas(chart):
    L=chart["lagna"]; S=chart["signs"]
    yogas={}
    # Panchamahapurusha
    for yn,yd in YOGA_DEFS.items():
        yogas[f"maha_{yn}"]=(S[yd["pn"]] in yd["signs"]) and ((S[yd["pn"]]-L)%12 in KENDRA)
    yogas["maha_Bhadra_strong"]=yogas["maha_Bhadra"] and not chart["combust"]
    yogas["maha_any"]=any(yogas[f"maha_{y}"] for y in YOGA_DEFS)

    # Dharma Karmadhipati
    s9=(L+8)%12; s10=(L+9)%12
    l9id=SIGN_LORD[s9]; l9n=GNAMES[GRAHAS.index(l9id)]
    l10id=SIGN_LORD[s10]; l10n=GNAMES[GRAHAS.index(l10id)]
    p9=S[l9n]; p10=S[l10n]
    taint=(SIGN_LORD[(L+7)%12]==l9id)
    asp9=_asp(l9id,p9); asp10=_asp(l10id,p10)
    dk_any=(p9==p10) or ((p10 in asp9) and (p9 in asp10)) or \
           ((p9==s10) and (p10==s9)) or ((p9==s9) and (p10==s10)) or \
           ((p9==p10) and (p9 in {s9,s10}))
    yogas["dk_exchange"]     = (p9==s10) and (p10==s9)
    yogas["dk_ownhouses"]    = (p9==s9)  and (p10==s10)
    yogas["dk_conjunction"]  = (p9==p10) and (p9 in {s9,s10})
    yogas["dk_conj_any"]     = (p9==p10)
    yogas["dk_mutualaspect"] = (p10 in asp9) and (p9 in asp10)
    yogas["dk_any"]          = dk_any
    yogas["dk_pure"]         = dk_any and not taint

    return yogas

ALL_YOGA_KEYS = (
    [f"maha_{y}" for y in YOGA_DEFS] +
    ["maha_Bhadra_strong","maha_any"] +
    ["dk_exchange","dk_ownhouses","dk_conjunction",
     "dk_conj_any","dk_mutualaspect","dk_any","dk_pure"]
)

MAHA_KEYS = [f"maha_{y}" for y in YOGA_DEFS] + ["maha_any"]
DK_KEYS   = ["dk_exchange","dk_ownhouses","dk_conjunction",
              "dk_conj_any","dk_mutualaspect","dk_any","dk_pure"]

# ── Simulation ────────────────────────────────────────────────────────────────
def simulate_group(cities, n, label, seed, hour_w, dow_w):
    rng=np.random.default_rng(seed); weights=_pop_w(cities)
    cidx=rng.choice(len(cities),size=n,p=weights)
    records=[]; errors=0
    for i in tqdm(range(n),desc=f"  {label}",unit="birth"):
        city=cities[cidx[i]]
        lat=city[2]+float(rng.normal(0,0.008))
        lon=city[3]+float(rng.normal(0,0.008))
        try:
            jd,ldt=random_birth_ut(rng,city,hour_w,dow_w)
            chart=calc_chart(jd,lat,lon)
            yogas=compute_yogas(chart)
        except Exception:
            errors+=1; continue
        rec={"group":label,"city":city[0],"state":city[1],
             "lat":round(lat,5),"lon":round(lon,5),
             "local_dt":ldt.isoformat(),"jd_ut":round(jd,6),
             "birth_hour":ldt.hour,"birth_dow":ldt.weekday(),"birth_month":ldt.month,
             "lagna_sign":chart["lagna"],"ayanamsha":round(chart["ayam"],4),
             "mercury_combust":int(chart["combust"])}
        for gn in GNAMES: rec[f"{gn.lower()}_sign"]=chart["signs"][gn]
        for k in ALL_YOGA_KEYS: rec[k]=int(yogas[k])
        records.append(rec)
    if errors: print(f"    [{label}] {errors} errors skipped ({errors/n*100:.1f}%)")
    return pd.DataFrame(records)

# ── Statistics ────────────────────────────────────────────────────────────────
def yoga_stats(df_L,df_S,keys):
    n_L,n_S=len(df_L),len(df_S); rows=[]
    for yoga in keys:
        k_L=int(df_L[yoga].sum()); k_S=int(df_S[yoga].sum())
        p_L=k_L/n_L; p_S=k_S/n_S
        tbl=np.array([[k_L,n_L-k_L],[k_S,n_S-k_S]])
        # Guard against zero cells
        if tbl.min()==0:
            rows.append({"Yoga":yoga,"Large_n":k_L,"Large_%":round(p_L*100,3),
                         "Small_n":k_S,"Small_%":round(p_S*100,3),
                         "Chi2":0.0,"p_raw":"1.000000","p_bonf":"1.000000",
                         "OR":1.0,"OR_CI_lo":0.0,"OR_CI_hi":999.0,
                         "Cohen_h":0.0,"sig_raw":False,"sig_bonf":False}); continue
        chi2,pval,_,_=stats.chi2_contingency(tbl,correction=False)
        a,b,c,d=k_L+.5,n_L-k_L+.5,k_S+.5,n_S-k_S+.5
        OR=(a*d)/(b*c); se=math.sqrt(1/a+1/b+1/c+1/d)
        h=2*(math.asin(math.sqrt(p_L))-math.asin(math.sqrt(p_S)))
        rows.append({"Yoga":yoga.replace("maha_","").replace("dk_",""),
            "col":yoga,
            "Large_n":k_L,"Large_%":round(p_L*100,3),
            "Small_n":k_S,"Small_%":round(p_S*100,3),
            "Chi2":round(chi2,4),"p_raw":f"{pval:.6f}",
            "p_bonf":f"{min(pval*len(keys),1.0):.6f}",
            "OR":round(OR,4),
            "OR_CI_lo":round(math.exp(math.log(OR)-1.96*se),4),
            "OR_CI_hi":round(math.exp(math.log(OR)+1.96*se),4),
            "Cohen_h":round(h,4),
            "sig_raw":pval<0.05,"sig_bonf":pval*len(keys)<0.05})
    return pd.DataFrame(rows)

def omnibus_test(df_L,df_S,keys):
    n_L,n_S=len(df_L),len(df_S); total=n_L+n_S
    obs=np.array([[float(df_L[k].sum()),float(df_S[k].sum())] for k in keys])
    exp_L=obs.sum(axis=1)*(n_L/total); exp_S=obs.sum(axis=1)*(n_S/total)
    chi2=sum((obs[i,0]-exp_L[i])**2/max(exp_L[i],1e-9)+
             (obs[i,1]-exp_S[i])**2/max(exp_S[i],1e-9) for i in range(len(keys)))
    return chi2, float(stats.chi2.sf(chi2,df=len(keys)-1))

def lagna_chi2(df_L,df_S):
    obs=np.array([[float((df_L["lagna_sign"]==i).sum()),
                   float((df_S["lagna_sign"]==i).sum())] for i in range(12)])
    c2,p,_,_=stats.chi2_contingency(obs.T,correction=False); return c2,p

def dt_summary(df_L,df_S):
    rows=[]
    for lbl,df in [("Large city\n(high-intervention)",df_L),
                   ("Small town\n(biological)",df_S)]:
        hc=df["birth_hour"].value_counts().sort_index()
        rows.append({"Group":lbl,
            "Peak hour":f"{hc.idxmax():02d}:00",
            "Trough hour":f"{hc.idxmin():02d}:00",
            "Daytime 6am–6pm":f"{df['birth_hour'].between(6,17).mean()*100:.1f}%",
            "Overnight 0–5am":f"{df['birth_hour'].between(0,5).mean()*100:.1f}%",
            "Weekday Mon–Fri":f"{df['birth_dow'].between(0,4).mean()*100:.1f}%",
            "Weekend Sat–Sun":f"{df['birth_dow'].isin([5,6]).mean()*100:.1f}%"})
    return pd.DataFrame(rows)

# ── Report ────────────────────────────────────────────────────────────────────
SEP="─"*78

def print_report(df_L,df_S,maha_df,dk_df,m_om,d_om,lc2,lp,dts):
    n_L,n_S=len(df_L),len(df_S)
    print(f"\n{'═'*78}")
    print(f"  REALISTIC YOGA SIMULATION  |  Lahiri Ayanamsha")
    print(f"  Large city (high-intervention datetime):  N={n_L:,}")
    print(f"  Small town (biological circadian):        N={n_S:,}")
    print(f"{'═'*78}")

    print(f"\n  INPUT DISTRIBUTIONS VERIFIED")
    print(f"  {SEP}")
    for _,r in dts.iterrows():
        grp=r["Group"].replace("\n"," ")
        print(f"  {grp}")
        for k,v in r.items():
            if k!="Group": print(f"    {k:<22}: {v}")
    
    print(f"\n  LAGNA DISTRIBUTION  χ²={lc2:.2f}  p={lp:.4f}  "
          f"({'★ SIGNIFICANT' if lp<0.001 else 'significant' if lp<0.05 else 'not significant'})")
    print(f"  {'Sign':<13}{'Large%':>7}{'Small%':>7}{'Δ%':>8}  Note")
    print(f"  {SEP}")
    for i in range(12):
        pL=float((df_L["lagna_sign"]==i).mean())*100
        pS=float((df_S["lagna_sign"]==i).mean())*100
        flag=" ◄◄" if abs(pL-pS)>2.0 else " ◄" if abs(pL-pS)>1.2 else ""
        print(f"  {SIGN_NAMES[i]:<13}{pL:>6.2f}%{pS:>6.2f}%{pL-pS:>+7.2f}%{flag}")

    def yoga_table(title, df, omni, bonf_n):
        print(f"\n  {title}")
        print(f"  {SEP}")
        print(f"  {'Yoga':<20}{'Large%':>7}{'Small%':>7}{'Δ%':>6}"
              f"{'χ²':>8}{'p_raw':>10}{'p_bonf':>10}{'OR':>7} Sig?")
        print(f"  {SEP}")
        for _,r in df.iterrows():
            diff=r["Large_%"]-r["Small_%"]
            sig="✓" if r["sig_bonf"] else ("·" if r["sig_raw"] else " ")
            print(f"  {r['Yoga']:<20}{r['Large_%']:>6.2f}%{r['Small_%']:>6.2f}%"
                  f"{diff:>+5.2f}%{r['Chi2']:>8.3f}{r['p_raw']:>10}"
                  f"{r['p_bonf']:>10}{r['OR']:>7.4f} {sig}")
        print(f"  Omnibus χ²={omni[0]:.3f}  p={omni[1]:.6f}  "
              f"({'★p<0.001' if omni[1]<0.001 else 'p<0.05' if omni[1]<0.05 else 'n.s.'})"
              f"   Bonferroni α=0.05/{bonf_n}")

    yoga_table("PANCHAMAHAPURUSHA YOGAS", maha_df, m_om, len(MAHA_KEYS))
    yoga_table("DHARMA KARMADHIPATI YOGAS", dk_df, d_om, len(DK_KEYS))
    print(f"\n  ✓ Bonferroni-corrected significant  · uncorrected p<0.05\n")
    print(f"{'═'*78}\n")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n",    type=int,  default=10000)
    ap.add_argument("--seed", type=int,  default=42)
    ap.add_argument("--out",  type=Path, default=Path("."))
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)

    print(f"\nRealistic Yoga Simulation v2  |  Target N={args.n:,}/group")

    print("Simulating LARGE CITY (high-intervention) births…")
    df_L=simulate_group(LARGE_CITIES,args.n,"large_city_high_intervention",
                        args.seed,HOUR_W_LARGE,DOW_W_LARGE)

    print("Simulating SMALL TOWN (biological circadian) births…")
    df_S=simulate_group(SMALL_CITIES,args.n,"small_town_biological",
                        args.seed+1,HOUR_W_SMALL,DOW_W_SMALL)

    pd.concat([df_L,df_S],ignore_index=True).to_csv(
        args.out/"realistic_births_v2.csv",index=False)

    maha_df = yoga_stats(df_L,df_S,MAHA_KEYS)
    dk_df   = yoga_stats(df_L,df_S,DK_KEYS)
    m_om    = omnibus_test(df_L,df_S,MAHA_KEYS)
    d_om    = omnibus_test(df_L,df_S,DK_KEYS)
    lc2,lp  = lagna_chi2(df_L,df_S)
    dts     = dt_summary(df_L,df_S)

    maha_df.to_csv(args.out/"realistic_maha_v2.csv",index=False)
    dk_df.to_csv(  args.out/"realistic_dk_v2.csv",  index=False)
    dts.to_csv(    args.out/"realistic_dt_v2.csv",  index=False)

    print_report(df_L,df_S,maha_df,dk_df,m_om,d_om,lc2,lp,dts)
    print(f"Files written to {args.out}/")

if __name__=="__main__":
    main()
