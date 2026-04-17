---
title: "Time-Series InSAR Surface Deformation Analysis of Four Lithium Extraction Salars on the Puna Plateau"
author: "Timm Gönner"
author_profile: true
date: 2026-04-16
toc: true
toc_sticky: true
toc_label: "Time-Series InSAR Surface Deformation Analysis of Four Lithium Extraction Salars"
header:
  overlay_image: https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Llulleillaco_photo.jpg
  overlay_filter: 0.3
  caption: "Salar Arizaro with the stratovolcano Llullaillaco in the far background"
read_time: false
tags:
  - InSAR
  - LiCSBAS
  - Central Andes
  - Lithium Extraction
  - Surface Deformation
  - Salars 
---
Booming lithium demand is driving rapid brine extraction across the Andean salars—but its impact on ground stability remains largely unknown. Using a decade of satellite radar data, this study investigates whether subsidence observed at one site is part of a broader, region-wide response across the Lithium Triangle.

# Introduction

With the global rise in lithium demand for rechargeable battery
production, lithium mining in the high Andes has expanded significantly
over recent years (Vera et al., 2023; Trahey et al., 2020). The
extraction of lithium involves pumping large quantities of groundwater
to the surface where it is then evaporated (Vera et al. 2023), yet the
impact of this extraction on ground surface stability remains poorly
studied. Using satellite radar interferometry (InSAR), recent work has
shown that brine pumping at the Salar de Olaroz in northwest Argentina
produced up to 17 cm of localised subsidence (Lenardon et al., 2023).
Whether similar deformation is occurring at other salars across the
Lithium Triangle, the region containing an estimated 50-85% of the
world's continental lithium brine deposits (Vera et al., 2023), is an
open question.

To explore this, I used LiCSBAS2, an open-source Interferometric
Synthetic Aperture Radar (InSAR) time series analysis package that uses
pre-computed interferograms from the COMET-LiCS platform (Morishita et
al., 2020; COMET, 2026), to inspect four salars for surface displacement
between 2016 and 2026: Salar del Rincon, Salar de Olaroz, Salar de Aguas
Calientes II, and Salar de Llullaillaco (Fig. 1). These were
primarily selected by visual identification of solar evaporation ponds
in optical satellite imagery. The analysis was conducted during a
four-week internship in early 2026.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig1_2026-04-13_Overview_V3.png">
<figcaption><b>Figure 1:</b> Geographic overview of all salars in the study region. Salars that were studied in detail are outlined.</figcaption>
</figure>

*This internship was supervised by Prof. Dr. Bodo Bookhagen.*

# Regional Context

The Lithium Triangle spans areas of Argentina, Bolivia, and Chile
across the Altiplano-Puna Plateau - the central Andes - and the second-largest orogenic plateau
after Tibet (Allmendinger et al., 1997). Although the Altiplano and Puna
are sometimes used interchangeably, they both describe morphologically
different areas: the Bolivian Altiplano is a broad and flat region, while
the Argentine Puna is characterized by internal drainage with
reverse-fault-bounded basins and ranges (Allmendinger et al., 1997). On
average, the elevation of the plateau is around 3,750 m, formed
by non-collisional convergence between the Nazca and South American
plates at rates of around 10 cm per year (Pardo-Casas & Molnar, 1987;
Eckelmann et al., 2013).

The geological structural configuration consists of northwest to southeast trending reverse faults and east to west volcanic chains. This
combination creates the closed hydrological basins where salars formed at
the topographic low points. The only water discharge from the salars is
through evaporation, resulting in concentrations of dissolved metals
into hypersaline brines (Reidel, 2025).

In the region there are two primary types of salars: mature halitic
salars and immature clastic salars (Houston et al., 2011). Mature salars
have thick salt crusts that build up over long periods through transport
with evaporation of groundwater brines (Ruch et al., 2012). Because the
water table under the halite nucleus of mature salars is typically quite
shallow, continued halite crystal precipitation can cause the surface to
naturally uplift (Ruch et al., 2012). Immature clastic salars
are dominated by sediment input, such as sands or clay that are
transported in via alluvial fans or land slides. These salars have a
thinner halite crust and usually a lower developed brine system (Ruch et
al., 2012). This difference does influence the pattern interpretation
of the InSAR analysis, because actively growing salt bodies may show a
natural uplift, which may also mask some finer subsidence signals from
brine extraction.

The following sections will further elaborate on the applied methods and
showcase the results for each salar, followed by a discussion.

# Data and Methods

## Data

The InSAR time series analyses were carried out between
2015-2026, but not all data were used. The start date was
determined by the data availability of Sentinel 1 SAR scenes and
COMET-LiCS interferograms, which have been available since 2016 (COMET,
2026).

## Tools

COMET-LiCS provides EU Copernicus Sentinel-1 tiled InSAR products. These
interferograms are generally within two weeks of acquisition (COMET,
2026). For the InSAR time series analysis, LiCSBAS2, an open-source
Python and Bash package, was used to derive displacement time series and
velocity maps from the COMET-LiCS frames (Morishita et al., 2020). A
custom Bash pipeline was created to automate all steps of the LiCSBAS2
workflow for reproducibility and ease of repeated use. Post-processing
visualization and analysis were carried out in both QGIS and with Python
scripts.

## Processes

The LiCSBAS2 pipeline included all available processing steps, including
atmospheric correction using GACOS. Required manual inputs were the
frame ID, start and end dates, bounding box coordinates, multilook
factor, coherence filter value, and output directory. Simple error
handling logic was built in to prevent pipeline termination when GACOS
files were unavailable.

The vertical displacement (d_v) was derived from the cumulative
line-of-sight displacement (d_LOS) by dividing by the vertical component
of the unit LOS vector (U) on a per-pixel basis: d_v​=d_LOS​/U, where
U=cos⁡(θ_inc). This assumes negligible horizontal displacement at the
salars investigated, which could be validated in future work by
decomposing ascending and descending geometries.

For the displacement calculations and maps, rasters and .h5 files were
clipped to masks that were roughly hand-drawn along the visible borders
of the salars. This method is not the most precise and must be refined
in further work, using, for example, the USGS salar shapefiles
(Mihalasky et al., 2020).

## Parameters

For these LiCSBAS2 runs, the overall same parameters were applied. A
coherence filter of 0.2 was used, which in future work should be redone
and increased to at least 0.4, to ensure fewer artifacts are included in
the time series analysis. A multilook factor of 2 was used, as this
reduced phase noise, and improved coherence estimates. It was kept
relatively modest, as I wanted to retain finer spatial detail, to be
able to identify potential small-scale variations and influences of
features. The start and end dates were generally also the same, from
23.12.2015 to 24.12.2025, with the end date being limited by the time
the analyses were done earlier this year. Only Salar del Rincon had its
end date clipped to 2022, as the COMET-LiCS interferograms for that
frame were not available between 2022 and 2024 during the time of this
project.

The following frame was used for all salars except Rincon:
149A_11428_131313. For Rincon, the frame used was 083D_11452_131313.
Hence, Rincon was the only salar inspected with a descending frame.

# Salar Case Studies

In this section each inspected salar will be briefly presented with the
relevant observations and insights. The outputs include two primary
figures: a time series plot showcasing the vertical displacement
velocity over the observation period, and a map showcasing the spatial
vertical displacement rates of each salar. Aside from these velocity
visuals, the cumulative displacement values were also calculated and are
represented through various statistical metrics.

## Salar del Rincón

### Local Context

Salar del Rincón is located at approximately 3,730 m elevation in the
Puna region of the Salta Province, Argentina, within a closed basin
averaging 4,170 m. At roughly 30,000 ha, it is the largest salar by
surface area examined in this study and is estimated to hold the
second-largest lithium deposit in Argentina (mindat, 2025). The salar is
classified as a mature halitic salar, with a well-developed halite
nucleus and concentric evaporite zonation. The climate is hyperarid,
with mean annual precipitation of approximately 81 mm and high solar
radiation (Reidel, 2025).

The associated mining project, the Rincón West Project, is owned by
Argentina Lithium and Energy Corp. Since 2022, several exploratory
drilling campaigns have been conducted; however, no preliminary economic
assessment has been completed and no commercial-scale brine extraction
has taken place. Production is projected to begin in 2028 (Reidel,
2025). The InSAR observation period (2016-2022) therefore predates any
significant extraction activity, and the results serve as a pre-mining
baseline.

### Results

The Theil-Sen overall mean vertical velocity is -0.10 mm/yr (Fig. 2),
indicating near-zero net displacement over the observation period
(clipped to \<= 01.01.2022, due to data gap). There is a small
cumulative change of +2.10 mm from the first to the last epoch. A
piecewise linear fit identifies a breakpoint on 6 May 2020. Prior to
this date the trend is slightly negative (-1.64 mm/yr), while the
post-break segment shows a stronger uplift trend (+6.30 mm/yr). The
residual scatter around the piecewise trend is moderate (RMSE 5.25 mm)
and the sinusoidal fit captures an approximately annual periodic
component with an amplitude of 1.81 mm.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig2_2026-04-13_Rincon_TS.png">
<figcaption><b>Figure 2:</b> Vertical displacement time series plot for Salar del Rincón. The reference point is next to the salar at Lat: -23.952° S and Lon: -67.048° West.</figcaption>
</figure>

The displacement map (Fig. 3), shows that the retained signal
is concentrated along the salar margins and surrounding alluvial fans.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig3_2026-04-13_Rincon_map.png">
<figcaption><b>Figure 3:</b> Vertical displacement rate map for Salar del Rincón. Colormaps were centered on 0 and the reference point is next to the salar at Lat: -23.952° S and Lon: -67.048° West.</figcaption>
</figure>

### Interpretation

The near-zero net displacement and absence of a subsidence signal are
consistent with the pre-mining status of this salar. The seasonal
periodicity visible in the sinusoidal fit likely reflects cyclic
groundwater recharge and evaporation, a pattern also observed at other
salars in this study.

The data gap between 2022 and 2024 is a key limitation, as exploratory
drilling commenced in 2022 and any early-stage effects would not be
captured in this analysis.

## Salar de Olaroz

### Local Context

The Salar de Olaroz forms the northern portion of the Cauchari-Olaroz
salar complex, located at approximately 3,900 m elevation in the Jujuy
Province of northwest Argentina. The basin is structurally controlled by
north-south trending high-angle faults that form deep basins, cross-cut
by northwest-southeast trending lineaments (Burga et al., 2024). The
salar is classified as a mature halitic salar and is the only site in
this study with longer active commercial-scale lithium extraction during
the observation period.

The lithium extraction project is operated by Minera Exar S.A. a joint
venture company owned by Lithium Argentina (54.1%), Ganfeng Lithium Co.
Ltd. (37.4%), and the provincial state company Jujuy Energia y Mineria
Sociedad del Estado (JEMSE) (8.5%) (Burga et al. 2024). Exploration
began in 2009 and has included surface brine sampling, seismic and
gravity surveys, vertical electrical sounding, and multiple drilling
campaigns. Production brine pumping commenced in 2018 at the Cauchari
Salar, with extraction expanding into the Olaroz Salar from 2019 onward.
By 2020, the complex had 24 production wells, and brine production
increased by 70% in 2021 (Burga et al., 2024).

### Results

The Olaroz time series spans 2016 to late 2025 (395 epochs; 9.84 years)
and shows long-term subsidence (Fig. 4), the strongest deformation
signal of the four salars. The Theil-Sen trend estimate yields an
overall mean vertical velocity of -8.16 mm/yr, with a cumulative change
from the first to last epoch of -60.40 mm.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig4_2026-04-13_Olaroz_TS.png">
<figcaption><b>Figure 4:</b> Vertical displacement time series plot for Salar de Olaroz. The reference point is next to the salar at Lat: -23.379° S and Lon: -67.741° West.</figcaption>
</figure>

The piecewise linear fit identifies a breakpoint in mid-December 2020.
Prior to this breakpoint, the surface shows comparatively weak
subsidence of -1.35 mm/yr, which indicates near-stable behavior. After
the breakpoint, subsidence accelerates significantly and continues at an average
rate of -17.26 mm/yr. The residual scatter around the trend is higher
than for the other salars with a RMSE of 13.16 mm. The remaining annual
periodic signal is modest in comparison, with an amplitude of around
2.41 mm. The seasonal patterns may be overshadowed by the dominant
subsidence trend after 2020.

The displacement map (Fig. 5), reveals a distinct spatial
pattern: a concentrated subsidence bowl in the southern half of the
salar interior, reaching velocities below −32 mm/yr. The subsidence
signal diminishes radially outward, with the northern margins and
surrounding alluvial fans showing near-zero or slight positive
displacement.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig5_2026-04-03_Olaroz_vert.png">
<figcaption><b>Figure 5:</b> Vertical displacement rate map for Salar de Olaroz. Colormaps were centered on 0 and the reference point is next to the salar at Lat: -23.379° S and Lon: -67.741° West.</figcaption>
</figure>

### Interpretation

It is difficult to distinguish the precise start of brine
pumping at Olaroz, since the project documentation (Burga et al.,
2024) typically refers to the entire Cauchari-Olaroz complex, and not
Olaroz on its own. While the available data does not provide exact
pumping volumes, a circumstantial temporal basis for correlation is
strong, between the increase in well numbers and the onset of
accelerated subsidence.

Lenardon et al. (2023) reported up to 17 cm of localised subsidence at
this salar, based on observations ending in early October 2020. The
present analysis extends the record by five years and finds localised
subsidence reaching 27.5 cm at the final epoch. Whether the
pre-breakpoint signals are consistent between the two studies should be
verified more precisely in future work.

## Salar de Llullaillaco

### Local Context

Salar de Llullaillaco is located in the Puna region of the Salta
province in Argentina, at an average elevation of approximately 3,900 m,
southeast of one of the highest stratovolcanoes, named Llullaillaco. The
salar hosts the Mariana Project, operated by Litio Minera Argentina
S.A., a subsidiary of Ganfeng Lithium Group Co., Ltd. (Ganfeng Lithium
Latam, 2023). Although the first evaporation pond was filled as early as
January 2023 (Secretaria de Mineria, 2024), lithium mine production
formally began in 2025 (TNR Gold Corp., 2025), followed by the first
export of lithium chloride in February 2026 (Panorama Minero, 2026). The
observation period (2016--2025) therefore spans the transition from a
pre-mining baseline into the earliest stages of commercial extraction.

The extraction targets lithium-bearing brines at depths of 328 m or
greater, using a conventional pump-and-evaporation approach. Based on
the available information in the already cited sources, the salar
appears to be moderately mature, though detailed characterization
remains limited due to a lack of public information.

### Results

Llullaillaco shows a consistent gradual uplift over the full time series
(Fig. 6), accumulating around +21.6 mm from the first to last epoch. The
Theil-Sen trend estimate indicates an average uplift rate of +3.07 mm/yr
over the 9.84-year observation period (396 epochs).

The piecewise linear fit identifies a breakpoint around 23 May 2024.
Prior to this date, the AOI mean time series exhibits sustained uplift
at +3.29 mm/yr, whereas after the breakpoint the trend shifts to a
slight subsidence of -0.93 mm/yr. The piecewise model fits the AOI-mean
time series closely (RMSE 2.24 mm). The sinusoidal fit on the detrended
residuals suggests only a weak seasonal component, with an annual
amplitude of around 0.79 mm.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig6_2026-04-13_Llullaillaco_TS.png">
<figcaption><b>Figure 6:</b> Vertical displacement time series plot for the Salar de Llullaillaco. The reference point is next to the salar at Lat: -24.853° S and Lon: -68.245° West.</figcaption>
</figure>

The displacement map (Fig. 7) shows broadly positive velocities across
most of the salar interior, reaching up to approximately +9.6 mm/yr in
the central area. Coherence is retained over most of the salar surface,
providing good spatial coverage.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig7_2026-04-03_Llullaillaco_vert.png">
<figcaption><b>Figure 7:</b> Vertical displacement rate map for Salar de Llullaillaco. Colormaps were centered on 0 and the reference point is next to the salar at Lat: -24.853° S and Lon: -68.245° West.</figcaption>
</figure>

### Interpretation

The dominant positive displacement trend of around +3 mm/yr is consistent
with natural halite crust growth at a moderately mature salar (Ruch et
al., 2012). The breakpoint in May 2024 is noteworthy and may indicate the first influence of commercial lithium production. Although the
production only began in 2025, the evaporation-pond filling in January
2023 and preparatory brine abstraction may have commenced before the
formal production date, which may be directly linked to the change in
trends.

## Salar Aguas Calientes II

### Local Context

Salar Aguas Calientes II is named as such on the OSM Standard basemap,
however, the USGS salar shapefile identifies it as Salar de Aguas
Calientes. Because several salars in the region share this name, various
authors use the latitude (23°30' S) to distinguish this particular
basin. It was selected as a control site because it has no known lithium
extraction or other major anthropogenic activity, providing a reference
for natural baseline deformation against which the other salars can be
compared. However, due to limited publicly available information, this
assumption is based on optical satellite imagery and has not been
independently verified.

The salar is located at an average altitude of approximately 4,220 m,
roughly halfway between Salar de Atacama and Salar de Olaroz in Chile.
Geomorphological evidence points to a formerly wetter paleoclimate, with
a paleolake having overflowed into the basin. Current erosion features
and spring activity along the western margin suggest active groundwater
processes that could influence seasonal displacement signals (Stoertz &
Ericksen, 1974).

### Results

The time-series for Aguas Calientes (Fig. 8) indicates a continuous
steady increase in vertical displacement rates over the 9.84 year
observation period (395 epochs). A Theil-Sen trend estimate yields an
average vertical velocity of +2.22 mm/yr, with a RMSE of 5.10 mm, and a
cumulative increase of +19.63 mm from the first to last epoch. A
piecewise linear model identifies a breakpoint on 29 December 2018.
Prior to this date, the deformation is characterized by a slight
negative trend (-0.72 mm/yr), while the post-breakpoint segment exhibits
sustained uplift at +2.62 mm/yr. The sinusoidal fit captures an annual
periodic signal that appears relatively stable.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig8_2026-04-13_Calientes_TS.png">
<figcaption><b>Figure 8:</b> Vertical displacement time series plot for Salar de Aguas Calientes. The reference point is next to the salar at Lat: -23.429° S and Lon: -67.499° West.</figcaption>
</figure>

The displacement map (Fig. 9) shows velocities with a maximum of +3.6
mm/yr. In it are two major clusters of predominantly larger positive
velocities, while some marginal areas show near-zero or
slightly negative values. A localised anomaly is visible on the western
margin, potentially spatially coinciding with the spring activity area
noted by Stoertz & Ericksen (1984).

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig9_2026-04-03_Calientes_vert.png">
<figcaption><b>Figure 9:</b> Vertical displacement rate map for Salar de Aguas Calientes. Colormaps were centered on 0 and the reference point is next to the salar at Lat: -23.429° S and Lon: -67.499° West.</figcaption>
</figure>

### Interpretation

Aguas Calientes displays the clearest example of a natural baseline
deformation signal among the four salars in this study. The steady +2.22
mm/yr trend, absence of any known anthropogenic disturbance, and
spatially uniform positive displacement across the salar interior are
consistent with gradual halite crust growth driven by evaporation of
shallow groundwater and ongoing salt precipitation (Ruch et al., 2012).
Without pre-2016 deformation data, it is difficult to determine whether
the breakpoint in December of 2018 represents a longer-term change in
trends or an anomaly.

As a control site with no brine extraction, the natural uplift rate
observed here provides a useful comparison. The similarity to
Llullaillaco's pre-mining uplift rate (+3.07 mm/yr) suggests that
low-magnitude positive displacement is a common natural background
process at Puna salars, against which extraction-induced subsidence, as
observed at Olaroz, can be distinguished.

# Discussion

## Compare and Contrast

As seen in Fig. 10 and Table 1 below, the three salars without full
commercial-scale extraction, all show low-magnitude positive
displacement, while the Salar de Olaroz, with productive brine pumping,
shows significant subsidence.

<figure>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/TimmGoenner_figures/Fig10_2026-04-13_Combined_TS.png">
<figcaption><b>Figure 10:</b> Combined vertical displacement time series with all salars.</figcaption>
</figure>

<center>
<b>Table 1:</b> Statistical comparison table.
| Salar              | Velocity (mm/yr)   | Cumulative (mm)   | Breakpoint   | Extraction status |
| ------------------ | ------------------ | ----------------- | ------------ | --------------------------- |
| Rincón             | -0.10              | +2.10             | May 2020     | Pre-mining (est. 2028) |
| Olaroz             | -8.16              | −60.40            | Dec 2020     | Active since \~2018--2020 |
| Llullaillaco       | +3.07              | +21.60            | May 2024     | Production began 2025 |
| Aguas Calientes    | +2.22              | +19.63            | Dec 2018     | None (control) |

</center>

The non-full-commercial-extracting salars all show positive displacement
at rates within Ruch et al. (2012)'s observed rates of natural halite
crust growth at mature salars in the Atacama desert. This growth likely
comes from capillary halite precipitation due to solar driven
evaporation that draws salty groundwater though the permeable halite
mass, and is therefore often the default state of salars.

The subsidence at Olaroz is significantly larger than any natural signal
observed at the other salars. It also appears to correlate temporally
with the increase of production wells between 2019-2021. Which strongly
suggests a significant impact of the groundwater extraction on the
surface deformation of salars.

## Seasonal Signals

All four salars show some annual patterns, but amplitude varies strongly
and can be overshadowed by long-term trends (notably at Olaroz). The
likely driver is the wet and dry seasonal cycle that leads to seasonal
inflation and subsidence. Of the salars, Rincón and Aguas Calientes show
the closest seasonal match. Further details regarding seasonal signals
haven't been explored, such as correlation to climatic events, or
influences of other parameters on the seasonal amplitude. These seasonal
patterns, particularly for the shorter time series at Rincón, may
strongly influence velocity estimates.

## Limitations

Several limitations affect the data, processing, and interpretation of
this study and should be considered when evaluating the results.

### Data

The COMET-LiCS interferograms for Salar del Rincón were unavailable
between 2022 and 2024, producing the shortest time series of the four
sites and preventing any observation of the period in which exploratory
drilling began. Furthermore, all salars except Rincón, descending, were
processed using a single ascending track, meaning that any horizontal
displacement component is projected into the vertical estimate rather
than being independently resolved.

### Processing

A coherence threshold of 0.2 was applied, which is lower than the
commonly recommended minimum of 0.4 and may allow phase-noise artefacts
to enter the time series. This may have led to some of the extreme
outliers in the displacement values.

Salar boundaries were drawn by hand
rather than with a standardised method (e.g. USGS salar polygons),
introducing imprecision in the area statistics. Finally, the
LOS-to-vertical conversion assumes negligible horizontal displacement,
which has not been validated with independent data.

### Interpretation

Exact brine pumping start dates for the salars could not be determined,
as project documentation is typically quite broad in their reporting.
Therefore the temporal correlation remains circumstantial. Furthermore,
most of the studied salars have not yet entered commercial-scale
extraction during the observation period, limiting the ability to detect
extraction-induced trend changes. Additionally, although the 9 year
observation period exceeds that of earlier InSAR studies, it remains
relatively short to long-term geological and hydrological cycles that
may influence salar surface dynamics. Finally, the assumption that Aguas
Calientes is free of anthropogenic influence was based on optical
satellite imagery and has not been independently verified.

## Future Work

### Immediate Improvements

The LiCSBAS2 pipeline should be re-run for all salars with a coherence
threshold of at least 0.4 to reduce phase-noise artefacts. Salar
boundaries should be redefined using USGS salar shapefiles in place of
the current hand-drawn masks, improving the precision and
reproducibility of areal statistics. The COMET-LiCS data catalogue for
the Rincón frame should be revisited to determine whether the
interferograms covering the 2022-2024 gap have since become available;
if so, the time series should be extended to capture the period in which
exploratory drilling commenced.

### Geometry Decomposition

Where reasonable, both ascending and descending-track data should be
incorporated for all salars to decompose the line-of-sight signal into
separate vertical and horizontal displacement components, removing the
current reliance on the assumption of negligible horizontal motion.

### Continued Monitoring

Salar de Llullaillaco is a particularly important target for ongoing
observation: commercial brine extraction only began in 2025, and the
pre-mining uplift baseline established in this study (+3.07 mm/yr)
provides a clear reference against which any future extraction-induced
subsidence can be detected. Continued InSAR monitoring through
2026-2028, as production volumes increase, could be informative.

### Validation and Extension

The InSAR-derived displacement fields should be compared with
independent geodetic measurements (e.g. GNSS or levelling data) where
available, to validate both the magnitude and direction of the observed
signals. Finally, the study should be extended to additional salars
across the Lithium Triangle that already have multi-year histories of
active brine extraction, enabling a more robust assessment of the
relationship between pumping intensity and surface subsidence.

# Conclusion

This project used LiCSBAS2 InSAR time series analysis to investigate
surface deformation at four salars in the Altiplano-Puna region between
2016 and 2025. Three of the four sites - Salar del Rincón (-0.10 mm/yr),
Salar de Llullaillaco (+3.07 mm/yr), and Salar Aguas Calientes (+2.22
mm/yr) - exhibit low-magnitude deformation consistent with natural halite
crust growth dynamics. Salar de Olaroz, the only site with longer active
commercial-scale brine extraction shows mean
cumulative subsidence of -60.40 mm and surface deformation velocity of -8.16 mm/yr. The
substantial deformation trend temporally appears to correlate with the
increase of production wells from 2020 onward. This contrast, and the sudden change in trend trajectory, strongly
suggests that groundwater extraction for lithium production is the
dominant driver of the subsidence observed at Olaroz. The results extend
the findings of Lenardon et al. (2023) by several years and confirm that
subsidence has continued and likely accelerated since their study period
ended.

With commercial extraction increasing in the region, the pre-mining
uplift baseline for several salars provides a reference for detecting
future extraction-induced subsidence. Continued InSAR monitoring across
the Lithium Triangle, combined with the improvements and validation
methods outlined in this work, will be essential to understand the
broader environmental consequences of lithium brine extraction on salar
surface stability and perhaps the regional hydrological systems.

## Acknowledgements

This internship was supervised by Prof. Dr. Bodo Bookhagen.

# Bibliography

Allmendinger, R., Jordan, T.E., Kay, S.M. and Isacks, B.L. (1997). The evolution of the Altiplano-Puna Plateau of the Central Andes, Annual Review of Earth and Planetary Sciences Volume 25.

Burga, E.; Burga, D.; Weber, D.; Sanford, A.; Dworzanowski, M. (2024).
NI 43 - 101 Technical Report Operational Technical Report at the
Cauchari-Olaroz Salars, Jujuy Province, Argentina. Lithium Argentina.

COMET (2026). COMET-LiCS Sentinel-1 InSAR portal.
[https://comet.nerc.ac.uk/COMET-LiCS-portal/](https://comet.nerc.ac.uk/COMET-LiCS-portal/)

Eckelmann, F.; Motagh, M.; Bookhagen, B.; Strecker, M. (2013). InSAR
Observations of Crustal Deformation Mechanics in the Interior of the
Puna Plateau of the Southern Central Andes.

Ganfeng Lithium Latam (2023) The Mariana project.
[https://ganfenglithium-latam.com/en/proyecto-mariana/](https://ganfenglithium-latam.com/en/proyecto-mariana/)

Houston, J.; Butcher, A.; Ehren, P.; Evans, K.; Godfrey, L. (2011) The
Evaluation of Brine Prospects and the Requirement for Modifications to
Filing Standards. Economic Geology.
[https://doi.org/10.2113/econgeo.106.7.1225](https://doi.org/10.2113/econgeo.106.7.1225)

Lenardon, M.; Farias, C.A.; Seppi, S.A.; Carignano, C.A. (2023). Terrain
subsidence in the Salar de Olaroz (Jujuy, Argentina) caused by
lithiferous brine extraction, detected by multi-temporal SAR
interferometry. <https://doi.org/10.1109/RPIC59053.2023.10530767>

Mihalasky, M.J.; Briggs, D.A.; Baker, M.J.; Jaskula, B.; Cheriyan, K.;
Deloach-Overton, S.W. (2020). Lithium Occurrences and Processing
Facilities of Argentina, and Salars of the Lithium Triangle, Central
South America. Geology, Minerals, Energy, and Geophysics Science
Center. [10.5066/P9RLUH4F](https://doi.org/10.5066/P9RLUH4F)

Mindat (2025) Salar del Rincón, San Antonio de los Cobres, Los Andes
department, Salta province, Argentina.
[mindat.org](http://mindat.org/).
[https://www.mindat.org/loc-264868.html](https://www.mindat.org/loc-264868.html)

Morishita, Y.; Lazecky, M.; Wright, T.J.; Weiss, J.R.; Elliott, J.R.;
Hooper, A. LiCSBAS: An Open-Source InSAR Time Series Analysis Package
Integrated with the LiCSAR Automated Sentinel-1 InSAR Processor. Remote
Sens. 2020, 12, 424,[
](https://doi.org/10.3390/RS12030424)[https://doi.org/10.3390/RS12030424](https://doi.org/10.3390/RS12030424)

Panorama Minero (2026) Ganfeng Completed Its First Export: "Lithium From
Salta to the World!", a Milestone for Argentine Mining.
[https://www.panorama-minero.com/en/news/ganfeng-completed-its-first-export-lithium-from-salta-to-the-world-a-milestone-for-argentine-mining](https://www.panorama-minero.com/en/news/ganfeng-completed-its-first-export-lithium-from-salta-to-the-world-a-milestone-for-argentine-mining)

Pardo-Casas, F.; Molnar, P. (1987). Relative motion of the Nazca
(Farallon) and South American Plates since Late Cretaceous time.
Tectonics. Vol. 6, Issue 3, pp. 233-248.
[https://doi.org/10.1029/TC006i003p00233](https://doi.org/10.1029/TC006i003p00233)

Reidel, F. (2025). NI 43-101 Technical Report: Lithium Resource
Estimate, Rincón West Project. Atacama Water.

Ruch, J.; Warren, J.K.; Risacher, F.; Walter, T.R.; Lanari, R. (2012).
Salt lake deformation detected from space. Earth and Planetary Science
Letters. [https://doi:10.1016/j.epsl.2012.03.009](about:blank)

Secretaría de Minería (2024) Portfolio Lithium. Buenos Aires:
Ministerio de Economía, República Argentina. Available at:[
](https://www.argentina.gob.ar/sites/default/files/portfolio_lithium_2024.pptx.pdf)[https://www.argentina.gob.ar/sites/default/files/portfolio_lithium_2024.pptx.pdf](https://www.argentina.gob.ar/sites/default/files/portfolio_lithium_2024.pptx.pdf)

Stoertz, G.E. and Ericksen, G.E. (1987). Geology of Salars in Northern
Chile. U.S. Geological Survey Professional Paper 811, 65 p.
<https://doi.org/10.3133/pp811>

TNR Gold Corp. (2025) TNR GOLD CORP.
[https://tnrgoldcorp.com/](https://tnrgoldcorp.com/)

Vera, M.L.; Torres, W.R.; Galli, C.I.; Changes, A.; Flexer, V. (2023).
Environmental impact of direct lithium extraction from brines. Nature
reviews, earth & environment.
[https://doi.org/10.1038/s43017-022-00387-5](https://doi.org/10.1038/s43017-022-00387-5)

Trahey, L.; Brushett, F.R.; Balsara, N.P.; Ceder, G.; Cheng, L.; Chiang,
Y.; Hahn, N.T.; Ingram, B.J.; Minteer, S.D.; Moore, J.S.; Mueller, K.T.;
Nazar, L.F.; Persson, K.A.; Siegel, D.J.; Xu, K.; Zavadil, K.R.;
Srinivasan, V.; Crabtree, G.W. (2020) Energy storage emerging: A
perspective from the Joint Center for Energy Storage Research, Proc.
Natl. Acad. Sci. U.S.A. 117 (23) 12550-12557,[
](https://doi.org/10.1073/pnas.1821672117)[https://doi.org/10.1073/pnas.1821672117](https://doi.org/10.1073/pnas.1821672117).
