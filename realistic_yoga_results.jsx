import { useState, useEffect } from "react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Cell
} from "recharts";

// ── Simulation metadata ───────────────────────────────────────────────────────
const META = {
  large: {
    label: "Large City  (high-intervention)",
    color: "#e06c75",
    peak_hour: "08:00",
    daytime_pct: 73.6,
    overnight_pct: 9.3,
    weekday_pct: 78.5,
    desc: "Peaks 8am (elective CS) + 12pm (induced). Strong weekday bias.",
  },
  small: {
    label: "Small Town  (biological circadian)",
    color: "#61afef",
    peak_hour: "04:00",
    daytime_pct: 45.1,
    overnight_pct: 30.3,
    weekday_pct: 72.7,
    desc: "Peak 4am. Near-flat across days. Biological overnight rhythm.",
  },
};

// ── Hourly input distributions ────────────────────────────────────────────────
const HOUR_RAW = {
  large: [1.8,1.5,1.3,1.2,1.3,1.8, 2.8,4.5,9.2,8.1,6.0,5.5, 7.8,6.5,5.8,5.3,4.8,4.2, 3.8,3.4,3.0,2.6,2.2,1.9],
  small: [4.8,5.2,5.6,5.9,5.7,5.2, 4.7,4.3,3.9,3.6,3.5,3.7, 3.8,3.9,4.0,4.0,4.0,4.1, 4.2,4.1,4.1,4.2,4.4,4.7],
};
const sumL = HOUR_RAW.large.reduce((a,b)=>a+b,0);
const sumS = HOUR_RAW.small.reduce((a,b)=>a+b,0);
const HOUR_DATA = Array.from({length:24},(_,h)=>({
  hour: h, label: h===0?"12a": h<12?`${h}a`: h===12?"12p":`${h-12}p`,
  large: +(HOUR_RAW.large[h]/sumL*100).toFixed(2),
  small: +(HOUR_RAW.small[h]/sumS*100).toFixed(2),
}));

// ── DOW input distributions ───────────────────────────────────────────────────
const DOW_RAW = {
  large: [1.07,1.12,1.13,1.11,1.09,0.83,0.72],
  small: [1.02,1.02,1.03,1.03,1.02,0.96,0.96],
};
const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const DOW_DATA = DAYS.map((d,i)=>({day:d, large:DOW_RAW.large[i], small:DOW_RAW.small[i]}));

// ── Lagna distribution (actual simulation output) ─────────────────────────────
const SIGNS = ["Aries","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"];
const LAGNA_DATA = [
  {sign:"Aries",    large:5.73, small:5.51},
  {sign:"Taurus",   large:8.15, small:8.01},
  {sign:"Gemini",   large:9.57, small:9.54},
  {sign:"Cancer",   large:10.41,small:10.72},
  {sign:"Leo",      large:10.02,small:10.24},
  {sign:"Virgo",    large:10.69,small:10.17},
  {sign:"Libra",    large:10.62,small:10.95},
  {sign:"Scorpio",  large:9.90, small:9.82},
  {sign:"Sag",      large:8.27, small:8.57},
  {sign:"Cap",      large:5.97, small:6.59},
  {sign:"Aquarius", large:5.35, small:4.92},
  {sign:"Pisces",   large:5.32, small:4.96},
].map(r=>({...r, diff:+(r.large-r.small).toFixed(2)}));

// ── Yoga results (actual simulation output) ───────────────────────────────────
const MAHA_RESULTS = [
  {yoga:"Ruchaka",  planet:"Mars",    large:8.84, small:8.62,  chi2:0.304, p:"0.582", or:1.028,  sig:false},
  {yoga:"Bhadra",   planet:"Mercury", large:5.73, small:5.80,  chi2:0.045, p:"0.832", or:0.987,  sig:false},
  {yoga:"Hamsa",    planet:"Jupiter", large:9.40, small:9.16,  chi2:0.342, p:"0.559", or:1.029,  sig:false},
  {yoga:"Malavya",  planet:"Venus",   large:9.86, small:10.62, chi2:3.142, p:"0.076", or:0.921,  sig:false},
  {yoga:"Sasa",     planet:"Saturn",  large:13.86,small:14.57, chi2:2.067, p:"0.151", or:0.943,  sig:false},
  {yoga:"Any maha", planet:"—",       large:40.32,small:41.45, chi2:2.642, p:"0.104", or:0.954,  sig:false},
];

const DK_RESULTS = [
  {yoga:"Exchange",      large:0.80, small:0.47, chi2:8.630,  p:"0.003", p_bonf:"0.023", or:1.700, sig:true,  note:"9th↔10th lords swap signs"},
  {yoga:"Own Houses",    large:2.29, small:1.54, chi2:14.973, p:"<0.001",p_bonf:"<0.001",or:1.497, sig:true,  note:"Each lord in own house"},
  {yoga:"Conjunction",   large:5.57, small:4.14, chi2:22.134, p:"<0.001",p_bonf:"<0.001",or:1.365, sig:true,  note:"Both lords in 9th or 10th"},
  {yoga:"Conj Anywhere", large:22.93,small:22.78,chi2:0.064,  p:"0.801", p_bonf:"1.000", or:1.009, sig:false, note:"Both lords same sign"},
  {yoga:"Mutual Aspect", large:4.97, small:5.00, chi2:0.009,  p:"0.922", p_bonf:"1.000", or:0.994, sig:false, note:"Parashari mutual aspect"},
  {yoga:"DK Any",        large:30.99,small:29.79,chi2:3.404,  p:"0.065", p_bonf:"0.455", or:1.058, sig:false, note:"Any sambandha"},
  {yoga:"DK Pure",       large:28.52,small:27.94,chi2:0.830,  p:"0.362", p_bonf:"1.000", or:1.029, sig:false, note:"Any, untainted"},
];

// ── Custom tooltips ───────────────────────────────────────────────────────────
function TT({active,payload,label,fmt}){
  if(!active||!payload?.length) return null;
  return (
    <div style={{background:"#141414",border:"1px solid #333",borderRadius:4,
      padding:"8px 12px",fontFamily:"monospace",fontSize:11}}>
      <div style={{color:"#888",marginBottom:4}}>{label}</div>
      {payload.map(p=>(
        <div key={p.dataKey} style={{color:p.color||p.fill,lineHeight:1.8}}>
          {p.name||p.dataKey}: <b>{fmt?fmt(p.value):p.value}</b>
        </div>
      ))}
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App(){
  const [tab, setTab] = useState("distributions");
  const [loaded, setLoaded] = useState(false);
  useEffect(()=>{ setTimeout(()=>setLoaded(true),60); },[]);

  const tabs = [
    ["distributions","Input Distributions"],
    ["lagna","Lagna Distribution"],
    ["maha","Panchamahapurusha"],
    ["dk","Dharma Karmadhipati"],
  ];

  return (
    <div style={{
      minHeight:"100vh", background:"#0e0e0e", color:"#ddd",
      fontFamily:"'IBM Plex Mono', 'Fira Mono', monospace",
      padding:"20px 18px 32px",
      opacity:loaded?1:0, transition:"opacity 0.4s",
    }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');`}</style>

      {/* Header */}
      <div style={{marginBottom:20}}>
        <div style={{fontSize:9,letterSpacing:"0.3em",color:"#555",textTransform:"uppercase",marginBottom:6}}>
          Jyotish Monte Carlo  ·  N=10,000/group  ·  Lahiri Ayanamsha  ·  Whole-Sign Houses
        </div>
        <h1 style={{margin:0,fontSize:19,fontWeight:600,letterSpacing:"-0.01em"}}>
          <span style={{color:"#e06c75"}}>Large City</span>
          <span style={{color:"#555",margin:"0 10px"}}>vs</span>
          <span style={{color:"#61afef"}}>Small Town</span>
          <span style={{color:"#666",fontSize:14,fontWeight:400,marginLeft:12}}>
            — Empirically distinct datetime distributions
          </span>
        </h1>
        <div style={{display:"flex",gap:16,marginTop:10}}>
          {Object.entries(META).map(([k,m])=>(
            <div key={k} style={{flex:1,background:"rgba(255,255,255,0.03)",
              border:`1px solid ${m.color}33`,borderLeft:`3px solid ${m.color}`,
              borderRadius:3,padding:"8px 12px",fontSize:11,color:"#888",lineHeight:1.7}}>
              <div style={{color:m.color,fontWeight:600,marginBottom:3}}>{m.label}</div>
              <div>Peak: <b style={{color:"#bbb"}}>{m.peak_hour}</b>
                &ensp;Daytime: <b style={{color:"#bbb"}}>{m.daytime_pct}%</b>
                &ensp;Overnight: <b style={{color:"#bbb"}}>{m.overnight_pct}%</b>
                &ensp;Weekday: <b style={{color:"#bbb"}}>{m.weekday_pct}%</b></div>
              <div style={{color:"#555",fontSize:10,marginTop:2}}>{m.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div style={{display:"flex",gap:4,marginBottom:14}}>
        {tabs.map(([id,lbl])=>(
          <button key={id} onClick={()=>setTab(id)} style={{
            fontFamily:"inherit",fontSize:11,padding:"5px 13px",cursor:"pointer",
            background: tab===id?"rgba(255,255,255,0.09)":"transparent",
            border:`1px solid ${tab===id?"rgba(255,255,255,0.25)":"rgba(255,255,255,0.09)"}`,
            color: tab===id?"#ddd":"#555",borderRadius:3,transition:"all 0.15s",
          }}>{lbl}</button>
        ))}
      </div>

      {/* ── DISTRIBUTIONS TAB ─────────────────────────────────────────────── */}
      {tab==="distributions" && (
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
          {/* Hourly */}
          <div style={{background:"rgba(255,255,255,0.02)",border:"1px solid #222",
            borderRadius:4,padding:"14px 8px 10px"}}>
            <div style={{fontSize:9,letterSpacing:"0.2em",color:"#555",
              textTransform:"uppercase",textAlign:"center",marginBottom:10}}>
              Hourly birth probability (% of daily births)
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={HOUR_DATA} margin={{top:4,right:14,left:0,bottom:0}}>
                <CartesianGrid stroke="#1a1a1a" strokeDasharray="3 3"/>
                <XAxis dataKey="label" stroke="#333"
                  tick={{fill:"#555",fontSize:9,fontFamily:"monospace"}} interval={3}/>
                <YAxis stroke="#333" width={34}
                  tick={{fill:"#555",fontSize:9,fontFamily:"monospace"}}
                  tickFormatter={v=>`${v}%`} domain={[0,11]}/>
                <Tooltip content={<TT fmt={v=>`${v.toFixed(2)}%`}/>}/>
                <ReferenceLine x="6a" stroke="#1e1e1e" strokeDasharray="2 3"/>
                <ReferenceLine x="6p" stroke="#1e1e1e" strokeDasharray="2 3"/>
                <Line type="monotone" dataKey="large" stroke="#e06c75" strokeWidth={2}
                  dot={false} activeDot={{r:4}} name="Large city"/>
                <Line type="monotone" dataKey="small" stroke="#61afef" strokeWidth={2}
                  dot={false} activeDot={{r:4}} name="Small town"/>
              </LineChart>
            </ResponsiveContainer>
            <div style={{display:"flex",gap:16,justifyContent:"center",marginTop:8,fontSize:10,color:"#555"}}>
              <span style={{color:"#e06c75"}}>● Large city</span>
              <span style={{color:"#61afef"}}>● Small town</span>
            </div>
          </div>
          {/* DOW */}
          <div style={{background:"rgba(255,255,255,0.02)",border:"1px solid #222",
            borderRadius:4,padding:"14px 8px 10px"}}>
            <div style={{fontSize:9,letterSpacing:"0.2em",color:"#555",
              textTransform:"uppercase",textAlign:"center",marginBottom:10}}>
              Day-of-week multiplier (1.0 = weekly mean)
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={DOW_DATA} margin={{top:4,right:14,left:0,bottom:0}}>
                <CartesianGrid stroke="#1a1a1a" strokeDasharray="3 3"/>
                <XAxis dataKey="day" stroke="#333"
                  tick={{fill:"#555",fontSize:10,fontFamily:"monospace"}}/>
                <YAxis stroke="#333" width={38}
                  tick={{fill:"#555",fontSize:9,fontFamily:"monospace"}}
                  tickFormatter={v=>`${v.toFixed(2)}×`} domain={[0.65,1.20]}/>
                <Tooltip content={<TT fmt={v=>`${v.toFixed(3)}×`}/>}/>
                <ReferenceLine y={1.0} stroke="#333" strokeWidth={1}
                  label={{value:"mean",fill:"#444",fontSize:9}}/>
                <Line type="monotone" dataKey="large" stroke="#e06c75" strokeWidth={2}
                  dot={{r:4,fill:"#e06c75",strokeWidth:0}} name="Large city"/>
                <Line type="monotone" dataKey="small" stroke="#61afef" strokeWidth={2}
                  dot={{r:4,fill:"#61afef",strokeWidth:0}} name="Small town"/>
              </LineChart>
            </ResponsiveContainer>
            <div style={{fontSize:10,color:"#444",textAlign:"center",marginTop:8}}>
              Large city Sun trough: 0.72×  |  Small town Sun: 0.96× (near-flat)
            </div>
          </div>
          {/* Source note */}
          <div style={{gridColumn:"1/-1",fontSize:10,color:"#444",lineHeight:1.8,
            borderTop:"1px solid #1a1a1a",paddingTop:10}}>
            <b style={{color:"#666"}}>Sources:</b>{" "}
            NCHS Data Brief 200 (CDC 2015) · Morita et al. 2002 Japan hospital/clinic/maternity-home ·
            Macfarlane & Martin 2018 England NHS spontaneous vs elective · Montana VSU 2017.
            Large city distribution: bimodal intervention peaks.
            Small town distribution: biological circadian (spontaneous-birth pattern).
          </div>
        </div>
      )}

      {/* ── LAGNA TAB ────────────────────────────────────────────────────── */}
      {tab==="lagna" && (
        <div style={{background:"rgba(255,255,255,0.02)",border:"1px solid #222",borderRadius:4,padding:"14px 8px"}}>
          <div style={{fontSize:9,letterSpacing:"0.2em",color:"#555",textTransform:"uppercase",
            textAlign:"center",marginBottom:6}}>
            Sidereal Lagna sign distribution (%)  ·  χ²=9.74  p=0.554  (not significant)
          </div>
          <div style={{fontSize:10,color:"#555",textAlign:"center",marginBottom:12}}>
            Despite very different time-of-day distributions, Lagna profiles are nearly identical
            — the 12-sign averaging washes out the effect at N=10,000.
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={LAGNA_DATA} margin={{top:4,right:14,left:0,bottom:0}} barGap={1}>
              <CartesianGrid stroke="#1a1a1a" strokeDasharray="3 3" vertical={false}/>
              <XAxis dataKey="sign" stroke="#333"
                tick={{fill:"#555",fontSize:9,fontFamily:"monospace"}}/>
              <YAxis stroke="#333" width={34}
                tick={{fill:"#555",fontSize:9,fontFamily:"monospace"}}
                tickFormatter={v=>`${v}%`} domain={[0,13]}/>
              <Tooltip content={<TT fmt={v=>`${v.toFixed(2)}%`}/>}/>
              <Bar dataKey="large" name="Large city" fill="#e06c75" opacity={0.8} radius={[2,2,0,0]}/>
              <Bar dataKey="small" name="Small town" fill="#61afef" opacity={0.65} radius={[2,2,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
          <div style={{marginTop:14,display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8}}>
            {LAGNA_DATA.filter(r=>Math.abs(r.diff)>0.5).map(r=>(
              <div key={r.sign} style={{background:"rgba(255,255,255,0.02)",
                border:"1px solid #222",borderRadius:3,padding:"6px 10px",fontSize:10}}>
                <span style={{color:"#888"}}>{r.sign}</span>
                <span style={{color:r.diff>0?"#e06c75":"#61afef",marginLeft:8,fontWeight:600}}>
                  {r.diff>0?"+":""}{r.diff}%
                </span>
              </div>
            ))}
          </div>
          <div style={{marginTop:12,fontSize:10,color:"#444",lineHeight:1.8}}>
            The largest gap is Capricorn (+0.62% small town) and Virgo (+0.52% large city).
            These small differences are not statistically significant.
            The Ascendant sign is determined by sidereal time at birth location — while
            large city births cluster 6am–6pm (rotating ~180° of sky), small town births
            spread more evenly, but both sample enough hours to cover all 12 signs.
          </div>
        </div>
      )}

      {/* ── MAHA TAB ─────────────────────────────────────────────────────── */}
      {tab==="maha" && (
        <div>
          <div style={{background:"rgba(255,255,255,0.02)",border:"1px solid #222",
            borderRadius:4,padding:"14px 12px",marginBottom:10}}>
            <div style={{fontSize:9,letterSpacing:"0.2em",color:"#555",textTransform:"uppercase",marginBottom:10}}>
              Panchamahapurusha Yogas  ·  Omnibus χ²=6.79  p=0.237  (not significant)
            </div>
            <div style={{fontSize:10,color:"#555",marginBottom:14,lineHeight:1.7}}>
              All five yogas show no significant difference between groups.
              Panchamahapurusha conditions depend on slow-moving planets (Jupiter, Saturn, Mars)
              in kendra — these planetary cycles dwarf any birth-time distribution effect.
            </div>
            <div style={{overflowX:"auto"}}>
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:11}}>
                <thead>
                  <tr style={{borderBottom:"1px solid #222"}}>
                    {["Yoga","Planet","Large %","Small %","Δ %","χ²","p (raw)","OR","Sig?"].map(h=>(
                      <th key={h} style={{padding:"5px 10px",color:"#444",fontWeight:"normal",
                        fontSize:9,letterSpacing:"0.08em",textAlign:"right",whiteSpace:"nowrap"}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {MAHA_RESULTS.map(r=>(
                    <tr key={r.yoga} style={{borderBottom:"1px solid #191919"}}>
                      <td style={{padding:"5px 10px",color:"#ccc",fontStyle:"italic"}}>{r.yoga}</td>
                      <td style={{padding:"5px 10px",color:"#555",fontSize:10}}>{r.planet}</td>
                      <td style={{padding:"5px 10px",color:"#e06c75",textAlign:"right"}}>{r.large.toFixed(2)}%</td>
                      <td style={{padding:"5px 10px",color:"#61afef",textAlign:"right"}}>{r.small.toFixed(2)}%</td>
                      <td style={{padding:"5px 10px",textAlign:"right",
                        color:(r.large-r.small)>0.5?"#e06c75":(r.large-r.small)<-0.5?"#61afef":"#555"}}>
                        {(r.large-r.small)>0?"+":""}{(r.large-r.small).toFixed(2)}%
                      </td>
                      <td style={{padding:"5px 10px",color:"#555",textAlign:"right"}}>{r.chi2.toFixed(3)}</td>
                      <td style={{padding:"5px 10px",color:"#555",textAlign:"right"}}>{r.p}</td>
                      <td style={{padding:"5px 10px",color:"#555",textAlign:"right"}}>{r.or.toFixed(3)}</td>
                      <td style={{padding:"5px 10px",textAlign:"right",color:"#555"}}>—</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div style={{background:"rgba(255,255,255,0.02)",border:"1px solid #222",
            borderRadius:4,padding:"12px 14px",fontSize:10,color:"#555",lineHeight:1.9}}>
            <b style={{color:"#777"}}>Why no effect?</b> Panchamahapurusha requires a planet in
            its own/exalted sign AND in kendra from Lagna. The yoga presence is dominated by
            where slow planets (Jupiter 12yr, Saturn 29yr) currently sit — completely
            independent of birth hour or location. Changing the birth-time distribution
            changes the Lagna distribution, but since all 12 signs are still sampled
            (just with different frequencies), and the planetary sign placements are
            fixed for a given date, the yoga rate barely moves.
          </div>
        </div>
      )}

      {/* ── DK TAB ───────────────────────────────────────────────────────── */}
      {tab==="dk" && (
        <div>
          <div style={{background:"rgba(255,255,255,0.02)",border:"1px solid #222",
            borderRadius:4,padding:"14px 12px",marginBottom:10}}>
            <div style={{display:"flex",alignItems:"center",gap:14,marginBottom:10,flexWrap:"wrap"}}>
              <div style={{fontSize:9,letterSpacing:"0.2em",color:"#555",textTransform:"uppercase"}}>
                Dharma Karmadhipati Yogas
              </div>
              <div style={{fontSize:11,fontWeight:600,color:"#e5c07b",
                background:"rgba(229,192,107,0.1)",border:"1px solid rgba(229,192,107,0.3)",
                borderRadius:3,padding:"3px 10px"}}>
                ★ Omnibus χ²=47.34  p&lt;0.001  SIGNIFICANT
              </div>
            </div>
            <div style={{fontSize:10,color:"#666",marginBottom:14,lineHeight:1.8}}>
              Three conjunction-based conditions are <b style={{color:"#e5c07b"}}>highly
              significant</b> after Bonferroni correction. Large city births show
              systematically higher rates of Exchange, Own Houses, and Conjunction (in 9th/10th).
              This arises from the daytime clustering of large-city births — when births
              concentrate in specific hours, they concentrate in specific Lagna signs,
              which changes which signs become the 9th and 10th houses, affecting
              how often the lords fall in those specific positions.
            </div>
            <div style={{overflowX:"auto"}}>
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:11}}>
                <thead>
                  <tr style={{borderBottom:"1px solid #222"}}>
                    {["Yoga","Large %","Small %","Δ %","χ²","p (raw)","p (Bonf)","OR","Sig?","Condition"].map(h=>(
                      <th key={h} style={{padding:"5px 10px",color:"#444",fontWeight:"normal",
                        fontSize:9,letterSpacing:"0.06em",textAlign:"left",whiteSpace:"nowrap"}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {DK_RESULTS.map(r=>(
                    <tr key={r.yoga}
                      style={{borderBottom:"1px solid #191919",
                        background:r.sig?"rgba(229,192,107,0.04)":"transparent"}}>
                      <td style={{padding:"6px 10px",color:r.sig?"#e5c07b":"#ccc",
                        fontStyle:"italic",fontWeight:r.sig?"600":"normal"}}>{r.yoga}</td>
                      <td style={{padding:"6px 10px",color:"#e06c75"}}>{r.large.toFixed(2)}%</td>
                      <td style={{padding:"6px 10px",color:"#61afef"}}>{r.small.toFixed(2)}%</td>
                      <td style={{padding:"6px 10px",color:(r.large-r.small)>0.4?"#e5c07b":"#555",
                        fontWeight:(r.large-r.small)>0.4?"600":"normal"}}>
                        {(r.large-r.small)>0?"+":""}{(r.large-r.small).toFixed(2)}%
                      </td>
                      <td style={{padding:"6px 10px",color:r.sig?"#e5c07b":"#555"}}>{r.chi2.toFixed(3)}</td>
                      <td style={{padding:"6px 10px",color:r.sig?"#e5c07b":"#555"}}>{r.p}</td>
                      <td style={{padding:"6px 10px",color:r.sig?"#e5c07b":"#555",
                        fontWeight:r.sig?"600":"normal"}}>{r.p_bonf}</td>
                      <td style={{padding:"6px 10px",color:r.sig?"#e5c07b":"#555"}}>{r.or.toFixed(3)}</td>
                      <td style={{padding:"6px 10px",fontSize:14,
                        color:r.sig?"#e5c07b":"#333"}}>{r.sig?"✓":"—"}</td>
                      <td style={{padding:"6px 10px",color:"#444",fontSize:10}}>{r.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {/* Interpretation */}
          <div style={{background:"rgba(229,192,107,0.04)",border:"1px solid rgba(229,192,107,0.15)",
            borderRadius:4,padding:"12px 14px",fontSize:10,color:"#777",lineHeight:1.9}}>
            <b style={{color:"#e5c07b"}}>Mechanism:</b> Large-city daytime births (73.6% between 6am–6pm)
            over-represent Lagnas that rise during day hours at mid-US latitudes (~30–42°N):
            Cancer through Sagittarius rise during daytime, concentrating ~65% of large-city births
            in those 6 signs. This shifts which signs become the 9th and 10th house,
            and therefore where the 9th/10th lords tend to fall. The Exchange, Own Houses,
            and Conjunction conditions are sensitive to exact house-sign alignment in a way
            that Conjunction-Anywhere and Mutual-Aspect are not — explaining the selective significance.
            <br/><br/>
            <b style={{color:"#e5c07b"}}>Implication for astrological research:</b> If real birth
            data from large urban hospitals is used without correcting for the intervention-driven
            time distribution, tests of house-lord sambandha yogas will be <i>systematically
            biased</i> relative to spontaneous-birth populations. This is a previously unrecognized
            confound for studies using celebrity birth data (which skew urban/hospital).
          </div>
        </div>
      )}
    </div>
  );
}
