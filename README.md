Jyotish Birth Timing Research

Quantitative analysis of Vedic astrological yoga prevalence under empirically distinct birth-time distributions

A Python/statistical research toolkit examining whether yoga rates in Jyotish (Vedic astrology) differ systematically between large urban hospital births and small-town births — using distinct, literature-grounded birth-time distributions for each group rather than a single national average.

────────────────────────────────────────

Overview

Most Jyotish statistical research treats birth time as uniformly or randomly distributed. It is neither. Large urban hospitals in the United States and comparable countries exhibit strongly non-uniform birth timing driven by obstetric intervention (scheduled caesarean sections and induced labour), while births in small-town community hospitals and birth centres follow a near-biological circadian pattern. This project tests whether those distributional differences — compounded by geographic differences in latitude and longitude — produce detectable differences in yoga prevalence.

The answer turns out to depend entirely on which yoga system is examined.

────────────────────────────────────────

Key Finding

Panchamahapurusha yogas: No significant difference. These yogas depend on slow-moving planets (Jupiter 12-year cycle, Saturn 29.5-year cycle) occupying specific signs in angular houses. Planetary sign placements are determined by date, not hour or location, so the birth-time distribution has no meaningful effect.

Dharma Karmadhipati yogas: Three of seven conditions are highly significant after Bonferroni correction (omnibus χ²=47.34, p<0.001):

┌────────────────────────────┬────────────┬────────────┬──────┬────────────────┐
│ Condition                  │ Large city │ Small town │ OR   │ p (Bonferroni) │
├────────────────────────────┼────────────┼────────────┼──────┼────────────────┤
│ Sign exchange (parivartan) │ 0.80%      │ 0.47%      │ 1.70 │ 0.023          │
│ Own houses                 │ 2.29%      │ 1.54%      │ 1.50 │ <0.001         │
│ Conjunction in 9th/10th    │ 5.57%      │ 4.14%      │ 1.37 │ <0.001         │
└────────────────────────────┴────────────┴────────────┴──────┴────────────────┘


The mechanism: large-city daytime-clustered births (73.6% between 6am–6pm) over-represent the Lagna signs that rise during daylight hours at US mid-latitudes. This shifts the 9th and 10th house signs and therefore the frequency of exact positional alignments between their lords.

Research implication: Celebrity birth data — which skews heavily urban and hospital — carries a systematic Dharma Karmadhipati yoga bias relative to spontaneous-birth populations. This is a previously uncharacterized confound for Jyotish statistical research.

────────────────────────────────────────

Methods

Birth-time distributions

Two empirically distinct distributions are used, derived from published obstetric literature:

Large city (high-intervention):

•  Bimodal hourly pattern: peak at 08:00 (elective caesarean scheduling) and 12:00–13:00 (induced labour completions)
•  Day-of-week: Tue–Thu ~1.12× weekly mean; Sunday ~0.72×
•  73.6% of births between 6am–6pm; 9.3% overnight (0–5am)
•  Sources: NCHS Data Brief 200 (CDC 2015); Morita et al. 2002 (Japan, 1.2M births); Macfarlane & Martin 2018 (England NHS, 5M births)

Small town (biological circadian):

•  Unimodal pattern: peak at 04:00, gradual decline through day
•  Day-of-week: near-flat; maximum variation ±4%
•  45.1% daytime; 30.3% overnight
•  Sources: spontaneous-birth data from Macfarlane & Martin 2018; maternity home data from Morita et al. 2002; Montana VSU 2017

Geographic pools

Large cities (≥1M population): New York City, Los Angeles, Chicago, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Dallas, San Jose, Austin, Jacksonville. Hospital locations weighted by city population.

Small towns (<100K population): Flagstaff AZ, Cheyenne WY, Bismarck ND, Missoula MT, Pocatello ID, Burlington VT, Eau Claire WI, Bowling Green KY, Morgantown WV, Laramie WY, Prescott AZ, Yuma AZ, Texarkana TX, Brunswick GA.

Astrological calculations

•  Ayanamsha: Lahiri (Chitrapaksha), computed per Julian Date via pyswisseph
•  House system: Whole-sign throughout
•  Planets: seven classical grahas (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn)
•  Library: pyswisseph (Swiss Ephemeris Python bindings)

Statistical methods

•  Per-yoga 2×2 chi-square (Pearson, no Yates correction)
•  Bonferroni correction across all tests within each yoga system
•  Odds ratio with 95% Woolf CI
•  Cohen’s h effect size
•  Omnibus chi-square across yoga profile vectors

────────────────────────────────────────

Yoga Systems Implemented

Panchamahapurusha

Five yogas formed when Mars, Mercury, Jupiter, Venus, or Saturn is in its own or exaltation sign and in a kendra (houses 1, 4, 7, 10) from the Lagna. Additional tracking of Mercury combustion (within 12° of Sun).

┌─────────┬─────────┬─────────────────────────────┐
│ Yoga    │ Planet  │ Qualifying signs            │
├─────────┼─────────┼─────────────────────────────┤
│ Ruchaka │ Mars    │ Aries, Scorpio, Capricorn   │
│ Bhadra  │ Mercury │ Gemini, Virgo               │
│ Hamsa   │ Jupiter │ Cancer, Sagittarius, Pisces │
│ Malavya │ Venus   │ Taurus, Libra, Pisces       │
│ Sasa    │ Saturn  │ Libra, Capricorn, Aquarius  │
└─────────┴─────────┴─────────────────────────────┘


Dharma Karmadhipati

Seven sambandha (relationship) conditions between the lords of the 9th house (Dharmasthana) and 10th house (Karmasthana), as defined in Laghu Parashari and Kalidasa’s Uttara Kalamrita. Taint condition: 9th lord also rules the 8th (affects Gemini lagna only). Aspects use full Parashari system (universal 7th plus Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th).

Karmasthana (additional)

Four 10th-house yoga conditions from the Wikipedia Karmasthana article: Sankhya, Amla, Raja Yoga (10th-house type), and Karma Raja Yoga (Chandra-lagna variant).

────────────────────────────────────────

Repository Structure


big_city_dka/
│
├── README.md
│
├── data/
│   ├── cdc_natality_downloader.py      # Download CDC NCHS natality microdata
│   ├── us_hospitals_by_city_size.csv   # Hospital lat/lon for large and small cities
│   └── birth_timing_reference.csv      # Published hourly/DOW distributions by setting
│
├── simulation/
│   ├── realistic_yoga_v2.py            # Main simulation (recommended entry point)
│   ├── mahapurusha_analysis.py         # Panchamahapurusha standalone
│   ├── karmasthana_analysis.py         # Karmasthana standalone
│   └── dk_yoga_analysis.py             # Dharma Karmadhipati standalone
│
├── results/
│   ├── realistic_births_v2.csv         # 20,000 simulated birth records
│   ├── realistic_maha_v2.csv           # Panchamahapurusha statistics
│   └── realistic_dk_v2.csv             # Dharma Karmadhipati statistics
│
└── demo/
    ├── index.html                      # Netlify demo app
    └── src/
        └── App.jsx                     # React source



────────────────────────────────────────

Installation


# Clone
git clone https://github.com/your-username/jyotish-birth-timing.git
cd jyotish-birth-timing

# Install Python dependencies
pip install pyswisseph pandas numpy scipy tqdm

# Run main simulation (10,000 births per group)
python simulation/realistic_yoga_v2.py

# Run with custom parameters
python simulation/realistic_yoga_v2.py --n 5000 --out ./my_results

# Download CDC natality microdata (optional, for empirical validation)
python data/cdc_natality_downloader.py --years 2020 2021 2022 --summary-only



────────────────────────────────────────

Demo

An interactive results dashboard is deployed at: [your-demo.netlify.app]

Built with React and Recharts. Shows input distributions, Lagna breakdown, and significance tables for all yoga systems with tab navigation.

────────────────────────────────────────

Data Sources

Birth timing distributions:

•  Mathews & Curtin (2015). Time of Birth and Type of Delivery. NCHS Data Brief No. 200. CDC/NCHS.
•  Morita et al. (2002). Nationwide Description of Live Japanese Births by Day of the Week, Hour, and Location. Journal of Epidemiology 12(5):330–336.
•  Martin & Macfarlane (2018). Timing of singleton births by onset of labour and mode of birth in NHS maternity units in England, 2005–2014. PLoS ONE 13(6):e0198183.
•  Montana VSU (2017). Distribution of Deliveries Throughout the Day in Montana, 2012–2016.
•  Kozhimannil et al. (2014). Rural-urban differences in obstetric care, 2002–2010. Medical Care 52(1):4–9.

Astrological definitions:

•  Laghu Parashari. Gangavishnu Shrikrishnadas edition, 1947.
•  Kalidasa. Uttara Kalamrita. Ranjan Publications.
•  Mantreswara. Phaladeepika. Verses 6.37–38.
•  Wikipedia contributors. Karmasthana (astrology). Retrieved 2025.
•  Wikipedia contributors. Dharma Karmadhipati yoga. Retrieved 2025.

Ephemeris:

•  Astrodienst AG. Swiss Ephemeris. https://www.astro.com/swisseph/

────────────────────────────────────────

Prior Work

This project builds on the statistical methodology of:

│ Oshop, R. & Foss, C. (2015). An examination of Jaimini astrological kendra relationships in Twitter celebrity charts. Journal of Scientific Exploration 29(3).

The replication of that paper (including Monte Carlo simulation and statistical analysis) is included as context in the  simulation/  directory comments.

────────────────────────────────────────

Notes on Interpretation

These are Monte Carlo simulations using empirical datetime distributions as inputs. The geographic coordinates are real hospital locations; the individual birth records are synthetic. Results describe the expected yoga prevalence given the stated distributional assumptions — they are not claims about any specific individual’s chart.

The significant Dharma Karmadhipati findings should be interpreted as a methodological caution: studies comparing yoga prevalence across birth populations with different intervention rates will observe systematic differences in house-lord positional yogas independent of any astrological effect.

---

## License

MIT. See LICENSE.

## Citation

If you use this code or results in published research:

```
Oshop, R. (2026). jyotish-birth-timing: Yoga prevalence under empirically distinct
birth-time distributions. GitHub. https://github.com/renayo/big_city_dka
```
