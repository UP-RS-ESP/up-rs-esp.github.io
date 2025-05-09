---
title: 'A U-Net-SegmentAnything 2-pass approach with stereo-depth sensing for river-pebble panoptic segmentation'
author: "Man Tuen Chan"
author_profile: true
date: 2024-03-18
# permalink:
toc: true
toc_sticky: true
toc_label: "A U-Net-SAM 2-pass approach with stereo-depth sensing for river-pebble panoptic segmentation"
header:
  overlay_image: 
  overlay_filter: 0.3
  caption: "
  "
read_time: false
tags:
  - Stereo depth
  - segmentation
  - Segment-Anything
  - U-Net
---

# Introduction
Sediment charateristics and grain-size distribution carries important information on the drainage system, the ecosystem, and the weather condition (Soloy et al., 2020; Wang et al., 2019). Unfortunately, traditional methods to manually collect these information are costly, labor intensive, and time consuming. Over the years, various techniques have been developed seeking to reduce manual input through machine learning. This project is an attempt to utilize an U-Net-SAM 2-pass approach in conjunction with stereo-depth estimation to automize image based sampling. 

*This internship was supervised by Prof. Dr. Bodo Bookhagen.*

# Method
## Approach
This project approached the challenge from 2 angles. First, we introduce a depth layer estimated through stereo disparity in addition to RGB. The rationale is to provide additional morphological information to improve the segmentatino accuracy. The use of stereo vision also provides the additional benefit that accurate size measurements is readily available and segmented results can easily be applied to the point cloud through the disparity map (Mustafah et al., 2012). 

Second, we combine instance segmentation (Meta's Segment-Anything) and semantic segmentation (U-Net) through a 2-pass approach to achieve panoptic segmentation of grains for the extraction of individual grain samples. U-Net is a powerful tool capable of picking up features at different scale. Yet, while U-Net is capable of producing reliable results, it only performs a semantic segmentation. To separately sample individual grains, a second pass instance segmentation can be performed on top of the first pass U-Net result. The Meta Segment-Anything Model (SAM) was used in this project to perform the second pass segmentation. SAM is a pretrained model developed by Meta Platforms, Inc. (formerly Facebook). SAM was trained with large amount of data (1 billion masks and 11 million images) and evaluation of the model have shown that it provides reliable zero-shot performance (Kirillov et al., 2023). Should it performs reliably without the need of fine-tuning, significant time and computation power can be saved.

## Data collection
<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="high_imgL.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/high_imgL.jpg"></a>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="high_imgR.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/high_imgR.jpg"></a>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="high_depth.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/high_depth.jpg"></a>
    </figure>
</div>
<figcaption>Figure 1: Example of the pebble setup with high-angle images: left, right, and depth images.</figcaption>


The Stereolabs ZED 2i stereo camera together with their software ZED SDK 4.0 was used to collect the data used in this project. The pebble setup (Figures 1 and 2) was used as study sample to collect a total of 25 images. These 25 images were taken at 5 different angles, namely 1 (near-)nadir view and 4 top-down oblique views (backward, forward, left, and right). Each top-down oblique view were taken at 3 different angles, giving high, mid, and low-angle view images. In total that adds up to 12 oblique images. While all remaining 13 images were take in nadir view, each nadir image were taken in different lighting condition. That includes variation in lighting intensity, direction, and number light source. 



<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="low_imgL.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/low_imgL.jpg"></a>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="low_imgR.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/low_imgR.jpg"></a>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="low_depth.jpg"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/low_depth.jpg"></a>
    </figure>
</div>
<figcaption>Figure 2: Example of the pebble setup with low-angle images: left, right, and depth images.</figcaption>
<br/>

ZED 2i was used to retreive the RGB image, the depth estimation and the reprojected point cloud (Figure 3). Depth sensing was performed using the neural depth mode and stored in meter unit. This mode utilize model trained by Stereolabs to fill gaps and correct for noise. The estimated depth map was aligned to the image captured by the left sensor and comes in the HD2K resolution (2208x1242). For all 25 images, each image and measurement were average of 30 exposures to provide consistency and hand labels using Napari. As shown in figure 3, depth sensing can be quite challenging at steep slopes, overhangs, and edges where a drastic change in distance can be found. There were visble signs of artifacts that is possibly the result of the model's attempt to interpolate and smooth the transition. At a lower angle, shadowing can also be seen. Combined with the gap filling artifacts and the limitation of hardware resolution, the use of depth maps may actually hinder the segmentation instead of benefit it when it comes to lower angle shots. 

<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="high_point_cloud.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/high_point_cloud.png"></a>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="low_point_cloud.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/low_point_cloud.png"></a>
    </figure>
</div>
<br/>
<figcaption>Figure 3: Example of the generated pebble-point cloud: high-left angle and low-left angle</figcaption>



## Model
Meta has provides 3 pretrained checkpoints for SAM. Three model have different neural network sizes, base ViT-B, large ViT-L, and huge ViT-H. ViT-H was used for the automatic mask generation with default settings.

The U-Net on the other hand was compiled using Adam algorithm with learning rate &alpha; = 0.1 for optimization. Binary cross-entropy loss function using binary IoU was chosen for binary segmentation and the threshold was set at 0.5. The training was performed using batch size B = 64 and epoch e = 100. In total 4 models were trained. 2 models were trained using 13 nadir images. 13 images were divided into 4500 128x128 patches, of which ~20% were retained for validation. The remaining (unseen) 12 oblique images were used as test images to evalue the model. They were not used in the training process. 2 models were trained using this dataset split, one with the depth layer and one without. For convenience, they were named split1D (with depth) and split1C (RGB only) respectively. The remaining 2 models were also differentiated by the use of depth layer but they were trained with a different dataset split. For these 2 models 9 nadir images and 4 oblique images (2 high angle, 1 mid angle, and 1 low angle) were used in the training instead of 13 nadir images. Following the same convention, they were named split2D and split2C.

The reason of using 2 different splits has to do with a concern regarding the dataset. While variations were made in the view angle and lighting conditions, all images were essentially capturing the same study sample. To examine if the training results can actually be generalized, split 1 and 2 restrict the view angles available to the training process as an attempt to evaluate the actual performance. 

For all models, an 8 fold k-fold cross-validation was also performed. The training and validation dataset were shuffled before the split and all models uses the same split for each fold.

# Results
## SAM segmentation
<center>
<figure>
    <a href="ZED_sam.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/ZED_sam.png"></a>
</figure>
</center>
<figcaption> Figure 4: Segment-Anything segmentation of the pebble setup. </figcaption>

The results of SAM segmentation were demonstrated below. SAM returns a binary mask for each individual segments and figure 4 shows an example of aggregated mask plotted with the original image. SAM model was trained with RGB photos, hence depth images were not used. Figure 5 plots the accuracy of the segmentation by image. Image 0 to 12 were nadir images with variation in lighting condition, 13-24 were oblique image with variation in view angle. The accuracy was assessed by pebble. Each segment was compared to the manually labeled masked in which each pebble was labeled with a different ID. Segments where pebble pixels were found was considered a pebble segment. In these segment, the pebble that takes up the most area of the segment was considered the main pebble. If the area of the main pebble inside the segment did not reach 70% of the pebbles total area, the segment will be considered as over-segmented. If the main pebble was not over-segmented and takes up at least 70% of the segment area, it is considered correctly segmented (or SAM segmented pebbles in figure 5). If non of these is true, it will be considered as under-segmented.


<center>
<figure >
    <a href="sam_pixel_count.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/sam_pixel_count.png"></a>
</figure>
</center>
<figcaption>Figure 5: Percentage of correctly segmented, over/under segmented, and not segmented grains in SAM automatic mask generation by image.</figcaption>

## U-Net training history and accuracy
<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1C_kfold0.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/history/pebble_unet_Split1C_kfold0.png"></a>
        <figcaption>(a)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1C_kfold0.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/history/pebble_unet_Split1C_kfold0.png"></a>
        <figcaption>(b)</figcaption>
    </figure>
</div>
<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1C_kfold0.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/history/pebble_unet_Split1C_kfold0.png"></a>
        <figcaption>(c)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1C_kfold0.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/history/pebble_unet_Split1C_kfold0.png"></a>
        <figcaption>(d)</figcaption>
    </figure>
</div>
<figcaption>Figure 6: U-Net Model training history of each split at kfold 0: (a) Split1C; (b) Split1D; (c) Split2C; (d) Split2D </figcaption>
<br/>
Figure 6 shows the training history of all splits at the first fold. Accuracy accessed through precesion, accuracy, F1 score, and binary IoU. The metrics were only calculated for test images that the models have seen in the training process. Figure 7 shows the accuracy metrics by image at different threshold. Solid line shows the mean value over 8 folds k-fold and the shaded area highlights the 25th to 75th percentiles. For the view angle correponding to each test images please see Table 1. Figure 8 shows the the accuracy variation over the folds. Solid line represent the mean value over all test images with threshold=0.7 while the shaded area indicates the threhold = 0.5-0.9.

Table 1: Test images view angles

| Split | Nadir | Oblique high | Oblique mid | Oblique low |
|:-----------------:|:-----------------:|:-----------------:|:-----------------:|:-----------------:|
| split1   | -- | Image 0-3 | Image 4-7 | Image 7-11 |
| split2   | Image 8-11 | Image 0-1| Image 2-4 | Image 5-7 |


<div style="display: flex; flex-direction: column; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1C_image_accuracy.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split1C_image_accuracy.png"></a>
        <figcaption>(a)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1D_image_accuracy.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split1D_image_accuracy.png"></a>
        <figcaption>(b)</figcaption>
    </figure>
</div>
<div style="display: flex; flex-direction: column; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split2C_image_accuracy.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split2C_image_accuracy.png"></a>
        <figcaption>(c)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split2D_image_accuracy.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split2D_image_accuracy.png"></a>
        <figcaption>(d)</figcaption>
    </figure>
</div>
<figcaption>Figure 7: U-Net Model accuracy of each split assessed by image at 3 threshold. Shadowed area indicates the 25th to 75th percentile along kfolds: (a) Split1C; (b) Split1D; (c) Split2C; (d) Split2D</figcaption>

<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1C_kfold_consistency.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split1C_kfold_consistency.png"></a>
        <figcaption>(a)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split1D_kfold_consistency.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split1D_kfold_consistency.png"></a>
        <figcaption>(b)</figcaption>
    </figure>
</div>
<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split2C_kfold_consistency.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split2C_kfold_consistency.png"></a>
        <figcaption>(c)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_unet_Split2D_kfold_consistency.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/Accuracy_plot/pebble_unet_Split2D_kfold_consistency.png"></a>
        <figcaption>(d)</figcaption>
    </figure>
</div>
<figcaption>Figure 8: U-Net model consistency of accuracy metrics over kfolds. Shadowed area indicates the 25th to 75th percentile along test images: (a) Split1C; (b) Split1D; (c) Split2C; (d) Split2D </figcaption>
<br/>
Through the union of SAM mask and U-Net mask, point cloud of individual pebbles can be easily created. Figure 9 presents an example created through open3d `geometry.create_point_cloud_from_depth_image` and visualized in CloudCompare. Figure 9a visualize a RGB mesh generated from the point cloud and 9b visualize the point cloud colored by the distance between the grain and the camera with an estimate of size through calculating the distance between points. This was manually done through the CloudCompare 'Point picking' function and the estimate width is 13.3cm and the estimated hight is 10.1cm. Unfortunately, it is likely that this estimation is incorrect as the example presented here was not properly scaled. For the pint cloud to be correctly scaled, 4 calibration parameters are necessary. These are the x,y focal length, and principal points of the ZED 2i camera. These parameters are accessible through the camera API but unfortunately only the focal length were exported and saved before returning the camera to the University. Additionally, manually selecting the points for may raise the concern of objectivity and consistency. A better approach could be to lock for the major and minor axes as an indicator of the grain size. Nevertheless, segmentation results can be used create point clouds of samples individually and provides the oppotunity to analyse other physical charateristics such as surface smoothness and geometry.

<div style="display: flex; flex-direction: row; justify-content: center;">
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_point_cloud_rgb.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/pebble_point_cloud_rgb.png"></a>
        <figcaption>(a)</figcaption>
    </figure>
    <figure style="flex: 1; margin-right: 0px;">
        <a href="pebble_point_cloud.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/ManTuenChan_UNET/pebble_point_cloud.png"></a>
        <figcaption>(b)</figcaption>
    </figure>
</div>
<figcaption>Figure 9: Point cloud of a pebble created from segmented depth map and RGB image with width and hight estimation: (a) RGB mesh and (b) Distance to camera in meter</figcaption>



# Conclusion and discussion
This project is an attempt to utilize an U-Net-SAM 2-pass approach in conjunction with stereo-depth estimation to automize image based sampling. To assess the feasibility of this approach, the ZED 2i camera was used to capture a series of RGB and depth images from different angles and under different lighting condition. These images were manually labeled and segmented with the Meta SAM model. 

The results of SAM segmentation were visually impressive yet the accuracy reveals that the quality of the results decreases when view angles steepen. The main issue seems to be the partial overlap that does not completely hide the pebbles. These mostly covered pebbles leave out a small edges that are still noticeable by human vision yet challenging for SAM to detect. One speculation as to why SAM is struggling with these partially covered pebbles is that it has to do with scale. Based on experience, SAM seems to favor the assumption that objects are at similar scale. It could be related to the use of point grid as input prompt, this assumption often lead to over-segmentation grains that are notably larger then the surroundings. As the view angle steepens more pebbles were partially covered, resulting in a higher percentage of non segmented pebbles. Another factor that stands out is the lighting condition. With strong artificial lighting there is a higher tendency of missing objects while the absence of artificial lighting does not really impact the performance. Nevertheless, with nadir images SAM is capable of producing reliable segmentation without the need of fine-tuning.

U-Net on the other hand, yields a mixed result. While the general stable and good accuracy suggest that the models were generally performing well, looking at split 1 models, the use of depth information apparently lead to larger fluctuation in performance across folds and a lower recall and F1 score. This likely suggested that depth information increases the likihood of producing flase negatives when the model was only trained with nadir images. Oppose to the expectation the depth information did not help the model to better generalize. The use of depth information in split 1 did not change how it struggles as the view angle differences increase or when the lighting was too strong. When compared to split 2, we can see that the inclusion of images take from different angles can visibly improve the performance. Here, even though hardly significant, the use of depth information slightly improved the performance and the stability across folds. Particularly at higher threshold, it also improved the models capability of handling challenging lower angle images and overexposed images. Take binary IoU as an indicator, split1D perform the worse with mean binary IoU at 0.72 across folds. Split1C shows a slight improvement at 0.78 while split2 models virtually performs equally weel at around 0.89. 

The results suggest that the approach is a feasible method given that some variation in view angle is also included in the training dataset. The use of depth information did not benefit the segmentatino as much as expected, but it still retains its value by providing the option to perform size measurement and create point clouds. This project has a few limition. First, no variation in camera paramters were tested. The same is true for the U-Net hyperparameters. The study sample is also the most concerning limitation. All images were taken from the same study sample, which raises the question if it could also achieve comparable results in real world application. It is also unclear what causes the worse performance of split1D. Tackling these problems would be possible improvements to the proposed method.

# Reference
Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A. C., Lo, W.-Y., Dollár, P., & Girshick, R. (2023). Segment Anything. 2023 IEEE/CVF International Conference on Computer Vision (ICCV), 3992–4003. https://doi.org/10.1109/ICCV51070.2023.00371

Mustafah, Y. M., Noor, R., Hasbi, H., & Azma, A. W. (2012). Stereo vision images processing for real-time object distance and size measurements. 2012 International Conference on Computer and Communication Engineering (ICCCE), 659–663. https://doi.org/10.1109/ICCCE.2012.6271270

Soloy, A., Turki, I., Fournier, M., Costa, S., Peuziat, B., & Lecoq, N. (2020). A Deep Learning-Based Method for Quantifying and Mapping the Grain Size on Pebble Beaches. Remote Sensing, 12(21), Article 21. https://doi.org/10.3390/rs12213659

Wang, C., Lin, X., & Chen, C. (2019). Gravel Image Auto-Segmentation Based on an Improved Normalized Cuts Algorithm. Journal of Applied Mathematics and Physics, 7(3), Article 3. https://doi.org/10.4236/jamp.2019.73044
