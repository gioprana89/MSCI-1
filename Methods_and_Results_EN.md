# Stock Market Reactions to MSCI Index Review Announcements

*Evidence from the November 2026 review of Indonesian equities*

**Working manuscript · Methods and Results · Post-pilot exploratory analysis**

## Methods

### Event, universe and sample

MSCI announced the November 2026 Index Review on 11 November at 22:04 UTC, corresponding to 05:04 Western Indonesian Time on 12 November, before the Jakarta market opened. The Indonesian changes affected nine stocks. BRPT left Standard, BRMS moved from Standard to Small Cap, and AVIA, CTRA, EMTK, JSMR, MTEL, RAJA and WIFI left Small Cap. The analysis uses 12 November as event day zero. The sessions on 11 and 13 November are reported descriptively. MSCI scheduled implementation for the 30 November close, after the end of the available stock panel. [MSCI announcement](https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=t6TJpGLKQvg%3D) · [Standard list](https://www.msci.com/eqb/gimi/stdindex/MSCI_Nov26_STPublicList.pdf) · [Small Cap list](https://www.msci.com/eqb/gimi/smallcap/MSCI_Nov26_SCPublicList.pdf)

The source workbook contains 147,044 stock-day observations, 965 ticker codes, and 153 exchange sessions from 1 April to 13 November 2026. Stock characteristics and model parameters use the 120 sessions from 17 April through 14 October, before the separate MSCI country-classification consultation announcement. The Composite Index (IHSG) series uses IDX monthly statistics for April–October and recorded secondary sources for November. The November index levels still require reconciliation against the complete official IDX series.

### Comparison stocks

Initial matches prioritized the same three-character IDX-IC industry and then the same one-character sector. The distance was Euclidean across standardized log median capitalization and log-transformed median turnover. Both features had a 1.5-standard-deviation caliper. A second candidate set excluded stocks whose MSCI Standard or Small Cap membership changed in the May or August reviews.

The screened specification considered the original candidate order followed by the alternate order, removed duplicates, and retained up to three controls per affected stock. We excluded retained Standard or Small Cap constituents reported in the contemporary list, candidates in the 11 November HSC notice, identified affiliated pairs, identified concurrent issuer disclosures, and candidates with mechanical event-window flags. The mechanical checks covered missing sessions, zero volume, reference-price resets and changes in listed shares. The public-source screen could not establish complete issuer disclosures, ownership relationships, or index-weight changes. As a result, the comparison set remains subject to verification. [Reported MSCI list](https://market.bisnis.com/read/20261112/7/2020860/ini-daftar-35-saham-ri-yang-tersisa-di-msci-usai-rebalancing-november-2026) · [Reproduced IDX–KSEI HSC notice](https://finance.detik.com/bursa-dan-valas/d-8749154/daftar-lengkap-383-saham-hsc-yang-didepak-dari-perhitungan-ihsg)

### Outcomes and historical reference

We calculate stock price returns relative to each session's IDX reference price and estimate expected returns from a stock-specific OLS market model with IHSG returns. Matched abnormal return is the affected stock's residual less the equally weighted mean residual of its controls. Turnover and net foreign trading are scaled by listed shares and centered on each stock's historical median before taking the difference from the controls. The portfolio estimate gives equal weight to each affected stock, including when an individual control is reused across matches.

For the historical benchmark, we evaluate each of the 120 baseline dates using a market model and medians estimated from the 100 sessions outside its contiguous 20-session block. All stocks and controls share the same placebo date. For each outcome, we report the historical two-sided tail rank, calculated as one plus the number of placebo estimates at least as large in absolute value as the announcement-day estimate, divided by one plus the number of placebo dates. The ranks describe historical extremeness. Serial dependence, time-varying volatility, and differences between the event and placebo training samples limit inferential interpretation. The rank estimates are exploratory and the historical quantiles describe the placebo distribution. [MacKinlay (1997)](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf) · [Kolari and Pynnönen (2010)](https://doi.org/10.1093/rfs/hhq072)

## Results

The two candidate sets contained 31 unique comparison codes. The public screen identified six reported retained MSCI constituents, seven HSC candidates, and two affected–control affiliation links. MEDC's regular-market ex-dividend date was 11 November, and WIRG disclosed AGM results on 12 November. Neither issuer was selected in the screened set. There were no mechanical event-window flags for the 40 reviewed securities. Screening retained 17 affected–control links, 14 unique control stocks and all nine affected stocks. Four affected stocks had a single control. Historical correlation between affected stocks and their screened donor portfolios ranged from −0.005 to 0.623, showing uneven pre-event comparability. [KSEI dividend notice](https://web.ksei.co.id/Announcement/Files/MEDC_DIV_20261112_ID.pdf) · [WIRG disclosure index](https://jejaksaham.id/pengumuman?k=rups&t=WIRG)

### Announcement-day estimates

| Outcome | Mean | Median | Stocks below zero | Placebos at least as extreme | Historical tail rank |
|---|---:|---:|---:|---:|---:|
| Matched abnormal return, percentage points | −3.260 | −2.340 | 9/9 | 3/120 | 0.033 |
| Matched abnormal turnover, bp of listed shares | +62.219 | +2.155 | 3/9 | 0/120 | 0.008 |
| Matched net foreign trading deviation, bp of listed shares | −4.132 | −2.604 | 6/9 | 7/120 | 0.066 |

The matched abnormal return was negative for all nine affected stocks. The mean remained negative with the original comparison set (−3.409 percentage points) and the May/August exclusion set (−3.624). Removing the Standard-to-Small Cap migration BRMS yielded −3.498. Removing MTEL, which appeared on the HSC list, reduced the mean to −2.880 and raised the historical tail rank from 0.033 to 0.091. Single-stock exclusions yielded mean return estimates between −3.655 and −2.562 percentage points.

The mean abnormal turnover of 62.219 basis points exceeded every historical placebo in absolute value. The median was 2.155 basis points. RAJA and WIFI contributed about 90% of the net aggregate gap. Removing both reduced the mean to 8.171 basis points and raised the historical tail rank to 0.256. The direction of mean net foreign trading could reverse under single-stock exclusion, so the foreign-trading result is treated as tentative.

The screened mean matched abnormal return was 0.287 percentage points on 11 November and 2.906 on 13 November. The vice president's resignation was reported on 12 November and the domestic HSC-related IHSG adjustment took effect on 13 November. These overlapping events limit attribution and the interpretation of the next-session increase. The estimates document relative market reactions around the review announcement. The foreign-trading variables aggregate transactions by foreign investors and do not identify index funds. [Cabinet Secretariat](https://setkab.go.id/en/president-prabowo-accepts-the-resignation-of-vice-president-gibran/) · [HSC adjustment](https://finance.detik.com/bursa-dan-valas/d-8750118/383-saham-hsc-tak-masuk-perhitungan-ihsg-mulai-hari-ini)

### Figures

1. **Stock reactions on the MSCI announcement day.** Three panels show screened matched estimates for each affected stock on 12 November.
2. **Announcement-day estimates and historical placebos.** The vertical line shows the observed portfolio estimate. Histograms show the 120 synchronous historical estimates.
3. **Trading around the November announcement.** The line graphs show the three available event-window sessions. The 13 November observations coincide with the domestic HSC-related adjustment.

## Before submission

Confirm remaining constituent weights, issuer disclosures, and the complete November IHSG levels. Extend the literature audit with a direct Scopus query and citation tracking. The *International Review of Finance* scope covers market microstructure and Asia-Pacific emerging markets. Its Letters section provides a format to assess for this single-episode study. Compare with recent papers and verify active coverage by ISSN through Scopus Sources at submission. [Wiley scope](https://onlinelibrary.wiley.com/page/journal/14682443/homepage/productinformation.html) · [Scopus Sources guide](https://www.elsevier.support/scopus/answer/how-do-i-use-the-scopus-sources-feature)
