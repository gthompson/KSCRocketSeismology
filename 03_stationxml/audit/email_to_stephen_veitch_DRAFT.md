To: Stephen Veitch (EarthScope EPIC Data Group)
Cc: epic.data.group
Subject: Rocket Seis // 201850 // 1R.2016--2023 // corrected StationXML (responses) and BHP8 2019 duplicates
Attach: 03_stationxml/KSC_1R_2016-2022.xml

Hi Stephen,

I've been auditing the KSC network metadata against the waveform data, and the StationXML I sent you on 2025-11-12 has some response errors. The data already archived under 1R_2016 (the PASSCAL RT130 stations) are affected. A corrected file is attached (1R and AM, 2016-2022, 192 channel epochs). It passes stationxml-validator 1.7.5.

What changed, for the stations you hold data for:

1. RT130 + L-22 geophones (BHP1-8, FIREP, and the other EH? stations): the overall sensitivity is 44.7x higher than in the archived metadata.
   - The RT130 preamp gain was 32, not 1. This is confirmed by the PASSCAL config files and by comparing each geophone with a co-located Trillium Compact across 68 launches.
   - The L-22D generator constant is 88 V/(m/s) (unshunted), not the NRL's 62.95. With 32 and 88 the geophones match the Trilliums to about 5%.
   - With the archived metadata, these data convert to ground velocities about 45x too high.
   - The poles and zeros are unchanged from the NRL L-22D (10854 Ohm shunt) entry. Can PASSCAL tell me whether our L-22s had damping shunts fitted?

2. BHP8 2019:100-176: these files are not BHP8. They come from DAS 9BC5 after it was moved to BHP7. Days 101-176 are identical to BHP7.10; day 100 (the install day at BHP7) is now BHP7.10 too, and BHP7.10 starts 2019-04-10. The new metadata ends BHP8 on 2019-02-13. Could you withdraw the BHP8 2019:100-176 days from the archive? I can send BHP7.10 2019:100 if you want it. The 2019:039-043 BHP8 days, BHP3 2019:035 and BHP5.10 2019:183 that you flagged are all now covered by the corrected epochs.

3. Centaur stations (not yet uploaded, but in the metadata), for your information:
   - infrasound channels at DVEL1-3, RBLAB and BCHH3 (to 2022-05-26) were recorded at 1 Vpp, not 40;
   - SON2 DD4-6 in 2017 were at 40 Vpp, not 1;
   - Chaparral M25 channels have been added (BCHH1 DD1, BCHH3 HDF, BCHH4 HDF);
   - a low-sensitivity infraBSU at BCHH in early 2016 now has a measured correction;
   - channel comments now record the input range, sensor and evidence for each epoch.

On your question about stations that share coordinates:
- JPK1 & JPK2: [GLENN]
- R1E5E, R37BE, RB268, RB383, RBLAB, RC304, RCD29: [GLENN]
- BHP7 & BHP8, BHP5 & BHP6, BHP3 & BHP4: yes, deliberately. Each pair was co-located (within 2-3 m) as a huddle test along the BHP linear array, so the near-identical coordinates are correct.
- BCHH1, BCHH3, BCHH4, SON1 and BCHH2 & SON2: [GLENN — same site, different instrument sets?]
- S39A1 & S39A3: [GLENN]

Could you replace the 1R_2016 metadata with the attached file, or tell me the best way to submit a revision? I'll send the USF (Centaur) station data once the catalog paper is submitted, as we discussed.

Thanks!
Glenn
