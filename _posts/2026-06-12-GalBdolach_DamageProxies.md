---
title: 'Fusing Optical and Radar Data for Delineating Urban Damage Destruction'
author: "Gal Bdolach"
author_profile: true
date: 2026-06-12
toc: true
toc_sticky: true
toc_label: "Delineating Urban Damage Destruction"
header:
  overlay_image: https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/header.jpg
  overlay_filter: 0.3
  caption: 'Pre- and post Earthquake Satellite Images'
read_time: false
tags:
  - urban damage detection
  - radar coherence
  - optical and radar data fusion
---
This study evaluates the capacity of medium-resolution optical and radar satellite imagery (Sentinel-1 and Sentinel-2) to detect and delineate urban destruction, utilizing the 2023 Turkey-Syria earthquake as a primary case study. The analysis identifies specific spectral bands and radar feature importance to determine which data inputs drive the most accurate damage classification.

# Introduction

Urban destruction caused by natural disasters and armed conflicts is a major global challenge and poses significant humanitarian, economic, and infrastructural challenges. The assessment of such destruction and its delineation are critical for rescue efforts, humanitarian aid, reconstruction planning, and long-term risk analysis. However, traditional field-based damage assessment and delineation are often complicated, especially in the days and weeks following the event. Field assessment efforts are often hindered by accessibility constraints, safety concerns, as well as military or political restrictions. As a result, damage assessment using satellite imagery becomes increasingly important. Remote sensing can be used as a tool for monitoring and delineating urban destruction at regional and global scales. High-resolution imagery can provide accurate destruction delineation; however, such imagery is not always available and is often expensive to acquire. This makes freely available medium-resolution imagery from satellites like Sentinel an intriguing solution.

This project aims to analyze which freely available medium-resolution satellite data can be used for the detection of urban destruction using XGBoost models. The project also analyzes which derived attributes and which band combinations offer the highest delineation accuracy. The study further evaluates the difference between radar and optical imagery and their fusion. 

Due to the widespread destruction and the availability of data, the 2023 Turkey-Syria earthquake serves as the main case study. The 2023 Turkey-Syria earthquake was a series of earthquakes, the largest being of 7.7 magnitude, which caused widespread destruction along the Turkey-Syria border and resulted in the loss of more than 50 thousand lives, as well as the collapse of 38,440 buildings (Damcı et al., 2025). The earthquake caused significant urban destruction in major cities such as Antakya and Iskenderun. Those two cities serve as the main training and validation areas for the models.

In order to test the transferability of the models to different geographic regions, the 2023 Morocco earthquake was also analyzed as an additional case study.

*This internship was supervised by Prof. Dr. Bodo Bookhagen.*

# Study Area 

The study focuses primarily on urban destruction caused by the 2023 Turkey-Syria earthquake. On 06.02.2023, a magnitude 7.7 earthquake struck southern Turkey with the epicenter lying near Gaziantep, while the epicenter of a second magnitude 7.6 earthquake, which occurred nine hours later, lay near Elbistan (Fig. 1, Damcı et al., 2025). The extensive building collapse and the availability of high-resolution imagery of the area directly after the earthquake via Google Earth made the event a suitable case for analyzing the capability of medium-resolution imagery for urban destruction delineation. 

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/d08f63c9-349a-46fc-9d6d-c7b0c15f3dc2.webp">
  <figcaption><b>Figure 1</b> Seismicity map of the affected region of the 2023 Turkey-Syria Earthquakes between Feb. 6 to Feb. 20 and the mapped active faults by the USGS (after AFAD-TADAS 2023) (Tobita et al. 2024).</figcaption>
</figure>

The city of Antakya (Fig. 2) was selected as the training area due to its high destruction density (Aydin et al., 2025) and large number of collapsed buildings, which could be used for the training of the models. The city contains dense urban neighborhoods as well as more isolated high-rise buildings, allowing the models to learn different spatial patterns of urban destruction. 

Iskenderun (Fig. 2), a smaller coastal city located to the north of Antakya along the Mediterranean Sea, was selected as the main validation area. Compared to Antakya, the city experienced a lower destruction density and more spatially isolated collapse patterns. This makes destruction delineation more difficult and reduces the possibility that the models simply identify large destruction areas. In addition, the availability of reliable building footprints allowed for a detailed object-based assessment of model performance, which serves as a more valuable evaluation tool than the pixel-based assessment used for Antakya. 

Near the port of Iskenderun, a large fire burned in the days after the earthquake, spreading smoke across the city as can be seen in Figure 2. This introduced additional visual disturbances into the imagery and allowed the models to be tested under more complex post-disaster conditions.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/325be9b1-6677-4131-90ab-74b34055b9ba.png">
  <figcaption><b>Figure 2</b> Map of the study area (Antakya and Iskenderun) post-earthquake using Sentinel-2 images with the OSM standard basemap as background.</figcaption>
</figure>

In addition to the Turkey–Syria earthquake, the 2023 Morocco earthquake was used as a small transferability test (Fig. 3). The village of Tafeghaghte, which was almost entirely destroyed during the earthquake (Imtiaz et al., 2025; *Morocco Quake Leaves Half of Village’s Population Dead or Missing, 2023*), differs substantially from Antakya and Iskenderun in terms of building materials, settlement structure, and surrounding environment. The village therefore served as a small test area to evaluate whether the models could detect destruction in a significantly different geographic setting.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/c663f79b-39a2-4fdb-bdbf-855dc0fd0c4c.png">
  <figcaption><b>Figure 3</b> Tafeghaghte before and after the 2023 Morocco earthquake, images provided by Google Earth Pro.</figcaption>
</figure>

# Data

This study used different datasets for the training, mapping, and validation of the models.
The models are based on Sentinel-1 and Sentinel-2 imagery downloaded from the Copernicus Browser. 
The Sentinel-2 imagery (except band 10) was resampled and aligned to a common 10 m spatial resolution using nearest-neighbor resampling in SNAP (Table 1). The Sentinel-1 imagery was processed in SNAP, and coherence, backscatter, and ten GLCM (Gray Level Co-occurrence Matrix) texture layers for both VV and VH polarizations were calculated before aligning the data with the Sentinel-2 data.  

The final datasets consisted of stacked raster files containing 12 Sentinel-2 bands together with 24 radar-derived layers. Separate stacks were created for Antakya and Iskenderun. 

For Antakya, which served as the training area, three temporal datasets were used: two pre-earthquake acquisitions and one post-earthquake acquisition. The usage of two pre-earthquake dates allowed the creation of additional "intact" change samples, helping the model distinguish between real destruction and normal temporal variation. For Iskenderun and Morocco, which were used for the evaluation of the models, one pre-earthquake and one post-earthquake stack were used, since these areas served only for validation and not for training.  

The calculation of Sentinel-1 coherence required earlier imagery in addition to the main pre and post dates. Table 2 summarizes the imagery used in the project. 

In addition to the Sentinel imagery, high-resolution imagery from Google Earth Pro and 3m PlanetScope imagery were used for the creation and validation of the training and validation datasets. 

<center>

#### Table 1. Sentinel-2 bands

</center>

| Band Number | Sentinel-2 Band Name | Common Name        | Spatial Resolution |
|--------------|----------------------|--------------------|-------------------|
| B1           | Coastal Aerosol      | Aerosol            | 60 m              |
| B2           | Blue                 | Blue               | 10 m              |
| B3           | Green                | Green              | 10 m              |
| B4           | Red                  | Red                | 10 m              |
| B5           | Vegetation Red Edge  | Red Edge 1         | 20 m              |
| B6           | Vegetation Red Edge  | Red Edge 2         | 20 m              |
| B7           | Vegetation Red Edge  | Red Edge 3         | 20 m              |
| B8           | Near Infrared        | NIR                | 10 m              |
| B8A          | Narrow Near Infrared | Narrow NIR         | 20 m              |
| B9           | Water Vapour         | Water Vapour       | 60 m              |
| B10          | Cirrus               | Cirrus             | 60 m              |
| B11          | Shortwave Infrared   | SWIR 1             | 20 m              |
| B12          | Shortwave Infrared   | SWIR 2             | 20 m              |


<center>

#### Table 2. Acquisition dates of satellite images

</center>

| Sensor | Image Dates | Purpose |
|:---|:---|:---|
| Sentinel-1 | 05.01.2023 & 17.01.2023 | Pre-earthquake coherence pair |
| Sentinel-1 | 17.01.2023 & 29.01.2023 | Pre-earthquake coherence pair |
| Sentinel-1 | 29.01.2023 & 10.02.2023 | Co-event coherence pair |
| Sentinel-1 | 17.01.2023 | Pre-earthquake backscatter & GLCM |
| Sentinel-1 | 29.01.2023 | Pre-earthquake backscatter & GLCM |
| Sentinel-1 | 10.02.2023 | Post-earthquake backscatter & GLCM |
| Sentinel-2 | 20.01.2023 | Pre-earthquake optical image |
| Sentinel-2 | 25.01.2023 | Pre-earthquake optical image |
| Sentinel-2 | 09.02.2023 | Post-earthquake optical image |

# Methodology

## Training Data

The training data contains both intact and destroyed buildings from the city of Antakya and the surrounding area and was based on a publicly available dataset created and provided by the Humanitarian OpenStreetMap Team (HOTOSM Turkey Destroyed Buildings (OpenStreetMap Export) | Humanitarian Dataset | HDX, n.d.). The dataset served as the initial source for collapsed/destroyed building polygons.

Using high-resolution imagery available through Google Earth Pro from before and directly after the earthquake, the Humanitarian OpenStreetMap Team (HOT) dataset was manually validated and corrected. Buildings labeled as collapsed but without visible evidence of destruction were removed, and additional evidently collapsed buildings missing from the dataset were manually added. The creation and correction of polygons was done using 3 m PlanetScope imagery. In Figure 4, an example from the training dataset is visualized, highlighting the high density of destruction in the center of Antakya. 

Intact buildings were all manually mapped in a more or less random fashion across the city in order to provide a balanced training dataset. The same validation methodology used for collapsed buildings was also applied to intact buildings. The final ratio between intact and collapsed building pixels in the dataset was approximately 1:1. 

For the training of the models, both pre-earthquake stacks and the post-earthquake stack were used. This means that changes between the two pre-earthquake dates as well as changes between pre- and post-earthquake dates were included in the training. Including pre-earthquake temporal pairs also allowed the model to learn normal temporal variation unrelated to destruction, thereby reducing false detections caused by seasonal or acquisition differences. All polygons were considered intact in the pre-earthquake comparisons. Every pixel overlapping a polygon inherited the polygon label; in total, 14,590 intact pixels and 5,508 destroyed pixels were used for the training and validation of the models.

To prevent spatial leakage, pixels originating from the same building polygon were not allowed to appear simultaneously in both the training and validation datasets. The final split consisted of 80% of the building polygons for training and 20% for validation. 

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/a2c74237-ac1b-4436-9648-e002a7f87ff9.png">
  <figcaption><b>Figure 4</b> Extract of the Antakya validation dataset, displayed over a post-earthquake Sentinel-2 imagery background.</figcaption>
</figure>

## Validation Data 

Apart from the internal validation performed in Antakya, the city of Iskenderun was selected as the primary independent validation area. Compared to Antakya, Iskenderun experienced lower destruction density (Tobita et al., 2024) and contained more reliable pre-earthquake building footprints from OpenStreetMap (Turkey Buildings (OpenStreetMap Export) | Humanitarian Dataset | HDX, n.d.), making it more suitable for object-based assessment (Fig. 5). The collapsed buildings in Iskenderun were all manually mapped and validated using the same methodology as in Antakya. These polygons were merged with the available OpenStreetMap data. In case of an overlap between a collapsed polygon and an intact building footprint, the intact polygons were removed.

The Iskenderun dataset contained 97 collapsed building polygons, some of which covered a number of buildings that, due to the resolution, could not be individually mapped, and 33,434 buildings from OSM. Out of the 33,434 OSM buildings, 33,275 remained after the removal of overlapping buildings. 

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/76c1eae7-72c3-419d-9b83-5d9169eed458.png">
  <figcaption><b>Figure 5</b> Extract of the Iskenderun validation dataset, displayed over a post-earthquake Sentinel-2 imagery background.</figcaption>
</figure>

## Feature Engineering

The models were not based solely on the unprocessed (raw) before and after satellite images, but also on a number of features derived from them.
The tested attributes included: 
- Raw before and after imagery
- Absolute difference
- Normalized difference
- Relative change
- Local mean difference ($3 \times 3$, $5 \times 5$, and $7 \times 7$ windows)
- Local variance difference ($3 \times 3$, $5 \times 5$, and $7 \times 7$ windows)
- Entropy difference
- Sobel edge magnitude difference
- Morphological gradient difference
- Top-Hat transform difference
- Difference in morphological opening and closing
- Median difference
- Percentile range (90-10) difference

A $3 \times 3$ window was used for entropy, morphological, and robust statistical features in order to preserve localized building-scale changes and reduce excessive spatial smoothing. Larger windows were avoided since the 10 m Sentinel resolution already introduces substantial spatial mixing in dense urban environments.

Each attribute was calculated for each band for every model. In models that contained the required bands, NDVI and NDBI were calculated and treated as separate bands, meaning that the different attributes were also calculated for them. 

## Feature Selection

In order to accurately compare the bands and their impact on the model, the importance and impact of the derived attributes had to be determined. This was done through the creation of 15 models based on different combinations of both optical and radar-derived bands for which all considered attributes were calculated. Feature importance was evaluated using both SHAP values and XGBoost gain. Gain measures how useful a feature is for reducing model error during tree splitting (Chen & Guestrin, 2016), while SHAP values measure how strongly a feature contributes to the final predictions across all samples (Lundberg & Lee, 2017).

Features with consistently low contributions across all models, defined as having an average SHAP value below 0.02 and an average gain below 0.005, were removed from subsequent experiments. However, Local Mean ($3 \times 3$) was retained despite its low contribution in order to preserve local spatial context and avoid excessive smoothing of the models.

## Model Training

The models were created using XGBoost classification. The following parameters were selected in order to improve generalization while maintaining computational efficiency:

- n_estimators = 150
- max_depth = 4 
- min_child_weight = 10 
- gamma = 2 
- learning_rate = 0.05 
- tree_method = 'hist' 
- random_state = 42 

Lower tree depth and higher minimum child weight were used to reduce overfitting and prevent overly specific splits. The histogram tree method was selected in order to improve training speed given the large number of pixels and derived attributes.

Two masks were generated to reduce false positives: a mask based on the SCL layer from Sentinel-2, which removed any clouds, shadows, and snow, and a vegetation mask, which removed pixels with an NDVI of over 0.3.

## Model Validation

Validation in Antakya was performed at the pixel level due to the lack of a complete and reliable pre-earthquake building footprint for the city. The results of the Antakya validation were considered of lesser importance for this study due to their relation to the training data and their dependence on pixel-level rather than object-level assessment. 

For Iskenderun, validation was performed at the object level. A building was considered collapsed if more than 15% of its area overlapped with pixels predicted as destroyed. This threshold was selected due to the signal mixing occurring within 10 m pixels and in order to account even for partial building collapse. The object-based approach allowed the calculation of true positives, false negatives, and false positives at the building scale. 

False positives were separated into two categories:

- Spillover false positives: buildings falsely classified as collapsed due to adjacency to truly collapsed buildings. A false positive was considered spillover if it was connected through destroyed pixels to a true positive building. 
- Isolated false positives: buildings falsely classified as collapsed without any direct spatial connection to true collapsed areas.

This distinction allowed a better assessment of whether errors were caused by spatial overspill from nearby destruction or by true misclassification of intact structures.

A pixel was classified as destroyed when the model probability exceeded 90%. A relatively high threshold was selected in order to improve precision and reduce the impact of noise and uncertain predictions.

# Results and Discussion

## Feature Selection

In total, 6 attributes fell below the thresholds of 0.02 SHAP and 0.005 gain (Figs. 6 & 7). The features Difference (raw), Top-Hat Transform, Sobel Edge, Relative Change, and the Morphological Gradient were removed due to their low impact on the models. Local Mean ($3 \times 3$), which also fell below the thresholds, was not removed in order to preserve fine-scale spatial context and avoid excessive smoothing of building-level signals.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/a2232d26-9832-4008-9154-6d7c268c3115.png">
  <figcaption><b>Figure 6</b> Feature importance distribution based on XGBoost's gain metric.</figcaption>
</figure>


<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/31afa71d-f91b-44da-950a-94096f1904a2.png">
  <figcaption><b>Figure 7</b> Feature importance distribution based on the SHAP metric.</figcaption>
</figure>

The removal of the low-contributing attributes did not reduce the accuracy of the models and in some cases even improved the recall (Table 3). The tested models included a model containing all Sentinel-2 bands, a model containing all radar-derived bands, and a model consisting of a mixture of the two. The results indicate that many of the removed attributes mainly introduced noise rather than important information, and that reducing the number of attributes can even improve model performance.

Additional experiments using 3D variance ($5 \times 5 \times \text{bands}$), meaning variance calculated both spatially and spectrally across selected band groups, did not significantly improve the results compared to using only traditional spatial variance (Table 4). This suggests that while spectral-spatial texture contains useful information, the additional complexity introduced by the 3D variance calculation did not substantially improve the delineation capability of the models at Sentinel resolution and in some cases even reduced it.


<center>

#### Table 3. Impact of attribute selection on F1 score in Antakya

</center>

| Model    | F1 score (Antakya) with low impact attributes | F1 score (Antakya) without low impact attributes    | F1 score (Antakya) without low impact attributes and with 3D variance|
| :---        |    :----   |:---         | :---|
| Sentinel 1    | 0.37       | 0.37   | 0.37 |
| Sentinel 2  | 0.73       | 0.73   |0.74  |
| Sentinel 2 + Coherence & Backscatter  | 0.77     | 0.77   | 0.76 |


<center>

#### Table 4. Impact of attribute selection on true positives in Iskenderun

</center>

| Model    | True positive (Iskenderun) with low impact attributes | True positive (Iskenderun) without low impact attributes    | True positive (Iskenderun) without low impact attributes and with 3D variance |
| :---        |    :----   |:---         | :---  |
| Sentinel 1    | 25       | 26  | 24 |
| Sentinel 2  | 49      | 52  | 51|
| Sentinel 2 + Coherence & Backscatter  | 68    | 70   | 64|


As a result of the discussed feature selection, the models discussed and analyzed in the following sections contained only the following attributes: 
Raw bands (both pre- and post-earthquake)
- Normalized Difference
- Local Mean Difference ($3 \times 3$, $5 \times 5$, $7 \times 7$)
- Variance Difference ($3 \times 3$, $5 \times 5$, $7 \times 7$)
- Entropy Difference ($3 \times 3$)
- Closing Difference ($3 \times 3$)
- Opening Difference ($3 \times 3$)
- Median Difference ($3 \times 3$)
- Percentile Range (90-10) Difference ($3 \times 3$)

A $3 \times 3$ window was used for entropy, morphological, and robust statistical features in order to preserve localized building-scale changes and reduce excessive spatial smoothing. Larger windows were avoided since the 10 m Sentinel resolution already introduces substantial spatial mixing in dense urban environments.

## Optical Imagery 

Ten models containing only Sentinel-2 bands were trained and validated in order to determine the impact of individual optical bands on the delineation of collapsed buildings (Table 5). Precision and false alarm values were calculated using only isolated false positives. Spillover false positives were not considered true misidentifications, since they are largely caused by the low spatial resolution of Sentinel imagery and by the influence that large-scale building collapse has on the surrounding environment. The results show that each true positive generally creates roughly one to two spillover false positives.

<center>

#### Table 5. Results of optical imagery based models

</center>

| Model                                           | TP | FN | Spillover FP | Isolated FP | Recall | Precision | F1 Score | Isolated False Alarms / 1000 Buildings |
| :---------------------------------------------- | -: | -: | -----------: | ----------: | -----: | --------: | -------: | -------------------------------------: |
| Model RGB                                       | 35 | 62 |           22 |          26 |  0.361 |     0.574 |    0.443 |                                   0.78 |
| Model RGB + NIR                                 | 40 | 57 |           52 |          44 |  0.412 |     0.476 |    0.442 |                                   1.32 |
| Model RGB + Narrow NIR                          | 46 | 51 |           51 |          24 |  0.474 |     0.657 |    0.551 |                                   **0.72** |
| Model RGB + Red Edge                            | 49 | 48 |           61 |          41 |  0.505 |     0.544 |    0.524 |                                   1.23 |
| Model RGB + SWIR                                | 54 | 43 |           57 |          42 |  0.557 |     0.563 |    0.560 |                                   1.26 |
| Model RGB + Infrared                            | 52 | 45 |           83 |          49 |  0.536 |     0.515 |    0.525 |                                   1.47 |
| Model RGB + Aerosols & Water Vapour             | 36 | 61 |           31 |          60 |  0.371 |     0.375 |    0.373 |                                   1.80 |
| Model Infrared                                  | **56** | 41 |          101 |          27 |  **0.577** |    **0.675** |    **0.622** |                                   0.81 |
| Model Infrared + Aerosols & Water Vapour        | 52 | 45 |          96  |          98 |  0.536 |     0.347 |    0.421 |                                   2.95 |
| Model All Sentinel 2                            | 52 | 45 |           90 |          64 |  0.536 |     0.448 |    0.488 |                                   1.92 |


The RGB model provides a baseline against which the influence of additional optical bands can be assessed. The addition of Red Edge, NIR, and SWIR bands all improved the performance compared to the RGB-only model. The addition of SWIR bands resulted in the strongest improvement, with the RGB + SWIR model achieving both higher recall and higher precision than the other RGB-based models. This indicates that shortwave infrared wavelengths are particularly sensitive to the spectral changes caused by urban destruction. These changes likely include exposed concrete, dust accumulation (Zhu et al., 2025), roof material changes, and moisture loss (Zohaib et al., 2025).

Interestingly, the addition of all infrared bands (Red Edge, NIR, Narrow NIR, and SWIR) to the RGB model did not outperform the RGB + SWIR model, despite containing a larger amount of spectral information. The Infrared model, which contains all infrared bands but excludes RGB, did however outperform all RGB-based combinations and achieved the best overall performance among the optical models. This indicates that combining RGB with a large number of infrared bands does not necessarily improve the model and may instead introduce redundancy and additional noise. The higher recall, precision, and lower false alarm rate of the Infrared model compared to the full Sentinel-2 model, which contains all 12 bands, further highlights that simply stacking more bands does not automatically improve model performance.

The addition of atmospheric bands (Aerosol and Water Vapour) did not improve the delineation of destruction and resulted in significantly higher false positive rates. Their contribution to urban destruction delineation therefore appears limited within the context of this study. A possible reason for this may be their very low resolution (60m), which fails to detect smaller-scale destruction.

Four additional optical models were tested in order to better isolate the impact of SWIR and to assess the interaction between SWIR and near-infrared bands (Table 6).

<center>

#### Table 6. Results of optical SWIR based models

</center>

| Model                                           | TP | FN | Spillover FP | Isolated FP | Recall | Precision | F1 Score | Isolated False Alarms / 1000 Buildings |
| :---------------------------------------------- | -: | -: | -----------: | ----------: | -----: | --------: | -------: | -------------------------------------: |
| Model SWIR                                       | 33 | 64 |           53 |          92 |  0.340 |     0.264 |    0.297 |                                   2.76 |
| Model SWIR + Narrow NIR                                 | 42 | 55 |           64 |          37 |  0.433 |     0.532 |    0.477 |                                   1.11 |
| Model RGB + Narrow NIR + SWIR                         | 49 | 48 |           60 |          28 |  0.505 |     **0.636** |    **0.563** |                                   **0.84** |
| Model RGB + NIR + SWIR                            | **58** | 39 |           89 |          72 |  **0.598** |     0.446 |    0.511 |                                   2.16 |


The results demonstrate that while SWIR strongly improves performance when combined with RGB or other infrared bands, the two SWIR bands alone do not produce reliable or meaningful results. A combination of Narrow NIR and SWIR also performed relatively poorly and did not improve on the RGB-based models. 

The comparison of the impact of NIR and Narrow NIR on the models, by combining each with RGB and SWIR, provides very interesting results. The model containing Narrow NIR achieved a higher precision but a lower recall than the corresponding NIR model. This suggests that NIR bands contribute more strongly to the detection of collapsed buildings, but at the cost of an increased number of isolated false positives. Nevertheless, neither of the tested combinations significantly outperformed the RGB + SWIR model. The main difference was that the NIR-based combinations detected a larger number of collapsed buildings, but without achieving a higher F1 score.

Overall, the tested optical models demonstrate the importance of infrared wavelengths, particularly SWIR, for the delineation of urban destruction. Out of all tested optical models, the Infrared model achieved the highest recall, precision, and one of the lowest isolated false alarm rates, highlighting the strong contribution of infrared spectral information for detecting collapsed urban structures.

## Radar Imagery

<center>

#### Table 7. Results of radar based models

</center>

| Model                                | TP | FN | Spillover FP | Isolated FP | Recall | Precision | F1 Score | Isolated False Alarms / 1000 Buildings |
| :----------------------------------- | ---: | ---: | -----------: | ----------: | -----: | --------: | -------: | -------------------------------------: |
| Model Coherence + Backscatter        | **31** | 66 |           83 |         285 |  **0.320** |     0.098 |    0.150 |                                   8.57 |
| Model GLCM                           |  7 | 90 |           20 |         103 |  0.072 |     0.064 |    0.068 |                                   **3.10** |
| Model Coherence + Backscatter + GLCM | 26 | 71 |           97 |         185 |  0.268 |     **0.123** |    **0.169** |                                   5.56 |


Compared to the optical models, the radar-only models produced substantially lower precision and recall (Table 7). The Coherence + Backscatter model performed significantly better than the GLCM-only model, indicating that coherence loss and backscatter changes contain considerably more useful information regarding structural collapse than radar texture measures alone.

The GLCM-based model showed very limited ability to delineate destruction and produced both low recall and a large number of false positives. This suggests that medium-resolution radar texture alone is insufficient for reliable urban destruction detection in dense urban environments. The addition of GLCM features to the Coherence + Backscatter model also did not improve the results and slightly reduced the overall performance. This further indicates that many radar texture features mainly introduce noise rather than meaningful structural information.

Despite the lower performance of models based solely on radar-derived information, radar still captures unique information that optical data alone cannot. Coherence and backscatter changes are particularly sensitive to structural disturbance, surface roughness changes, and the disruption of geometric scattering effects following building collapse (Olen & Bookhagen, 2018). 

Additionally, the independence of radar imagery from cloud cover and illumination conditions makes radar particularly valuable. In order to determine if radar-derived data can be of use, models that combine optical and radar data were tested. 

## Combined Optical and Radar 

<center>

#### Table 8. Results of optical and radar combined models

</center>

| Model                                                   | TP | FN | Spillover FP | Isolated FP | Recall | Precision | F1 Score | Isolated False Alarms / 1000 Buildings |
| :------------------------------------------------------ | -: | -: | -----------: | ----------: | -----: | --------: | -------: | -------------------------------------: |
| Model RGB + NIR + Coherence & Backscatter               | 63 | 34 |          112 |          45 |  0.649 |     0.583 |    0.614 |                                   1.35 |
| Model RGB + Narrow NIR + Coherence & Backscatter        | 64 | 33 |          115 |          31 |  0.660 |     0.674 |    0.667 |                                   0.93 |
| Model RGB + NIR + SWIR + Coherence & Backscatter        | 73 | 24 |          146 |          27 |  0.753 |     **0.730** |    **0.742** |                                   **0.81** |
| Model RGB + Narrow NIR + SWIR + Coherence & Backscatter | 71 | 26 |          152 |          30 |  0.732 |     0.703 |    0.717 |                                   0.90 |
| Model Infrared + Coherence & Backscatter                | 69 | 28 |          156 |          40 |  0.711 |     0.633 |    0.670 |                                   1.20 |
| Model All Sentinel 2 + Coherence & Backscatter          | 70 | 27 |          148 |          35 |  0.722 |     0.667 |    0.693 |                                   1.05 |
| Model All Sentinel 2 + Sentinel 1                       | 69 | 28 |          178 |          64 |  0.711 |     0.519 |    0.600 |                                   1.92 |


The combination of optical and radar-derived features substantially improved the delineation of urban destruction compared to models based solely on Sentinel-1 or Sentinel-2 data (Table 8). 

The best-performing model was the RGB + NIR + SWIR + Coherence & Backscatter model, which achieved the highest recall, precision, and F1 score, while also maintaining the lowest isolated false alarm rate. The results indicate that radar-derived features provide complementary structural information that strengthens the spectral information captured by optical imagery.

While optical data captures spectral changes caused by destruction, such as exposed debris, dust, and roof material changes, radar coherence and backscatter capture structural disturbance, roughness changes, and geometric disruption caused by collapsed buildings (Wang et al., 2022; Washaya et al., 2018). The combination of both data sources therefore allows the models to detect destruction more reliably than either dataset individually.

The combined models also demonstrated that optical data helps suppress part of the radar-derived noise. Radar-only models produced very large numbers of isolated false positives, while combined optical-radar models substantially reduced those errors and achieved much higher precision.

The importance of SWIR bands remained evident within the combined models. Adding SWIR consistently improved both recall and precision while maintaining relatively low false positive rates. This further supports the conclusion that SWIR wavelengths are particularly sensitive to urban destruction.

However, the experiments also showed that excessively large feature stacks reduce model quality. The model containing the full Sentinel-1 and Sentinel-2 datasets produced lower recall and significantly higher isolated false positive rates than more selective combinations. This suggests that introducing too many bands and derived attributes increases noise and reduces the ability of the model to generalize.

This effect can also explain the relatively disappointing performance of the Infrared + Coherence & Backscatter model. Although the Infrared model alone performed very well, ranking highest among the optical-only models, adding radar-derived features did not further improve the results as much as expected. In order to test whether this was caused by excessive feature complexity, a thinner model containing only the highest-contributing infrared bands (NIR, RE1, and SWIR2) together with coherence and backscatter was tested (Table 9).

<center>

#### Table 9. Results of thin infrared + coherence & backscatter model

</center>

| Model                                | TP | FN | Spillover FP | Isolated FP | Recall | Precision | F1 Score | Isolated False Alarms / 1000 Buildings |
| :----------------------------------- | -: | -: | -----------: | ----------: | -----: | --------: | -------: | -------------------------------------: |
| Model NIR + RE 1 + SWIR 2 + Coherence & Backscatter | **76** | 21 |           181 |         43 |  **0.784** |     0.639 |    0.704 |                                   1.29 | 


The thinner model achieved considerably better results than the full Infrared + Coherence & Backscatter model, indicating that careful feature selection is more effective than simply maximizing the number of input bands. Although the thinner model produced a slightly lower F1 score than the RGB + NIR + SWIR + Coherence & Backscatter model, it achieved the highest recall of all tested models and detected the largest number of collapsed buildings.

## Feature Importance

Feature importance analysis was performed using both XGBoost gain and SHAP values. 

<center>

#### Table 10. Feature importance of two models

</center>

| Model RGB + NIR + SWIR + Coherence & Backscatter | SHAP | Gain     |   | Model thin Infrared + Coherence & Backscatter | SHAP     | Gain     |
|--------------------------------------------------|----------------|----------|---|-----------------------------------------------|----------|----------|
| Blue                                             | **1.195**       | 0.089 |   | SWIR 2                                         | **1.992** | 0.160 |
| NIR                                              | 1.055      | **0.292** |   | NIR                                           | 1.384 | **0.369** |
| VV Coherence                                     | 0.999       | 0.060 |   | VV Coherence                                  | 1.137 | 0.112  |
| SWIR 2                                            | 0.972        | 0.157 |   | VH Coherence                                  | 0.882  | 0.073 |
| VH Coherence                                     | 0.733      | 0.059 |   | RE 1                                           | 0.589 | 0.146 |
| VH Backscatter                                   | 0.472       | 0.037 |   | VH Backscatter                                | 0.499 | 0.069 |
| NDBI                                             | 0.443      | 0.056 |   | VV Backscatter                                | 0.365 | 0.071 |
| NDVI                                             | 0.420      | 0.041 |   |                                               |          |          |
| Red                                              | 0.408      | 0.049 |   |                                               |          |          |
| SWIR 1                                            | 0.385       | 0.082 |   |                                               |          |          |
| VV Backscatter                                   | 0.203       | 0.031 |   |                                               |          |          |
| Green                                            | 0.128       | 0.047 |   |                                               |          |          |


The feature importance analysis demonstrates that models with similar overall accuracy can rely on substantially different spectral information (Table 10). This indicates that urban destruction can be delineated through multiple spectral pathways rather than through one single dominant band combination.

In both models, NIR remained one of the most important bands in terms of both SHAP and gain, showing that near-infrared wavelengths provide highly relevant information for distinguishing between intact and collapsed structures. SWIR 2 also remained highly important in both models, especially in terms of gain, indicating that it was frequently used by the trees to create effective splits. However, while the gain of SWIR 2 remained relatively stable, its SHAP importance was considerably lower in the RGB-based model. This suggests that while SWIR 2 continued to play an important structural role within the model, part of the information it captured became shared with the visible bands, reducing the model’s dependence on SWIR 2 for final predictions.

Among the visible bands, blue showed the highest SHAP and gain values. This may be related to the sensitivity of shorter wavelengths to dust, exposed concrete, and brightness changes associated with collapsed structures. Its relatively lower gain but high SHAP importance suggests that blue was not used as frequently for tree splitting as infrared bands, but that when used it had a strong influence on the final prediction outcome.

The lower importance of the red and green bands suggests that they either contain more redundant information or are less sensitive to destruction-related spectral changes. Radar-derived coherence remained consistently important in both models, underlining the value of combining optical and radar-derived information. While optical bands capture spectral changes such as exposed material, debris, and color differences, coherence captures structural disturbance and the loss of geometric consistency following collapse.

Backscatter showed lower importance in both gain and SHAP, likely due to its higher sensitivity to urban noise and local geometric variation. Nevertheless, its contribution remained positive, indicating that radar backscatter still contains useful complementary information when combined with optical imagery.

Overall, the feature importance analysis highlights NIR, SWIR 2, blue, and radar coherence as the most relevant inputs for urban destruction delineation within this study. However, further testing is required to determine whether these bands alone are sufficient or whether part of their predictive value depends on interactions with lower-importance bands. 

## Spatial Assessment of Results 

The two most successful models, the thinner Infrared + Coherence & Backscatter model and the RGB + NIR + SWIR + Coherence & Backscatter model, produced very similar spatial patterns of false negatives and false positives.

Most false negatives were smaller buildings, often isolated from other collapsed structures, as can be seen in Figures 8 & 9. In many cases, the buildings collapsed mainly into themselves and not sideways into the street or neighboring buildings, thus leaving only a limited spectral and structural footprint. The average area of a false negative polygon was slightly above 300 m², while the average true positive building covered roughly 600 m². This indicates that larger collapses affecting a wider spatial area are considerably easier to detect using medium-resolution imagery, and corresponds to a similar study which identified 300 m² as a threshold for urban destruction delineation with Sentinel images (Aimaiti et al., 2022). 

Most false positives occurred close to truly collapsed buildings. Even in cases where no direct pixel connection existed between the false positive and a true positive, nearby destruction often appeared to influence the prediction. Only a relatively small number of isolated false positives occurred in completely unaffected neighborhoods. This suggests that many false positives are not random misclassifications but rather are caused by the spatial mixing and overspill effects introduced by the 10 m Sentinel resolution, especially considering that several important infrared bands originally have a 20 m spatial resolution and were resampled.

A noticeable concentration of destroyed pixels was also observed near the coastline. Many of those areas were not directly related to collapsed buildings but were located in reclaimed coastal zones affected by inundation, tilting, and liquefaction following the earthquake (Tobita et al., 2024). This indicates that the models not only capture complete building collapse, but also more broadly areas which experienced certain strong spectral and structural surface changes after the earthquake.

The spatial assessment therefore highlights the main limitation of the models: the medium spatial resolution of Sentinel imagery. While the models are capable of identifying larger zones of destruction and clusters of collapsed buildings with relatively high accuracy, they struggle with smaller isolated collapses and with the precise delineation of building boundaries. This results in both missed detections of small buildings and spillover effects into neighboring intact structures.


<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/80b045df-1c8a-44ab-b190-6d14f3c4bc91.png">
  <figcaption><b>Figure 8</b> RGB + NIR + SWIR + Coherence & Backscatter Model Results</figcaption>
</figure>


<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Gal_Bdolach_figures/cbeb8fa7-54d3-490c-b9ea-5a138221014a.png">
  <figcaption><b>Figure 9</b> Thin Infrared Model Results</figcaption>
</figure>

## Transferability Tests

Both the Infrared + Coherence & Backscatter and the RGB + NIR + SWIR + Coherence & Backscatter models failed to reliably detect destruction in the village of Tafeghaghte in Morocco. The models produced no meaningful destruction delineation. This indicates that the models trained on the Turkey-Syria earthquake data do not generalize well to structurally and spectrally different environments.

There are several factors that likely contributed to the limited transferability of the models. The building material, settlement structure, and urban density in Tafeghaghte differ significantly from those in Antakya. Additionally, differences in illumination conditions, topography, vegetation, and background reflectance most likely altered the spectral response to the collapse of structures. Since the training dataset of the models is based on the dense urban destruction patterns of Antakya, the models appear to struggle when applied to rural mountainous villages with completely different construction characteristics like those of Tafeghaghte. 

An additional test in which two pre-earthquake Iskenderun stacks were analyzed resulted in no destruction being detected. This demonstrates that the models do not systematically classify normal temporal variation as collapse and that false positives caused purely by acquisition differences remain relatively limited.

A further test in which the pre- and post-earthquake Iskenderun stacks were intentionally reversed also resulted in no destruction being detected. This indicates that the models are not simply detecting normal change between two images, but are specifically sensitive to the directional spectral and structural changes associated with building collapse.

Overall, the transferability experiments demonstrate that while the models perform relatively well within the Turkey-Syria earthquake context, their application to geographically and structurally different environments remains limited. Additional training data from different regions, settlement types, and earthquake events would likely be necessary to develop a more globally transferable urban destruction detection model.


# Limitations and Future Work

The main limitation of the study is the geographic transferability of the models. While the models performed well in Iskenderun, they failed to produce meaningful results in the rural Moroccan test area. This suggests that the spectral and structural characteristics learned from the Turkey-Syria earthquake may not be directly transferable to other regions, especially those with a completely different urban morphology, building materials, topography, and environmental conditions. While the importance of the infrared bands and of radar coherence is likely not specific to Antakya and Iskenderun, their relative importance may change when analyzing urban destruction in other regions of the world. Additionally, the models were trained on urban destruction caused by earthquakes; it remains unclear if SWIR, NIR, and coherence are equally important for the delineation of urban destruction following military conflicts, floods, and fires. 

Another limitation is the spatial resolution of Sentinel data. Most Sentinel-2 infrared bands have an original resolution of 20 m and were resampled to 10 m, while many collapsed buildings in dense urban environments are smaller than a single 20 m pixel. This caused significant signal mixing and resulted in spillover effects as well as difficulties in detecting small isolated collapses. The models performed considerably better on larger buildings or building clusters than on small isolated buildings. The reliance on OpenStreetMap building footprints may also introduce geometric inaccuracies or missing structures, potentially affecting the accuracy assessment. However, these inaccuracies are unlikely to significantly alter the study's main conclusions regarding the importance and performance of the tested bands and models. 

Finally, the study focused only on XGBoost models, as these are well-suited for analyzing feature importance and handling mixed optical and radar datasets. However, other approaches such as convolutional neural networks, temporal models, or object-based deep learning methods may achieve different results and may rely on different band combinations or feature configurations. 

Future work should therefore focus on:
- Testing the analyzed bands and models across a larger number of urban destruction events and geographic regions,
- Analyzing the impact of different disaster types on optical and radar feature importance,
- Integrating higher-resolution imagery or Sentinel-2 super-resolution approaches,
- And testing the band combinations identified in this study using alternative modeling approaches such as CNNs.

Additional work could also analyze whether radar-only models can be improved through different temporal baselines or preprocessing approaches, and whether specific GLCM texture metrics might be useful under certain band combinations and modeling approaches. 

# Conclusion

This study analyzed the importance of optical and radar-derived Sentinel data for the delineation of urban destruction using XGBoost models. The results demonstrate that carefully selected combinations of optical, especially infrared, bands and radar-derived coherence and backscatter provide the most effective approach for medium-resolution urban destruction delineation.

Among the optical models, infrared bands consistently produced the best results, with SWIR bands in particular showing a very high importance. The addition of SWIR bands significantly improved both recall and precision compared to other RGB-based models, indicating that shortwave infrared wavelengths are highly sensitive to the spectral changes associated with urban destruction, such as exposed concrete, debris, dust, and roof material changes. The study therefore demonstrates the strong contribution of infrared wavelengths for the delineation of urban destruction, with SWIR 2 (Sentinel-2 Band 12) emerging as one of the most important individual bands. While SWIR is already widely used for wildfire and volcanic monitoring (Kato et al., 2021), and its contribution to land cover classification has been studied (Zohaib et al., 2025), its application for urban destruction delineation following earthquakes remains relatively limited. In addition to SWIR, the NIR band (Sentinel-2 Band 8) also remained consistently important for the different models, while its replacement with the narrow NIR band (Sentinel-2 Band 8A) reduced the models' recall but at times improved their precision. Further study is needed to analyze the exact impact a narrower near-infrared band has on destruction delineation. 

Radar-derived coherence and backscatter features substantially improved the performance of the optical-only models, highlighting the importance of combining spectral and structural information. However, radar-only models performed considerably worse than optical or combined models. Coherence, backscatter, and Gray Level Co-occurrence Matrix (GLCM) alone were insufficient for reliable urban destruction delineation within the methodology used in this study. Nevertheless, the comparatively weak performance of radar-only models does not imply that radar-based urban destruction delineation is impossible. Rather, it suggests that the methodology used here, including the relatively small training dataset, limited temporal variability, and the use of XGBoost instead of deep learning approaches, was insufficient to fully exploit the potential of radar-derived information.

The study also demonstrated that increasing the number of bands or attributes does not necessarily improve model performance. Several lower-contributing attributes mainly introduced noise and their removal either maintained or improved the results. Similarly, models containing all Sentinel bands often performed worse than more selective combinations. This highlights the importance of careful feature and band selection when working with medium-resolution remote sensing data.

The best-performing models achieved a recall and precision of roughly 0.7, demonstrating that urban destruction delineation using freely available medium-resolution satellite imagery is possible, even with relatively limited training data. While the models did not reach the initially aspired values of over 0.8 recall and precision, the results remain promising considering the 10–20 m spatial resolution of Sentinel imagery, the complexity of urban destruction patterns, and additional disturbances such as smoke, coastal liquefaction, and inundation. The models performed particularly well for larger building clusters, while small isolated collapses remained difficult to detect due to spatial mixing and resolution limitations.

The unsuccessful transferability test in Morocco highlights that models trained on a single region or event are unlikely to generalize globally without additional geographically diverse training data.

Overall, the results indicate that medium-resolution Sentinel imagery can provide valuable information for rapid urban destruction assessment, especially when infrared optical bands are combined with radar coherence information. The study further suggests that with larger and more geographically diverse training datasets, an increase in pre-event data and the integration of deep learning methods may significantly improve both accuracy and the geographic transferability of the models in future work.

# Bibliography 

Aimaiti, Y., Sanon, C., Koch, M., Baise, L. G., & Moaveni, B. (2022). War Related Building Damage Assessment in Kyiv, Ukraine, Using Sentinel-1 Radar and Sentinel-2 Optical Images. Remote Sensing, 14(24), 6239. https://doi.org/10.3390/rs14246239

Aydin, N. Y., Celik, K., Gecen, R., Kalaycioglu, S., & Duzgun, S. (2025). Rebuilding Antakya: Cultivating urban resilience through cultural identity and education for post-disaster reconstruction in Turkey. International Journal of Disaster Risk Reduction, 117, 105196. https://doi.org/10.1016/j.ijdrr.2025.105196

Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, KDD ’16, 785–794. https://doi.org/10.1145/2939672.2939785

Damcı, E., Temür, R., Kanbir, Z., Şekerci, Ç., & Öztorun Köroğlu, E. (2025). Comprehensive investigation of damage due to 2023 Kahramanmaraş Earthquakes in Türkiye: Causes, consequences, and mitigation. Journal of Building Engineering, 99, 111420. https://doi.org/10.1016/j.jobe.2024.111420

HOTOSM Turkey Destroyed Buildings (OpenStreetMap Export) | Humanitarian Dataset | HDX. (n.d.). Retrieved 24 May 2026, from https://data.humdata.org/dataset/hotosm_tur_destroyed_buildings

Imtiaz, A., Saloustros, S., Beqiraj, M., Cortés, G., Devaux, M., Lattion, E., Zhu, Y., & Sehaqui, H. (2025). Understanding building damage through the lens of the Swiss post-seismic reconnaissance mission of 2023 Al Haouz, Morocco, earthquake. Scientific Reports, 15(1), 16587. https://doi.org/10.1038/s41598-025-00659-2

Kato, S., Miyamoto, H., Amici, S., Oda, A., Matsushita, H., & Nakamura, R. (2021). Automated classification of heat sources detected using SWIR remote sensing. International Journal of Applied Earth Observation and Geoinformation, 103, 102491. https://doi.org/10.1016/j.jag.2021.102491

Lundberg, S., & Lee, S.-I. (2017). A Unified Approach to Interpreting Model Predictions (arXiv:1705.07874). arXiv. https://doi.org/10.48550/arXiv.1705.07874

Morocco quake leaves half of village’s population dead or missing. (2023, September 10). https://www.bbc.com/news/world-africa-66770314
Olen, S., & Bookhagen, B. (2018). Mapping Damage-Affected Areas after Natural Hazard Events Using Sentinel-1 Coherence Time Series. Remote Sensing, 10(8), 1272. https://doi.org/10.3390/rs10081272

Tobita, T., Kiyota, T., Torisu, S., Cinicioglu, O., Tonuk, G., Milev, N., Contreras, J., Contreras, O., & Shiga, M. (2024). Geotechnical damage survey report on February 6, 2023 Turkey-Syria Earthquake, Turkey. Soils and Foundations, 64(3), 101463. https://doi.org/10.1016/j.sandf.2024.101463

Turkey Buildings (OpenStreetMap Export) | Humanitarian Dataset | HDX. (n.d.). Retrieved 24 May 2026, from https://data.humdata.org/dataset/hotosm_tur_buildings

Wang, C., Zhang, Y., Xie, T., Guo, L., Chen, S., Li, J., & Shi, F. (2022). A Detection Method for Collapsed Buildings Combining Post-Earthquake High-Resolution Optical and Synthetic Aperture Radar Images. Remote Sensing, 14(5), 1100. https://doi.org/10.3390/rs14051100

Washaya, P., Balz, T., & Mohamadi, B. (2018). Coherence Change-Detection with Sentinel-1 for Natural and Anthropogenic Disaster Monitoring in Urban Areas. Remote Sensing, 10(7), 1026. https://doi.org/10.3390/rs10071026

Zhu, P., Li, H., Gao, B., Zhao, X., & Wang, Q. (2025). Photovoltaic dust accumulation index: Monitoring PV dust with Sentinel-2 satellite imagery. Energy, 335, 138130. https://doi.org/10.1016/j.energy.2025.138130

Zohaib, Abbas, S., Umar, M., Usman, M., ul Eaza, N., Mahnoor, & Abbas, Z. A. (2025). Assessing the role of Red-Edge and SWIR bands in urban land cover mapping using machine learning: Spectral and spatial resolution trade-offs. GeoJournal, 90(5), 221. https://doi.org/10.1007/s10708-025-11468-5