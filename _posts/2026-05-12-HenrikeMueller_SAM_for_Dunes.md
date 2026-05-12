---
title: 'Dune Detection using the Meta Segment Anything Model'
author: "Henrike Müller"
author_profile: true
date: 2026-05-11
toc: true
toc_sticky: true
toc_label: "Dune Detection using SAM2"
header:
  overlay_image:"https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/Google_earth.jpg?raw=true"
  overlay_filter: 0.3
  caption: "Barchan Dunes in Morocco (source: Google Earth)"
read_time: false
tags:
  - 
---

# Introduction

Barchan dunes are primarily found in areas with a limited sand supply and consistent, unidirectional wind throughout the year. They are characterized by a moon-like, crescent shape (Bristow, 2019) and are the only migratory dune type whose entire sand mass shifts with the wind direction (Brunotte et al., 2001). A barchan consists of a windward slope, formed by sand grains transported uphill by saltation (Brunotte et al., 2001), and a slip surface on the lee side (Mahmoud, 2022). These dunes occur in arid regions worldwide, including Peru, Namibia, and Morocco (Sauermann et al., 2000).

In Morocco, the rapid movement of barchan dunes is considered an environmental and socioeconomic problem (Dakir et al., 2016), as silting threatens settlements, oases, and various types of infrastructure (Elbelrhiti et al., 2023). Different regions of Morocco face distinct challenges. For example, in the southeast of the country, oasis agricultural systems are threatened by the silting of palm groves, which serve as a protective barrier (Kacem et al., 2025). In the Atlantic Sahara region, silting disrupts economic activity by clogging harbors, halting fishing operations, and causing maritime accidents, which can also lead to ecological consequences. Furthermore, it impacts terrestrial life by burying roads and buildings, forcing migration, and incurring high maintenance costs (Elbelrhiti et al., 2023). Given these widespread impacts, monitoring dune movements is a significant concern.

Remote sensing methods are often useful for investigating vast areas like the Moroccan desert. Consequently, various studies have already investigated dune morphology and movement using satellite imagery and aerial photographs (Ben Kacem et al., 2025; Dakir et al., 2016; Elbelrhiti et al., 2008; Mahmoud, 2022). A few of these studies implemented workflows for the automatic extraction of dunes and their movements using machine learning approaches. However, these approaches still rely on manual input, either during the collection of training data (Mahmoud, 2022) or during post-classification refinement steps (Dakir et al., 2016).

Against this background, the aim of this internship was to develop a more automated workflow for identifying and delineating dune features, with a focus on the Atlantic Sahara region of Morocco. In particular, the potential of the Segment Anything Model 2, developed by Meta Platforms, was investigated and tested on Sentinel-2 imagery. Segment Anything is a pre-trained image segmentation algorithm, making it very efficient to use. The question to investigate is whether this generally trained model can complete such a specific segmentation task.

# Regional Settings

The selected study area is part of the Atlantic Sahara region and the Tarfaya-Laayoune basin, located in southwest Morocco. Between the cities of Tarfaya and Laayoune lies the longest barchan dune field on Earth, consisting of different dune corridors (Elbelrhiti et al., 2008). The formation and persistence of barchan dunes require a specific combination of conditions, including a limited sand supply, a consistent unidirectional wind regime, and a firm, vegetation-free surface (Brunotte et al., 2001). All these conditions are perfectly met in the study area.

In Morocco’s coastal regions, beaches are the primary source of sand. However, these are frequently interrupted by coastal cliffs, which act as barriers and limit the transport of sand inland (Elbelrhiti et al., 2023). One of the main sediment sources feeding the dune corridors of the Atlantic Sahara is Cap Juby, located north of Tarfaya, where sand is mobilized by wind, initiating the formation of proto-dunes (Elbelrhiti, 2012). With a resultant drift potential of 0.91, the region exhibits one of the most unimodal wind regimes worldwide (Elbelrhiti, 2012). The dominant winds come from the northwest (337°) and largely match the observed direction of dune migration in this region (Elbelrhiti et al., 2008). Another essential condition is provided by the hard, vegetation-free surface that characterizes the area. The platform, known as the Dalle Moghrébienne, consists of a Plio-Pleistocene sandy limestone that facilitates the migration of barchan dunes (Elbelrhiti et al., 2023).

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/study_area.png?raw=true">
  <figcaption><b>Figure 1</b> Cropped Sentinel image of the study area with regional context provided by an OpenStreetMap basemap.</figcaption>
</figure>

# Data and Methods

## Segment Anything

Developed by Meta AI, the Segment Anything Model (SAM) is a foundation model for image segmentation, generating high-quality masks for a huge variety of images and objects. SAM was trained on over 11 million images and 1.1 billion masks (Kirillov et al., 2023), using a data engine consisting of different steps, moving from manual assistance to full automation during the collection of the training masks. This diversity of training lays the groundwork for SAM's unique zero-shot transfer, which allows the model to be applied to new images and tasks not seen in training (Kirillov et al., 2023). The model’s transformer architecture consists of three components: a heavy-weight image encoder and mask encoder, as well as a light-weight mask decoder.

Applying the model as a user requires minimal input—specifically, just the image. The standard model, delivered as the “Automatic Mask Generator,” sets a raster of 32 x 32 input points on the images and uses them as seed points for mask generation. However, the density of the raster can be controlled along with other parameters. These include, for example, thresholds for mask prediction quality and stability (e.g., pred_iou_thresh, stability_score_thresh), and filtering criteria for overlapping masks using non-maximum suppression (e.g., box_nms_thresh). Beyond this automated approach, a characteristic feature of SAM is its promptable nature. Prompts can be provided in the form of positive and negative points, bounding boxes, or input masks.

For this project, the updated version SAM2 was used, which builds upon the original model by improving efficiency and enabling the processing of sequential data, thereby allowing segmentation to be extended from static images to video and multi-temporal image analysis (Ravi et al., 2024).

Nevertheless, SAM exhibits some weaknesses that need to be considered when applying it. Firstly, the encoder uses a maximum resolution of 1024x1024 pixels, and larger images are downsampled internally. This means that the size of the input images is important for the quality of the mask output. Furthermore, during training, it became apparent that the model often overlooked smaller features and hallucinated small, unconnected features (Kirillov et al., 2023).

The method was developed using Sentinel data obtained from the Copernicus Data Space Ecosystem. The selected study area is fully covered by tile 28RFR, and Level-2A (bottom-of-atmosphere reflectance) products were used for the analysis. The image used was sensed on January 16, 2025.

During the workflow creation process, Landsat data was also tested, but due to the higher spatial resolution, the decision was made to use Sentinel imagery.

## Preprocessing

The functionality of the Segment Anything Model requires a few preprocessing steps before being able to feed images into the algorithm. SAM’s image encoder uses an internal resolution of 1024x1024 pixels (Kirillov et al., 2023), which leads to a downsampling of input images with a higher resolution. To avoid an internal resampling process, tiling the image was essential. However, due to SAM's lower performance on smaller objects (Kirillov et al., 2023), it was necessary to artificially increase the size of the dune objects before creating the tiles. This was achieved by resampling the image. By increasing the resolution of the image fivefold, each dune feature is represented by a greater number of pixels and is easier for SAM to detect. Lanczos interpolation was chosen as the resampling method, as it preserves details in high quality (Erdnüß & Müller, 2020). The tiles were then created from the resized image with the required size of 1024x1024 and an overlap of 200 pixels.

Dunes often show very subtle intensity or texture differences compared to their surroundings. To better distinguish between dune and background, adaptive histogram equalization was applied to each tile. CLAHE (Contrast Limited Adaptive Histogram Equalization) separates the image into 8x8 tiles and applies histogram equalization to each of these blocks. To avoid over-amplifying noise signals, a contrast limit is set, distributing every bin that is above that limit uniformly to other bins. In a final step, the equalized blocks are combined using bilinear interpolation to remove borders (OpenCV). The results of this filtering step are exemplified in Figure 2.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/clahe.jpg?raw=true">
  <figcaption><b>Figure 2</b> Comparison between (A) original image and (B) contrast-enhanced image.</figcaption>
</figure>

For method development, a limited number of tiles were chosen due to the heterogeneity of the general area of interest. The aim of this work is to develop a workflow for the detection of barchan dunes and to lay the groundwork for possible tracking. However, the chosen area of interest includes dunes in different states, including many coalescent dunes, as well as various non-dune objects. This approach allows for a more controlled evaluation of the segmentation methodology by reducing potential sources of systematic error. The three tiles were chosen by visual inspection and represent different complexities of dune structure and background (Figure 3).

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/tile_examples_selection.jpg?raw=true">
  <figcaption><b>Figure 3</b> Three sample tiles chosen for method development.</figcaption>
</figure>

## Automatic Mask Generator

Segment Anything provides different ways of generating masks: with or without user input. As explained, the Automatic Mask Generator requires only the image input itself but can be customized by choosing different parameters for the algorithm. While the general parameters chosen can be seen in Table 1, two different options were tested for the size of the input point grid (points per side): 32x32 points and 64x64 points.

| Parameter                                      | Value  |
|------------------------------------------------|--------|
| Points per batch                               | 128    |
| Predicted IoU threshold                        | 0.3    |
| Stability score threshold                      | 0.5    |
| Bounding Box Non-Maximum Suppression Threshold | 0.5    |
| Crop n layers                                  | 1      |
| Crop n points downscale factor                 | 2      |
| Minimum mask region area                       | 50     |

Table 1 Automatic Mask generator parameters

Before being able to look at the mask outputs, they must be filtered by size. Due to the high number of input points, one mask covers the entire image in all three cases.
Looking at the filtered mask outputs in Figure 4, they show that there is no significant difference between the number of points per side. Both 32x32 and 64x64 produce reasonable results. In contrast, when comparing the results of the individual tiles, clear differences in the accuracy of the masks are noticeable. The output for tile number 145 (Figure 4A and 4B) appears to be almost perfect. All the dunes were detected, and their shape was also recognized for almost all of them. Only in the case of a single dune was the area inside the crescent included in the mask. One weakness is the placement of masks even between the dunes, which is likely due to the high number of input points even next to the objects. This becomes even more apparent on tile 240 (Figure 4C and 4D) where more background noise seems to amplify this problem. Additionally, the masks on the actual dunes seem less robust. Tile 243 (Figure 4E and 4F) appears to pose even bigger problems for SAM, with only a few dunes being clearly detected.
In general, it can therefore be summarized that detection works very reliably if the dunes are clearly distinguishable from the background and are fairly isolated from each other.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/automatic_mask_generator_results.jpg?raw=true">
  <figcaption><b>Figure 4</b> Comparison of different mask outputs generated with the Automatic Mask Generator: (A) 32x32 input points for tile 145, (B) 64x64 input points for tile 145, (C) 32x32 input points for tile 240, (D) 64x64 input points for tile 240, (E) 32x32 input points for tile 243, (F) 64x64 input points for tile 243.</figcaption>
</figure>

### Manual Input Points

Another option for generating masks with SAM2 is to feed your own input points into the model. This was first done for all three tiles by manually clicking the points and using the respective coordinates as seed points (see Figure 5).

In comparison with the output of the Automatic Mask Generator, the results for tile 145 show only minor differences. While fewer masks are detected in the background, the overall quality of the masks remains similar to the first automatically generated output. The results for tile 243, on the other hand, appear to show a significant improvement. Although smaller dunes are still not reliably detected and some incorrect masks remain, the majority of the dunes have been detected, and the outcomes are cleaner and clearer. Noise, as in tile 240, still leads to masks with a high error rate. Even though some of the dunes have been detected, the geometry of the masks does not accurately represent the shapes of the dunes.

Considering the major improvements in tile 243 and the consistency of the output in tile 145, the conclusion can be drawn that when the input points are located on the dunes, SAM produces results of higher quality, at least when examining them visually.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/masks_clicked_points.jpg?raw=true">
  <figcaption><b>Figure 5</b> Comparison of the mask outputs using manually clicked points as input points for SAM; each row shows 1. the selected points, 2. second mask output of multimasks, and 3. third output of multimasks.</figcaption>
</figure>

## Seed Point Generation

Selecting input points on a few tiles, as in the examples shown before, is fast and easy. However, to create a truly automatic segmentation workflow and be able to apply it to bigger datasets, a different way of choosing the seed points must be implemented. Different methods were tested to set points. For example, working with SIFT-Features was taken into consideration, but no reasonable results could be reached. The final procedure to extract seed points consists of a combination of the Gaussian Filter and the Laplace filter.

In a first step, it was necessary to distinguish the dunes from the background and therefore minimize the influence of noise that resembles structures. Applying a Gaussian filter to the image produces an approximation of the background (Figure 6B), which was then subtracted from the original input image (Figure 6C). A grayscale image was then computed as the mean of the RGB channels, enhancing intensity-based edges (Figure 6D). On this grayscale image, a Laplacian filter was applied to identify the previously enhanced edges (Figure 6E). High Laplacian responses (both negative and positive) were thresholded to obtain a binary mask. Next, a binary closing operation was performed on the extracted values, connecting nearby pixels by bridging gaps and filling smaller holes (Figure 6F). In a last processing step, the now connected objects were labeled and filtered for features smaller than 50 pixels to remove fragments (Figure 6G). The remaining regions were assumed to be the candidate dune features, and for each one, the pixel with maximum Laplacian response was selected as the seed point for SAM (Figure 6H).

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/seed_point_workflow.jpg?raw=true">
  <figcaption><b>Figure 6</b> Workflow for automatic seed point generation</figcaption>
</figure>

Having generated seed points for all three example tiles, they were fed into Segment Anything. As shown in Figure 7, the results show a high resemblance to the masks with the manually clicked points.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/HenrikeM_figures/seed_point_masks.jpg?raw=true">
  <figcaption><b>Figure 7</b> Automatically generated seed points for each tile (A, C and E) and the resulting best mask output (B, D and F)</figcaption>
</figure>

# Discussion

The question posed in the beginning was whether the generally trained Segment Anything Model can be used to efficiently detect dunes in satellite imagery and therefore provide a groundwork for tracking their movement. Looking at the results of the segmentation process, the question can be answered positively. With a low amount of manual work, the mask outputs, especially for two out of the three example tiles, look promising upon visual inspection. Generating the seed points using the proposed workflow further reduces manual work, with only the preprocessing needing to be done separately. However, while reaching the proof of concept, there are still a lot of issues. For example, the process only produces high-quality results on tiles with a relatively simple structure and a clear distinction between the dunes and the background. Fragments in the background or merged dunes immediately lead to lower accuracy of the mask output. This leads to another challenge of the process: the lack of ground-truth datasets for this region makes it impossible to validate and quantify the actual accuracy of the output, and any assessment of the quality of the results is purely visual and subjective. This also leads to a problem when choosing the correct mask output of SAM. When working with individual input points, SAM2 delivers three different mask outputs, and their quality tends to vary quite a bit, which often simplifies the decision. However, sometimes it’s harder to evaluate just by visual inspection which output is the most accurate. Furthermore, each tile must be examined individually, requiring a manual step in the post-processing. This contradicts the goal of a fully automated process.

Future work should address these problems. Starting with the initial detection of the dunes, it would be possible to finetune the Segment Anything Model for this specific use case. While being trained on universal image data, it is possible to adjust SAM's model weights with individual data, but the lack of ground truth data remains a problem. In contrast, other remote sensing applications have already benefited from model finetuning due to the availability of training datasets. An example is automatic field delineation, where sufficient annotated data has enabled effective training (Scribano et al., 2025). This is not possible for our use case.

Furthermore, the process needs to be improved in the post-processing and could, for example, improve the reduction of mask fragments in the final output. This could perhaps be done by filtering the mask shapes, but the exact method would require further examination.

# References

Ben Kacem, A., Amyay, M., & Benbih, M. (2025). Evaluation of the mobility of barchan dunes and its effects in the palm grove of Jorf (Southeast of Morocco). *Ecological Engineering & Environmental Technology, 26*(11), 312–322. <https://doi.org/10.12912/27197050/213427>

Bristow, C. (2019). Bounding surfaces in a barchan dune: Annual cycles of deposition? Seasonality or erosion by superimposed bedforms? *Remote Sensing, 11*(8), 965. <https://doi.org/10.3390/rs11080965>

Brunotte, E., Gebhardt, H., Meusburger, P., Meurer, M., & Nipper, J. (Eds.). (2001). *Lexikon der Geographie: In vier Bänden*. Spektrum Akademischer Verlag.

Chan, V., Rheinwalt, A., and Bookhagen, B. (2026). OrthoSAM: multi-scale extension of the Segment Anything Model for river pebble delineation from large orthophotos, *Earth Surf. Dynam.*, 14, 391–416, <https://doi.org/10.5194/esurf-14-391-2026>.

Dakir, D., Rhinane, H., Saddiqi, O., El Arabi, E., & Baidder, L. (2016). Automatic extraction of dunes from Google Earth images: New approach to study the dunes migration in the Laâyoune city of Morocco. *The International Archives of the Photogrammetry, Remote Sensing and Spatial Information Sciences, XLII-2/W1*, 53–59. <https://doi.org/10.5194/isprs-archives-XLII-2-W1-53-2016>

Elbelrhiti, H. (2012). Initiation and early development of barchan dunes: A case study of the Moroccan Atlantic Sahara desert. *Geomorphology, 138*(1), 181–188. <https://doi.org/10.1016/j.geomorph.2011.08.033>

Elbelrhiti, H., Andreotti, B., & Claudin, P. (2008). Barchan dune corridors: Field characterization and investigation of control parameters. *Journal of Geophysical Research: Earth Surface, 113*(F2), Article 2007JF000767. <https://doi.org/10.1029/2007JF000767>

Elbelrhiti, H., Kamal, S., Elbelrhiti, K., Amimi, T., Ennouali, Z., Benmohammadi, A., Oubbih, J., & Chao, J. (2023). Sand dunes and sand encroachment in Moroccan Atlantic Sahara: Current situation, threat and perspective. In L. Qi, M. K. Gaur, & V. R. Squires (Eds.), *Sand dunes of the Northern Hemisphere: Distribution, formation, migration and management* (1st ed., pp. 20–33). CRC Press. <https://doi.org/10.1201/9781003290629-3>

Erdnüß, B., & Müller, T. (2020). Leistungsstarke und effiziente Bildinterpolation. In T. Längle & M. Heizmann (Eds.), *Forum Bildverarbeitung 2020* (pp. 253–265).

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A. C., Lo, W.-Y., Dollár, P., & Girshick, R. (2023). *Segment anything* (Version 1) [Preprint]. arXiv. <https://doi.org/10.48550/arXiv.2304.02643>

Mahmoud, A. M. A. (2022). *Monitoring sand dune movement using remote sensing* (Doctoral dissertation, University of Nottingham).

Qi, L., Gaur, M. K., & Squires, V. R. (2023). *Sand dunes of the Northern Hemisphere: Distribution, formation, migration and management: Volume 2: Characteristics, dynamics and provenance of sand dunes in the Northern Hemisphere* (1st ed.). CRC Press. <https://doi.org/10.1201/9781003290629>

Ravi, N., Gabeur, V., Hu, Y.-T., Hu, R., Ryali, C., Ma, T., Khedr, H., Rädle, R., Rolland, C., Gustafson, L., Mintun, E., Pan, J., Alwala, K. V., Carion, N., Wu, C.-Y., Girshick, R., Dollár, P., & Feichtenhofer, C. (2024). *SAM 2: Segment anything in images and videos* (Version 2) [Preprint]. arXiv. <https://doi.org/10.48550/arXiv.2408.00714>

Sauermann, G., Rognon, P., Poliakov, A., & Herrmann, H. J. (2000). The shape of the barchan dunes of Southern Morocco. *Geomorphology, 36*(1–2), 47–62. <https://doi.org/10.1016/S0169-555X(00)00047-7>

Scribano, C., Govi, E., Bertellini, P., Parisi, S., Franchini, G., & Bertogna, M. (2026). Segment anything for satellite imagery: A strong baseline and a regional dataset for automatic field delineation. In E. Rodolà, F. Galasso, & I. Masi (Eds.), *Image analysis and processing – ICIAP 2025* (Vol. 16168, pp. 115–126). Springer Nature Switzerland. <https://doi.org/10.1007/978-3-032-10192-1_10>
