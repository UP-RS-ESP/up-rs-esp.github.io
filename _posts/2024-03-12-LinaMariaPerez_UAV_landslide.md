---
title: 'Structure from Motion Application for Landslide Characterization and Monitoring'
author: "Lina Pérez"
author_profile: true
date: 2024-03-12
toc: true
toc_sticky: true
toc_label: "Structure from Motion Application for Landslide Characterization and Monitoring"
read_time: false
tags:
  - UAV
  - landslides
  - point cloud 
  - point cloud registration
  - ICP
---

On January 9th, 2023, a catastrophic landslide severely impacted the upper basin of Chontaduro Creek, located in the municipality of Rosas-Cauca in southwestern Colombia. This work investigates landslide velocities and spatial patterns of deformation through repeated UAV flights.


# Introduction

Landslides are natural disasters that can have devastating impacts on human communities and infrastructure. Similar to other natural hazards, their severity can increase due to cascading effects and can be exacerbated by recent global climate changes. Moreover, larger landslides can result in diverse forms of damage and casualties. To address these challenges, advanced technologies such as UAV-based photogrammetry and lidar are used to rapidly and cost-efficiently assess large landslides. However, the precise georeferencing, co-registration, and alignment of UAV surveys collected from different devices with varying resolutions, flight conditions and flight heights as well as varying areal coverage present significant challenges for data analysis. To tackle these challenges, this work explores different methods to ensure accuracy in the pre-processing of this type of data.

*This internship was supervised by Prof. Dr. Bodo Bookhagen.*


# The Rosas-Cauco Landslide

On January 9th, 2023, a catastrophic landslide severely impacted the upper basin of Chontaduro Creek, located in the municipality of Rosas-Cauca in southwestern Colombia (refer to Figure 1). This event caused extensive damage to the communities of La Soledad, Santa Clara, Párraga Viejo, and Chontaduro, resulting in the destruction of at least 150 homes and a significant portion of the Pan-American highway, which connects southern Colombia to the rest of the country. Inhabitants of the region reported their initial observations of instability on January 4th when they noticed small cracks with lengths ranging from 20 cm to 30 cm forming in the crown area near the Alfonso Córdoba school. However, it was not until the period between the afternoon of January 9th and the morning of January 10th that the landslide's progression became starkly evident, leaving distinct markings on both the crown and flanks of the movement. Following this significant event, the landslide exhibited continuous and substantial activity until January 18th. By January 10th, the area affected by the mass movement had expanded to 64.72 hectares, and it further increased to 87.16 hectares by January 13th, ultimately reaching 89.12 hectares by January 18th.

The Rosas landslide, situated in Colombia, has been closely monitored by several government institutions, including the *Unidad Nacional de Gestión del Riesgo* (UNGRD), the Geological Survey of Colombia (SGC), and the National Armed Forces. These agencies have conducted numerous UAV (Unmanned Aerial Vehicle) flights to monitor the ongoing evolution of the landslide. Over the past decade, there has been a notable increase in the utilization of remote sensing technology for landslide mapping and monitoring. This surge in usage has been complemented by significant improvements in the spatial resolution of remote sensing technologies, particularly with the introduction of laser scanning (both airborne and terrestrial) and unmanned aerial vehicles (UAVs) (Niethammer et al., 2012). Earth observation methods are useful to produce detailed multi-temporal sets of images, orthophotos, and digital elevation models (DEMs). These products may provide insight into the flow kinematics such as flow rate, landslide expansion, and accumulation at the toe zone or retreating scarps. In addition, these new techniques allow volume calculations of the accumulated and removed material by the landslide and mapping of the topographic changes (Lucieer et al., 2014).

Furthermore, recent advances in photogrammetric image processing and computer vision have resulted in a technique known as Structure from Motion (SfM). Highly detailed 3D models can be obtained from overlapping multi-view photography with SfM algorithms. While spaceborne and airborne remote sensing techniques are commonly employed for landslide research, these methods may lack the flexibility offered by the novel remote sensing platform of UAVs. When combined with UAV technology, Structure from Motion (SfM) can provide a cost-effective and efficient means of acquiring dense and accurate 3D data of the Earth's surface. In this study, we investigate various methods for processing the extensive UAV data acquired for the Rosas landslide, aiming to produce accurately georeferenced and aligned 3D models.


# Study area

The Rosas landslide occurred in the rural district of La Soledad, located within the municipality of Rosas-Cauca, situated in the southwestern region of Colombia. This region lies within the Patía Valley intercordilleran depression, nestled between the Western Cordillera and the Central Cordillera of Colombia. The primary drainage network affected is that of the Chontaduro creek, a tributary of the Esmita River, which is part of the upper Patía River basin (refer to Figure 1).

<center>
<figure>
<a href="UAV_landslide_figs_PerezRosasStudArea.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/RosasStudArea.jpg"/></a>
<figcaption>Figure 1: Shaded relief map of study area, showing major rivers, towns and a multi-temporal landslide inventory, sourced from SGC (2020)</figcaption>
</figure>
</center>

The study area is situated within the western range of the Colombian Andes, a region characterized by its susceptibility to landslides. This vulnerability arises from a combination of factors including steep terrain, adverse weather conditions, and the presence of soils derived from volcanic deposits originating from the Sotará volcanic complex. A comprehensive study conducted by the Geological Survey of Colombia-SGC (SGC, 2020), examined the development and distribution of landslide in the region. Their investigation identified a total of 273 landslide events occurring within the municipality of Rosas during the period spanning from 1990 to 2019. Of these occurrences, five were deemed severe, leading to tragic casualties, substantial economic losses, and considerable damage to critical infrastructure.

As depicted in Figure 1, the area has a historical record of being affected by landslides of varying magnitudes. However, the Rosas landslide, which is the focal point of our study, stands out as the largest landslide identified in the surrounding region since 1990.

## Geological setting

The geological setting of the study area is profoundly influenced by its location within the Northern Andes, where the convergence of three tectonic plates—the Nazca, Caribbean, and South American plates—gives rise to active N-NE faulting within the Andean block. This convergence, with the Nazca plate moving eastward relative to northwestern South America at a rate of 6 cm/yr, leads to the formation of the Colombia-Trench to the west and the mountain range of the Colombian Andes (Andes Pulido, 2003). Within the Colombian Andes, three distinct mountain ranges—the Western, Central, and Eastern Cordillera—converge southward into a unified range, shaped by deformation and faulting resulting from the interaction of these tectonic plates (Taboada et al., 2000). The study area, encompassing the upper Patía River basin, is situated at the southern Colombian Andes' convergence point between the Western and Central Cordilleras. Here, the Western Cordillera rises dramatically from the Pacific Coastal Plain on its western flank, while to the east, it is separated from the Central Cordillera by the Cauca-Patia valleys spanning a distance of approximately 500 km. The Cauca-Patia valley, resembling a graben-like structure, is characterized by an asymmetric tilt and is filled with Tertiary-Quaternary continental clastics and volcanics. Bounded by the Cauca fault zone to the west and the Romeral fault zone to the east, this depression effectively separates the oceanic Western Cordillera from the ancient crystalline Central Cordillera (Figure 2).

<center>
<figure>
<a href="UAV_landslide_figs_PerezGELOGY.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/GELOGY.jpg"/></a>
<figcaption>Figure 2: Geological map of the study area. Sourced from SGC (2020). </figcaption>
</figure>
</center>


# Landslide event characterization

The Rosas mass movement, situated within the micro-basin of Chontaduro creek, is characterized as an active rotational landslide of a complex nature, exhibiting retrogressive and widening behavior. This landslide initiation point is positioned 900 meters from the summit of Broncazo Hill and 700 meters from its base (Figure 3).

<center>
<figure>
<a href="UAV_landslide_figs_Perezlandslide1.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/landslide1.png"/></a>
<figcaption>Figure 3: Panoramic view of Rosas landslide. Sourced from SGC (2023).</figcaption>
</figure>
</center>

The landslide displays distinct patterns of movement and failure mechanisms across its various sections. In the uppermost region, known as the crown, where the movement commences, displacements are attributed to a rotational failure mechanism. Moving to the flanks, which constitute the lateral sides of the landslide, translational faults predominate. Within the body of the landslide, one observes intense deformation, sinking, and the formation of cracks, both transverse and parallel to the primary crown (Figure 4). In the lowermost part of the movement, termed the toe, situated furthest from the crown, translational landslides, soil block falls, and flows of earth, debris, and mud have been observed. These flows are channeled through areas with lower slopes. The dynamic interplay of these movements signifies the complex nature of the landslide, with its activity and behavior evolving in response to variations in water availability in the upper part of the basin.

<center>
<figure>
<a href="UAV_landslide_figs_Perezlandslide-detail.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/landslide-detail.jpg"/></a>
<figcaption>Figure 4: Identifiable characteristics across the crown, body, and toe of the landslide: 1) A curved concave rupture surface creating a scarp measuring up to 20 meters in height. 2) Presence of tilted blocks, subsidence, and formation of cracks. 3) Occurrence of translational slides and debris flows.</figcaption>
</figure>
</center>


## Geology and failure surface

The initial phase of the mass movement was characterized by a rotational slide, evidenced by a semicircular curved and concave upward rupture surface. This phase exposed a steep slope scarp reaching heights of up to 40 meters (SGC, 2023), composed of alternating layers of residual ash soils and pyroclastic flows from the Galeón Formation. Subsequently, a portion of the body adjacent to the crown tilted backward due to the concavity of the failure surface, resulting in ground subsidence. When the central region of the landslide became fully saturated with water, copious flows of earth and rock emanated from both sides of the landslide, as well as from its center.

In the microbasin of Chontaduro creek, a geological sequence unfolds, comprising both epiclastic and volcanic rocks attributed to the Galeón Formation (TQpg). Notably, these formations are prominently exposed in areas such as Cerro Broncazo and its environs, encompassing the Quilcacé and Esmita rivers. In these regions, the volcaniclastic deposits can attain substantial thicknesses, reaching up to 800 meters (SGC, 2020).

<center>
<figure>
<a href="UAV_landslide_figs_PerezSlide4.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/Slide4.jpg"/></a>
<figcaption>Figure 5: Lithological sequence and unit details observed at the crown of the landslide.</figcaption>
</figure>
</center>

The scarp of the crown provided a clear view of the sequential arrangement of materials comprising the mobilized mass. Illustrated in Figure 5 and Figure 6, from bottom to top, the lithological units are delineated as follows:

-   The base layer showcases rocks attributed to well-selected, sandy, hyperconcentrated lahar deposits, linked with the Galeón formation.
-   Directly above lies a layer of clast-supported pyroclastic flows, featuring rounded volcanic rock clasts with subtle orientation indicative of flow, ensconced within a reddish sandy volcanic ash matrix.
-   Progressing upward, there exist lenticular alluvial and colluvial deposits, resulting from the erosion and transportation of various units within the Galeón formation.
-   Finally, at the apex of the sequence, residual soils stemming from both transport deposits and pyroclastic flows are evident.

<center>
<figure>
<a href="UAV_landslide_figs_PerezSlide3.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/Slide3.jpg"/></a>
<figcaption>Figure 6: Panoramic view of landslide crown scarp. Blue dashed line depicting the water horizon</figcaption>
</figure>
</center>

As depicted in Figure 6, a highly saturated surface conducive to water flow manifests between the hyperconcentrated flow layer and the pyroclastic flow layer. The permeability of the latter, coupled with the slight permeability of the underlying layer, facilitates water flow across this contact surface. Exhibiting horizontal continuity, this surface could be associated with the sliding surface of the mass movement.Recurrence of the poorly permeable hyperconcentrated lahar layer is notable at the base of the slide, indicating a seamless continuation of the water-saturated surface from the crown to the landslide's base.

Furthermore, noteworthy is the close proximity of the landslide's crown to the 'Alto de las Yerbas' fault line, as referenced in the technical report on Landslide Hazard Zoning by the SGC (2020), detailed in Figure 7. Findings from the present study imply that structural and lithological factors, compounded by intense rainfall, were the primary catalysts for the occurrence of this significant landslide.

<center>
<figure>
<a href="UAV_landslide_figs_PerezUAV_landslide_figs_Perezgeolandslide.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/geolandslide.png"/></a>
<figcaption>Figure 7: Geological surface units and main fault in the landslide site. Sourced from SGC (2020).</figcaption>
</figure>
</center>

## Rainfall as trigger mechanism

According to the Atlas of Colombia (IGAC, 2012), the region experiences an average annual rainfall of 2,000 mm at the summit of the Central Cordillera and 3,000 mm at the summit of the Western Cordillera. Rainfall patterns indicate a distinct summer season during June, July, August, and September, followed by a rainy season during the remaining months. The precipitation data for the study area was obtained from the Párraga weather station (Station Code: 52010050), which is managed by IDEAM (Instituto de Hidrología, Meteorología y Estudios Ambientales de Colombia). The time series analyzed encompasses 33 years of recorded data, spanning from 1990 to 2023 (Figure 8 shows the last 20 years of data). As shown in Figure 8, the study area experiences two distinct rainy seasons: the first occurs from January to May, characterized by relatively lower rainfall compared to the second rainy season, which typically occurs between October and December.

An important observation to highlight is that within the last 20 years of recorded data, the rainfall during the rainy season of December 2022, preceding the event, was notably exceptional. In November 2022 alone, precipitation levels reached a record high of up to 720 mm, marking it as the highest recorded rainfall within the observed period.

<center>
<figure>
<a href="UAV_landslide_figs_PerezUAV_landslide_figs_PerezmonthlyPre.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/monthlyPre.png"/></a>
<figcaption>Figure 8: Visualization of total monthly rainfall at the Parraga meteorological station spanning the past 20 years. Blue bars represent months with rainfall above the mean, while green bars denote months with precipitation below the mean.</figcaption>
</figure>
</center>

In the other hand, the daily time series recorded at the Párraga station exhibits a range of maximum daily precipitation values, varying between 0 mm and 95 mm. The highest recorded value, 94.8 mm, was documented on January 9th, which coincided with the onset of the landslide event (Figure 9). The cumulative rainfall data was computed over the last 60 days leading up to the triggering of the landslide, revealing an impressive total rainfall accumulation of 2309.3 millimeters recorded up to January 9, 2023 (Figure 9).

<center>
<figure>
<a href="UAV_landslide_figs_PerezUAV_landslide_figs_PerezDailyRainfall.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/DailyRainfall.png"/></a>
<figcaption>Figure 9: Total daily and accumulated rainfall at the Parraga meteorological station.</figcaption>
</figure>
</center>


# Methods

Aerial digital photographs of the landslide were captured on multiple occasions between January 9th and March 18th. Predominantly, these flights were conducted at an altitude of 250 meters. Over the span of 17 days, a total of 22 flights were executed by three organizations specializing in risk management and emergency disaster response: Unidad Nacional para la Gestión del Riesgo (UNGRD), Servicio Geológico Colombiano (SGC), and Policía Nacional (PNAL). Despite the involvement of various institutions, uniformity was maintained in the equipment used, ensuring consistent resolution in the photographs. However, aspects such as flight altitude, coverage area, flight plan design, and the number of captured images exhibited significant variation.

A further challenge encountered in the data acquisition process was the georeferencing of the flights. During the initial flights, markers were not employed, leading to difficulties in precise location mapping. To address this, on May 18th, a set of markers was installed to ensure at least one flight could be accurately georeferenced. However, these newly placed markers proved too small to be discernible in images taken from higher altitudes. Consequently, to enhance the overall georeferencing accuracy of all flights, an independent survey was executed as part of this study, utilizing natural points as reference markers in the final survey.

## Point Cloud Generation

The Structure from Motion (SfM) method uses algorithms to identify matching features in a series of overlapping digital images and calculates camera location and orientation from the differential positions of multiple matched features. From these calculations, overlapping imagery is then used to reconstruct a “sparse” or “coarse” 3D point cloud model of the photographed object or surface or scene (Brook et al., 2019). The software *Agisoft Metashape* was used to undertake the SfM processing. In Metashape, the SFM processing comprises three key steps (Agisoft, 2023):

1.  *Alignment*: Involves aerial triangulation and bundle block adjustment, where the software identifies feature points on images, matches them into tie points and determine camera positions, resulting in a tie point cloud and camera positions for depth map determination and 3D reconstruction.
2.  *Surface Generation*: Creates a 3D mesh or 2.5D digital elevation model (DEM), combining photogrammetric depth maps and LiDAR data, which can be textured and exported for various applications.
3.  *Orthomosaic Creation*: Generates a georeferenced orthomosaic by projecting images onto a chosen surface (DEM or mesh), useful for mapping and analysis, including vegetation indices in multispectral imagery projects.

In this study we adopted the workflow implemented in Agisoft Metashape, described in the User Manual v2.0 (Agisoft, 2023). The parameters used are described n the following sections.

## Image loading and chunks definition

Sixteen distinct chunks were produced by importing photographs from selected flights (refer to Table 1), of which five met key selection criteria: a sufficient quantity of photographs, high image quality characterized by proper exposure and sharpness, and extensive coverage of the landslide area. This careful selection was necessary as some flights were tasked with monitoring more restricted sectors of the mass movement, targeting specific areas such as the crown or the Pan-American Highway. For comprehensive area coverage and improved model resolution during that timeframe, photographs from January 18th and 19th were merged in one single chunk.

| Chunks       | Cameras | Points    | Markers    | Processed |
|--------------|---------|-----------|------------|-----------|
| 1/14/2023    | 1491    | 880,613   | 19 markers | X         |
| 1/17/2023    | 567     | 436,618   | 4 markers  |           |
| 1/18-19/2023 | 878     | 1,666,175 | 17 markers |           |
| 1/19/2023    | 369     | 387,054   |            | X         |
| 1/20/2023    | 196     | 194,101   |            |           |
| 1/26/2023    | 332     | 352,573   |            |           |
| 1/30/2023    | 321     | 351,487   |            |           |
| 2/3/2023     | 418     | 403.19    |            |           |
| 2/6/2023     | 331     | 336,810   |            |           |
| 2/11/2023    | 576     | 627,729   |            |           |
| 2/16/2023    | 329     | 346,862   |            |           |
| 2/19/2023    | 442     | 459,783   |            |           |
| 3/6/2023     | 330     | 324,661   |            |           |
| 3/21/2023    | 331     | 352.909   |            |           |
| 3/30/2023    | 328     | 327,605   |            |           |
| 5/18/2023    | 333     | 243,261   |            |           |

*Table 1: Point clouds generated in Agisoft.*

## Photos alignment and filtering

In each chunk, the photographs underwent an alignment process with the accuracy setting set to high, utilizing equipment source coordinates as a reference point. Camera optimization was conducted, selecting the estimation of the covariance of tie points. Subsequently, apparent outliers were removed from the sparse cloud manually to diminish potential reconstruction inaccuracies. Additional refinement was carried out by filtering based on tie point covariance and uncertainties, employing Metashape's integrated Python scripting capabilities for a more precise adjustment (Figure 10).

<center>
<figure>
<a href="UAV_landslide_figs_PerezUAV_landslide_figs_Perezcovariance.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/covariance.png"/></a>
<figcaption>Figure 10: Tie point covariances obtained after filtering.</figcaption>
</figure>
</center>

## Dense Point Cloud generation

For all chosen chunks, a dense 3D point cloud was constructed employing high-quality settings and mild depth filtering. This detailed point cloud serves as the foundation for generating Digital Surface Models (DSM) and orthomosaics. Additional settings were selected to reuse depth maps, calculate point colors and calculate point confidence (Figure 11).

<center>
<figure>
<a href="UAV_landslide_figs_PerezUAV_landslide_figs_Perezdenseall.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/denseall.png"/></a>
<figcaption>Figure 11: Dense point cloud generated for 14/01/2023 survey</figcaption>
</figure>
</center>

## Natural points definition and GNSS survey

To accurately reference the point clouds, a series of natural markers were established to guarantee high-precision (centimeter-level) localization that was readily identifiable in the field. Utilized reference points included distinct features such as sewer edges, fence corners, and light posts (see Figure 12). Out of the 27 natural markers delineated (see Figure 13), only 21 were successfully surveyed on-site. The survey faced several challenges, including the demolition of referenced structures, obscuring of markers by debris or soil, and inaccessible locations of certain points. The coordinates for each marker were recorded using a Trimble SPS855 GNSS Modular Receiver.

<center>
<figure>
<a href="UAV_landslide_figs_Perezmarker12.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/marker12.png"/></a>
<figcaption>Figure 12: Example of a marker defined</figcaption>
</figure>
</center>

<center>
<figure>
<a href="UAV_landslide_figs_Perezmarkers.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/markers.png"/></a>
<figcaption>Figure 13: Markers defined. Green points represent the markers defined and recorded during field work</figcaption>
</figure>
</center>

Following the download of raw data from the Trimble receiver, the post-processing software GrafNav was employed. GrafNav is an advanced GNSS post-processing suite that supports kinematic and static analysis with an advanced processing engine for GPS, GLONASS, and BeiDou signals. To refine the data, corrections were applied using the Popayan station (POPA), which is the station nearest to the collection site. The required data were acquired from the Colombian open data portal (<https://www.colombiaenmapas.gov.co/>). Both the RINEX files from the field-surveyed markers and the permanent station were inputted into GrafNav to execute the correction process. The precision-adjusted positions of the markers are shown in Table 2 and Figure 14.

<center>
<figure>
<a href="UAV_landslide_figs_PerezGNSS_grafnav.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/GNSS_grafnav.png"/></a>
<figcaption>Figure 14: Points depict the resulting standard deviation for horizontal and height measurements, while bars illustrate a quality metric established by GrafNav.</figcaption>
</figure>
</center>

As depicted in Figure 14, both the resulting horizontal and vertical standard deviations are below 0.656 meters, with mean values of 0.26 and 0.14 meters, respectively. Achieving accuracy at the centimeter level indicates favorable results. However, a metric of quality provided by Grafnav offers additional insight. This metric assigns values as follows:

-   Quality 1: Represents a fixed integer solution with excellent satellite geometry.
-   Quality 2-3: Indicates either fixed integers with marginal geometry or converging float solutions.
-   Quality 4-5: Suggests qualities akin to those of DGPS.
-   Quality 6: Represents a coarse acquisition (C/A) only solution.

The majority of solutions fall within the quality range of 2-3, with one solution (marker 1) exhibiting a very good quality of 1 and another (marker 10) displaying a poor quality of 6. All solutions showed satisfactory results and were subsequently utilized in the following step, which involves the precise alignment of point clouds based on markers.

| **Date**  | GPSTime | **Easting** | **Northing** | **H-Ell** | **H-MSL** | **Q** | SDHoriz | **SDHeigh (m)** | **Marker** |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| 8/09/2023 | 32:23.0 | 302995,460  | 248590,161   | 1514963   | 1486998   | 1     | 0,016   | 0,028           | 1          |
| 8/09/2023 | 59:34.0 | 302445,401  | 247995,626   | 1346507   | 1318573   | 3     | 0,12    | 0,072           | 12         |
| 8/09/2023 | 32:47.0 | 302540,380  | 247938,191   | 1342117   | 1314170   | 5     | 0,559   | 0,402           | 13         |
| 8/09/2023 | 50:24.0 | 302928,080  | 248596,004   | 1508566   | 1480608   | 3     | 0,18    | 0,112           | 2          |
| 8/09/2023 | 01:48.0 | 302956,219  | 248607,942   | 1512854   | 1484894   | 4     | 0,367   | 0,129           | 25         |
| 8/09/2023 | 25:50.0 | 302984,155  | 248601,450   | 1513498   | 1485535   | 5     | 0,257   | 0,13            | 3          |
| 8/10/2023 | 53:34.0 | 302155,060  | 247741,470   | 1338077   | 1310161   | 6     | 0,291   | 0,181           | 10         |
| 8/10/2023 | 26:29.0 | 302045,545  | 247650,392   | 1328182   | 1300273   | 3     | 0,347   | 0,215           | 21         |
| 8/10/2023 | 29:50.0 | 302207,493  | 247767,666   | 1341687   | 1313767   | 2     | 0,243   | 0,138           | 23         |
| 8/10/2023 | 03:19.0 | 302229,752  | 247892,380   | 1344103   | 1316187   | 3     | 0,343   | 0,217           | 24         |
| 8/10/2023 | 10:53.0 | 301981,062  | 248881,942   | 1547867   | 1520018   | 3     | 0,263   | 0,137           | 26         |
| 8/10/2023 | 58:14.0 | 301798,636  | 248108,698   | 1446887   | 1419024   | 3     | 0,19    | 0,117           | 4          |
| 8/10/2023 | 09:31.0 | 301847,911  | 248155,130   | 1446869   | 1419003   | 3     | 0,364   | 0,186           | 6          |
| 8/10/2023 | 31:22.0 | 301868,008  | 248170,170   | 1446827   | 1418960   | 3     | 0,147   | 0,072           | 7          |
| 8/10/2023 | 30:20.0 | 301875,048  | 248297,576   | 1452434   | 1424571   | 3     | 0,235   | 0,161           | 8          |
| 8/10/2023 | 00:47.0 | 301968,070  | 248386,332   | 1451916   | 1424048   | 4     | 0,235   | 0,09            | 9          |
| 8/11/2023 | 58:29.0 | 301263,276  | 246688,966   | 1308378   | 1280506   | 4     | 0,656   | 0,64            | 17         |
| 8/11/2023 | 40:23.0 | 301456,505  | 246350,882   | 1292738   | 1264830   | 2     | 0,054   | 0,055           | 18         |
| 8/11/2023 | 04:19.0 | 301430,773  | 246394,964   | 1296034   | 1268131   | 2     | 0,077   | 0,064           | 19         |
| 8/11/2023 | 30:58.0 | 301364,741  | 246498,245   | 1300102   | 1272211   | 4     | 0,364   | 0,259           | 20         |
| 8/11/2023 | 34:20.0 | 301586,893  | 247430,776   | 1319567   | 1291696   | 5     | 0,604   | 0,323           | 27         |

*Table 2: GNSS data corrected in Grafnav.*

## Chunk alignment

For a precise alignment of point clouds, the process begins with the correction of a designated reference point cloud; in this case, the cloud dated 01/14/2023 is used. The coordinates of the markers are revised using the data acquired from the recent field campaign. Following this update, camera parameters are re-optimized, and a new dense point cloud is generated. This newly referenced point cloud then serves as the reference for aligning subsequent point clouds through the point-based method, a technique available to align chunks within *Agisoft*.

Despite this registration, some misalignment persist. To address this, some pre-filtering steps and global registration methos are appied to subsequently apply a meticulous registration is conducted using the Iterative Closest Point (ICP) method, elaborated in the following sections.

## Pre-processing and Global registration

The registration process was exclusively conducted within the stable zones identified within the study area. By avoiding regions experiencing landslide activity, where the terrain undergoes constant changes, we ensure a precise correlation between zones exhibiting minimal alterations over time. The stable areas from both the reference and target point clouds were manually selected and extracted using *Cloud Compare*.

Subsequently, pre-registration steps were performed on these stable area point clouds, including:

1.  **Initial Filtering Step**: This involved the removal of statistical outliers using an Open3D function. Points that deviate significantly from the average distance to their neighbors were identified as outliers and removed. This step was iterated until all points not forming a continuous surface were eliminated.

2.  **Nearest Neighbor Distance Calculation**: Next, KDtree was employed to compute the nearest neighbor distances between both point clouds (Figure 15). In some regions where there was a lack of overlapping between the point clouds, resulting distances exceeded 3 meters. To address this issue and ensure complete overlap, points farther than 3 meters from one point cloud to the other were filtered out.

<center>
<figure>
<a href="UAV_landslide_figs_Perezinitialdistance.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/initialdistance.png"/></a>
<figcaption>Figure 15: Nearest neighbor distances between both point clouds.</figcaption>
</figure>
</center>

After the initial filtering step, the alignment process proceeds with an initial coarse alignment to bring the point clouds into close proximity. This alignment method incorporates feature identification to refine the search for corresponding points. This process generally involves two key steps:

1.  **Utilizing Fast Point Feature Histograms (FPFH)**: FPFH is a technique employed in 3D registration, which aims to align multiple 3D point clouds. FPFH analyzes each point in a 3D point cloud by examining its surrounding points. It computes a histogram describing the geometric features of each point based on its neighbors, encompassing attributes like angle and distance between neighboring points. FPFH facilitates the matching of points across different 3D scenes by leveraging the geometric properties of each point and its surroundings (Rusu et al., 2011).

2.  **Application of *registration_ransac_based_on_feature_matching* Function**: Open3D's `registration_ransac_based_on_feature_matching` function implements the RANSAC (Random Sample Consensus) algorithm tailored for point cloud registration via feature matching. RANSAC randomly selects a minimal subset of points from both point clouds to estimate a transformation, such as rotation and translation, between them (Fischler et al., 1981). Subsequently, the estimated transformation is evaluated by applying it to all feature correspondences obtained in the previous step, and the number of inliers—correspondences consistent with the estimated transformation—is tallied.

In essence, these refined alignment techniques enable the accurate registration of point clouds by iteratively estimating transformations based on feature correspondences, thereby enhancing the robustness and accuracy of the alignment process. Although the global alignment has improved the distribution of distances, as depicted in Figure 16, with a mean value of less than 2 meters, the Global Registration Modified Hausdorff Distance has increased to 3.75 meters. This discrepancy underscores the necessity for a more precise registration process to minimize the offset between the two point clouds.

<center>
<figure>
<a href="UAV_landslide_figs_Perezglobalregistration.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/globalregistration.png"/></a>
<figcaption>Figure 16: Nearest neighbor distances between both point clouds before and after global registration.</figcaption>
</figure>
</center>

## ICP registration

Unlike global alignment, fine registration methods require two point clouds that already have a rough correspondence. The Iterative Closest Point (ICP) algorithm is commonly used for local refinement and has two main variants:

**Point-to-point ICP**

The Iterative Closest Point (ICP) algorithm, introduced in the early 1990s by various authors (Besl et al. (1992), Chen et al. (1992), Zhang (1994)), stands out among the myriad registration methods proposed in the literature. It has become one of the most well-known for efficiently registering two 2D or 3D point sets under Euclidean (rigid) transformation.

The process follows a simple concept (Yang et al., 2015):

1.  Begin with an initial transformation involving rotation and translation.

2.  Alternate between two steps:

    a.  Establish closest-point correspondences under the current transformation.

    b.  Estimate a new transformation using these correspondences.

3.  Repeat steps 2a and 2b until convergence is achieved.

Notably, the point-to-point ICP method is capable of directly processing the raw point sets without regard to their inherent characteristics, such as distribution, density, and noise level.

The `registration_icp` function of *Open3D* aligns both stable-area point clouds using the global transformation matrix from the previous step via ICP registration. subsequently, we use the `evaluate_registration` function that calculates two key metrics: **Fitness**, that measures overlapping area (\# of inlier correspondences / \# of points in target), higher values indicate better alignment. And **Inlier RMSE**, that measures RMSE of all inlier correspondences with lower values indicating better alignment.

As depicted in Figure 17, the final registration demonstrates excellent performance, with mean distances smaller than 50 centimeters. Subsequently, the final transformation matrix derived from this registration is applied to the full dataset, encompassing both stable and landslide areas.

<center>
<figure>
<a href="UAV_landslide_figs_Perezfinalregistration.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/UAV_landslide_figs_Perez/finalregistration.png"/></a>
<figcaption>Figure 17: Nearest neighbor distances between both point clouds before and after global registration and ICP registration.</figcaption>
</figure>
</center>

In Table 3, a comprehensive overview of the effectiveness of various registration methods in enhancing the alignment of point clouds is provided. By meticulously examining the metrics presented in the table, including distances between corresponding points before and after registration, the impact of each method on the alignment quality becomes evident.

|                         | Hausdorff Distance | Modified Hausdorff Distance |
|-------------------------|:------------------:|:---------------------------:|
| Before global alignment |       154.51       |         3.312067224         |
| After global alignment  |       145.26       |            3.75             |
| After ICP               |         \-         |            2.41             |

*Table 3: Hausdorff and Modified Hausdorff distance calculated throughout the registration process*

# Key project insights

-   Regarding the GNSS survey, various points for improvement were identified. Allocating more time to conduct the survey offers the opportunity to collect data under optimal conditions, ensuring minimal cloud cover for improved satellite connectivity. It's highly recommended to avoid locations with high environmental noise, although in densely populated areas like the study site, finding such sites proved challenging. Natural landmarks, initially identified using high-resolution orthophotos, were utilized; however, a more efficient method for accurately georeferencing UAV-generated models involves setting markers during flight execution. Some markers selected during pre-field preparations had disappeared or changed by the time of the GNSS survey, posing a limitation to the method.

-   The heterogeneity in data acquisition, spanning different UAV devices, flight heights, number of photos captured, varying point density within and between point clouds, and distinct spatial extents, poses challenges during post-processing and alignment.

# References

Agisoft. (2023). Metashape professional 2.0 user manual. Retrieved from [https://www.agisoft.com/pdf/metashape-pro\_2\_0\_en.pdf](https://www.agisoft.com/pdf/metashape-pro_2_0_en.pdf)

Besl, P. J., & McKay, N. D. (1992). Method for registration of 3-d shapes. Sensor Fusion IV: Control Paradigms and Data Structures, 1611, 586–606.

Brook, M. S., & Merkle, J. (2019). Monitoring active landslides in the auckland region utilising UAV/structure-from-motion photogrammetry. Japanese Geotechnical Society Special Publication, 6(2), 1–6.

Chen, Y., & Medioni, G. (1992). Object modelling by registration of multiple range images. Image and Vision Computing, 10(3), 145–155.

Fischler, M. A., & Bolles, R. C. (1981). Random sample consensus: A paradigm for model fitting with applications to image analysis and automated cartography. Communications of the ACM, 24(6), 381–395.

IGAC. (2012). Atlas geográfico. In Obtenido de <http://atlasgeografico.net/departamento-del-meta.html>.

Lucieer, A., Jong, S. M. de, & Turner, D. (2014). Mapping landslide displacements using structure from motion (SfM) and image correlation of multi-temporal UAV photography. Progress in Physical Geography, 38(1), 97–116.

Niethammer, U., James, M., Rothmund, S., Travelletti, J., & Joswig, M. (2012). UAV-based remote sensing of the super-sauze landslide: Evaluation and results. Engineering Geology, 128, 2–11.

Pulido, N. (2003). Seismotectonics of the northern andes (colombia) and the development of seismic networks. Bulletin of the International Institute of Seismology and Earthquake Engineering, Special Edition, 69–76.

Rusu, R. B., & Cousins, S. (2011). 3d is here: Point cloud library (pcl). 2011 IEEE International Conference on Robotics and Automation, 1–4.

SGC. (2020). ZONIFICACIÓN DE AMENAZA POR MOVIMIENTOS EN MASA EN EL MUNICIPIO DE ROSAS – CAUCA ESCALA 1:25.000.

SGC. (2023). Informe visita de emergencia a la microcuenca de la quebrada chontaduro y concepto técnico sobre el trazado alterno de la vía panamericana – municipio de rosas, departamento del cauca. Bogotá, enero de 2023.

Taboada, A., Rivera, L. A., Fuenzalida, A., Cisternas, A., Philip, H., Bijwaard, H., Olaya, J., & Rivera, C. (2000). Geodynamics of the northern andes: Subductions and intracontinental deformation (colombia). Tectonics, 19(5), 787–813.

Yang, J., Li, H., Campbell, D., & Jia, Y. (2015). Go-ICP: A globally optimal solution to 3D ICP point-set registration. IEEE Transactions on Pattern Analysis and Machine Intelligence, 38(11), 2241–2254.

Zhang, Z. (1994). Iterative point matching for registration of free-form curves and surfaces. International Journal of Computer Vision, 13(2), 119–152.
