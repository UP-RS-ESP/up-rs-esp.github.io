---
title: 'Camera Calibration and Mitigating Doming Effects'
author: "Florian Josephowitz"
author_profile: true
date: 2025-12-17
toc: true
toc_sticky: true
toc_label: "Camera Calibration with Calib.IO and Metashape"
header:
  #overlay_image: https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/untitled_3_crop.jpg
  overlay_filter: 0.3
  caption: "3D Model generated with SfM"
read_time: false
tags:
  - Structure from Motion
  - Camera Calibration
  - Metashape
  - Calib.IO
---
Photogrammetric models are widely used in geoscience, but subtle processing errors can significantly distort their geometry. This study investigates the causes of doming errors and outlines practical strategies to improve model accuracy.

# Introduction
High-quality photogrammetric models are essential tools across many scientific disciplines, particularly in the geosciences, where accurate geometry is critical for subsequent analyses. Applications such as roughness estimation, volume calculation, curvature analysis, 3D curve fitting, and data fusion with LiDAR require geometrically reliable models. However, photogrammetric workflows involve multiple complex processing steps and are strongly influenced by user experience, camera hardware, and parameter estimation during bundle adjustment. A common systematic artifact is the so-called doming error, which manifests as a global warping of reconstructed surfaces, especially in ground-based or UAV surveys of relatively flat areas with pronounced vertical relief. This report examines the characteristics and underlying causes of doming errors and proposes strategies to mitigate their impact, thereby improving the geometric fidelity of photogrammetric models.

The basis for this work are images from three different cameras. These images are used to analyze the resulting doming error of a ground reconstruction from each camera. A ground scan with different objects such as stones, spheres, and coded targets is used as a testing ground. The scene is reconstructed from every camera image. The photos from all cameras are structured in 4 recording groups with different angles and distances. The four groups of camera orientations used are: High above ground with nadir view, high above ground with oblique view, lower above ground with oblique view, and very low with oblique view and handheld recording.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/S1H%20OVerview_area_white.jpg">
  <figcaption><b>Figure 1</b> 3D reconstruction of the test area on Campus Golm.</figcaption>
</figure>

The recorded images are processed as described below and further analyzed to determine the doming error and other influence of the camera calibration on the final products of photogrammetry. Focus lies on the camera calibration as main driver for the doming error. It is believed that badly estimated radial distortion parameters heavily influence the doming error strength. Some insights could be found but no final conclusion is made jet. The report also mentions ways do further research in this topic as follow-up to this internship.

*This internship was supervised by Prof. Dr. Bodo Bookhagen.*


# Camera Calibration Theory
Camera and lens calibration is necessary for image measurements and especially for photogrammetry. Camera calibration determines the deviation of measured image points from a ideal central projectiv camera model$$^1$$. An ideal central projection would exist in the theoretical case of a pinhole camera and describes a model, in which the beam geometry of an camera is centered in a optical center and the light paths are ideal straight lines between object and camera sensor$$^1$$. This is not the case at all in lens systems, where light is collected and passed trough different glass elements. The goal of camera calibration is to model the geometric deviation of the light beams as accurate as possible and describe it as the inner orientation of the camera system$$^1$$. Besides the inner orientation there are non geometrical errors too. They show up in images as chromatic aberrations or diffraction blur, but these are not part of inner orientation and not considered here. After Luhmann and Maas (2017), the inner orientation of a camera consists of the position of the principle point and the description of the lens errors of the image coordinates in the image plane.

*Principal point position:*

The principal point is a theoretical center of the perspective projection and it is used as rotation point for the projection between the image points ($$x,y,z$$) and the object coordinates ($$X,Y,Z$$).

The principle point is usually not exactly the same as the geometric center of image. It is slightly offsetted in x and y direction and noted as $$x_0$$ and $$y_0$$. In addition, the image point has a z coordinate inside the image coordinate frame. It is located above the image plane at $$-c$$ with c being the camera constant, what is roughly the focal length of the lens.

The collinearity model is the mathematical description that the projection between object and image coordinates.

$$
x = x_0 -c \cdot \frac{r_{11}(X - X_0) + r_{21}(Y - Y_0) + r_{31}(Z - Z_0)}{r_{13}(X - X_0) + r_{23}(Y - Y_0) + r_{33}(Z - Z_0)}+ \Delta x
$$

$$
y = y_0 - c \cdot \frac{r_{12}(X - X_0) + r_{22}(Y - Y_0) + r_{32}(Z - Z_0)}{r_{13}(X - X_0) + r_{23}(Y - Y_0) + r_{33}(Z - Z_0)}+ \Delta y
$$

After $$^1$$ and $^2$$.

The parameters $$x_0, y_0, -c$$ inside the equation are the position of the principle point. The $$r_i$$ coefficients and $$X_0,X_0,Z_0$$ are elements of the exterior orientation of the individual images.

*Image coordinate perturbations:*

The image coordinate perturbations extend the collinearity equation. The geometric image error models sum up to one correction $$\Delta x$$ and $$\Delta y$$ for the $$x$$ and $$y$$ axis of the image coordinate system$$^2$$. There are several corrections discussed in the literature for the image correction. Many basic models follow the work of Duane C. Brown$$^3$$. The corrections used here to compensate the radial distortion and the decentering distortion are also represented in software solutions an use the parameters $$K_1,K_2,..,K_i$$ and $$P_1,P_2$$. There are more complex effects in other literature, but these are not described here.

$$ \Delta x = \Delta x_r + \Delta x_d + \Delta x_u + \Delta x_f $$ $$ \Delta y = \Delta y_r + \Delta y_d + \Delta y_u + \Delta y_f $$

The total distortion error to the image pixels are the sum from each individual error source.

*Radial Distortion:*

The radial lens distortion is represented as an odd ordered polynomial series$$^2$$.

$$  
\Delta r = K_1 r^3 + K_2 r^5 + K_3 r^7  
$$

with $$  
r = \sqrt{\bar{x}^2+\bar{y}^2} = \sqrt{(x-x_0)^2+(y-y_0)^2}  
$$

which results in

$$  
\Delta x_r = \bar{x} \Delta r / r  
= \frac{(x-x_0) K_1 r^3 + K_2 r^5 + K_3 r^7}{\sqrt{(x-x_0)^2+(y-y_0)^2}}  
$$

$$  
\Delta y_r = \bar{y} \Delta r / r  
= \frac{(y-y_0) K_1 r^3 + K_2 r^5 + K_3 r^7}{\sqrt{(x-x_0)^2+(y-y_0)^2}}  
$$

The coupling of the Parameters $K_i$ with the exterior orientation is usually low$$^2$$.

*Decentering Distortion:*

Decentering distortion is caused by misalignment of the optical axis from the image center$$^2$$.

$$  
\Delta x_d = P_1 (r^2 + 2\bar{x}^2) + 2P_2 \bar{x}\bar{y}  
$$

$$  
\Delta y_d = 2P_1 \bar{x}\bar{y} + P_2 (r^2 + 2\bar{y}^2)  
$$

*In plane distortions:*

These are described by $$\Delta x_f = b_1 \bar{x} + b_2 \bar{y}$$ but neglected in this case.

Modified after Fraser (1997) the combined influence of all lens errors is:

$$\Delta x = -x_0 - \frac{\bar{x}}{c} \Delta c + \bar{x}r^2 K_1 + \bar{x}r^4 K_2 + \bar{x}r^6 K_3 + (2\bar{x}^2 + r^2) P_1 + 2P_2 \bar{y} \bar{x} + b_1 \bar{x} + b_2 \bar{x} $$

$$ \Delta y = -y_0 -\frac{\bar{y}}{c}\Delta c + \bar{y}r^2 K_1 + \bar{y}r^4 K_2 + \bar{y}r^6 K_3 + 2P_1 \bar{y} \bar{x} + (2\bar{y}^2 + r^2) P_2 $$

with $$\bar{x} = (x-x_0)$$ and $$\bar{y} = (y-y_0)$$ wich are the distances from the principle point in each axis.

For this report, the following parameters are used in all calibrations.

| \#  | Parameter | Description                         |
|-----|-----------|-------------------------------------|
| 1   | F         | Focal length                        |
| 2   | Cₓ        | Principal point                     |
| 3   | Cᵧ        | Principle point                     |
| 4   | K₁        | Radial Distortion Coefficient 1     |
| 5   | K₂        | Radial Distortion Coefficient 2     |
| 6   | K₃        | Radial Distortion Coefficient 3     |
| 7   | P₁        | Descentering Distortion Coefficient |
| 8   | P₂        | Descentering Distortion Coefficient |

# Setup
Basis for the testing are three different cameras: the Sony Alpha 7 R MK 5 (A7R5), the Sony Alpha 6000 (A6000) and the Panasonic S1H. Two of them are Full-Frame (\~36 x 24 mm) sensor cameras, one cameras has slightly smaller APS-C sensor (\~17 x 21 mm). APS-C cameras are usually lighter and more affordable and therefore widely used. As optics, high quality fixed focal-length lenses are used. Fixed focal-length lenses usually maintain more optical stability during shooting than zoom lenses because they contain less movable lens elements$$^4$$. These cameras are oriented according to different distances and angles during the image acquisition.

## Cameras
The cameras main characteristics are summarized in the following table.

| Camera | Resolution (pix) | Sensor Format | Pixel Size (µm) | Lens | Focal Length (mm) |
|------------|------------|------------|------------|------------|------------|
| **A7R5** | 9504 × 6336 | Full-Frame | 3.79 × 3.79 | Sony GM | 50 |
| **A6000** | 6000 × 4000 | APS-C | 0.4 × 0.4 | Sony GM | 50 |
| **S1H** | 6000 × 4000 | Full-Frame | 6 × 6 | Contax/Zeiss | 50 |

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/IMG_3362.JPEG">
  <figcaption><b>Figure 2</b> Monopod setup and image Aquisition for Lens/Camera Calibration.</figcaption>
</figure>


## Calibration Setup
Camera Calibration is the central point of the tests done here. Precalibration is carried out for all used cameras before the image acquisition. So the image acquisition started immediately after the calibration of the camera. For the calibration a coded checkerboard (ChAruCo) is used (18x25 \| Checker Size: 15 mm \| Marker Size: 12 mm \| Dictionary: AruCo DICT_5x5). The board is printed on aluminum and has a size of 400 x 300 mm. The advantage of the ChAruCo board in comparison to uncoded checkerboards is, that is allows greater distribution of tie points in the image corners and edges. This is because they can also be used when partly covered since every second rectangle on the board is coded with an identifier. The overall goal of the calibration is to ensure coverage of the entire image plane and use different distances and orientations to the checkerboard. For that, the checkerboard is first photographed from a distance from all 4 edges of board ensuring coverage of all edges. Then close up images and nadir images are taken of the board. The tie board was placed on the ground and the viewer's position changed. For each Camera around 127-224 images were acquired with the ChArUco board: A7R5 224 images, A6000 127 images, S1H 181 images.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/Charuco%20example.png">
  <figcaption><b>Figure 3</b> Example of a Charuco target board.</figcaption>
</figure>

## Acquisition scenarios
Photogrammetric reconstruction generally profit from different view distances and different view angles to ensure high angle view ray intersections. Furthermore the distance to the object surface defines the resolution that is possibly reachable. To test for the best reconstruction instructions, different angles and distances are included in the data acquisition.

Theoretical resolution on the object is simply linked to the pixel size and focal length of the camera-system.

$$ \text{GSD} = \frac{\Delta p_{ix}}{c} \cdot h $$

From this equation we can see which ground sampling distance (GSD) is expected for the used camera-system. GSD is the pixel size on the ground, this does not resemble the real resolving limit of the images but is well suited for planning.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/acquisition_distance_vs_focal_length.svg">
  <figcaption><b>Figure 4</b> Simple acquisition distance calculation for different camera models with an expected GSD of 1 mm.</figcaption>
</figure>

The orientation scenarios are *High Nadir, High Oblique, Low Oblique, Low Handheld.* The following figure shows an overview over the different camera orientations. The images from all positions are taken with the help of a monopod. The last set of photos was done handheld with not tripod. The highest positions contains views looking down nadir and oblique views with around (XXX), the low positions are done with oblique views (xxx) and very low angle handheld images.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/Setup_overview_v2.svg">
  <figcaption><b>Figure 5</b> Setup with different acquisition distances and angles.</figcaption>
</figure>

## Input Data
This is the input data for the photogrammetric reconstruction and the later doming analysis.

| Camera    | Scene Set    | Images | Lens  |
|-----------|--------------|--------|-------|
| **A7RV**  | High Nadir   | 42     | 50 mm |
|           | High Oblique | 40     | 50 mm |
|           | Low Oblique  | 95     | 50 mm |
|           | Low Handheld | 68     | 50 mm |
| **A6000** | High Nadir   | 82     | 50 mm |
|           | High Oblique | 104    | 50 mm |
|           | Low Oblique  | 117    | 50 mm |
|           | Low Handheld | 30     | 50 mm |
| **S1H**   | High Nadir   | 60     | 50 mm |
|           | High Oblique | 50     | 50 mm |
|           | Low Oblique  | 131    | 50 mm |
|           | Low Handheld | 83     | 50 mm |

## Data Processing:
For the processing a simple workflow is used the software Agisoft Metashape (v2.1). From camera alignment and filtering of the tie points a dense point cloud is derived. Before that, a the camera calibration is done in the software CalibIO and the right parameters for the self-calibration in Metashape has to be chosen.

### Precalibration
The calibration with ChArUco board is done in the software CalibIO. For this, the CalibIO workflow is followed with the detection of tie points and camera optimization. As Initialization method *vanishing points* is used. The boards tie points are detected with the *estimate homography* option. To improve the quality of the calibration some photos with high rms reprojection erros are manually excluded from the optimization. In the second refinement of the calibration the robust norm with a threshold of 0.3 pix is enabled. The result is exported as .json file, converted to an .xml and loaded into Metashape.

### Internal self-calibration
The internal self calibration is automatically done in Metashape during the image alignment. The parameters are set inside the Alignment menu and then the calibration is estimated during the tie point calculation. One option in this testing was to load the highly accurate precalibration and let Metashape refine it slightly. This is also set up before the alignment. After the initial alignment some of the tie points with high errors are deleted (Tie point filtering or gradual selection). After that the camera positions are optimized again, what leads to a better model.

The Process is visualized in the following graph.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/02%20Mermaid%20Chart%20-%20Create%20complex,%20visual%20diagrams%20with%20text.-2025-12-16-204402.svg">
  <figcaption><b>Figure 6</b> Processing steps Metashape.</figcaption>
</figure>

### Alignement
The alignment of the images is done for all cameras on the quality setting "highest". This is the most accurate setting for the alignment and uses a four times upscaled images$$^4$$ for the tie point coordinate extraction. The alignment estimates the camera positions (exterior orientation), the camera calibration includes the lens distortions (interior orientation) and the point cloud with the tie points in the object space.

For testing the influence of the calibration on the doming effect later in the processing, the aligned is done for three settings for the calibration. Internal self-calibration in Metshape, loaded precalibration with variable parameters in Metashape and loaded precalibration with fixed parameter in Metashape.

### Filtering
After alignment the resulting tie points are filtered, and points with high reprojection errors are deleted to improve the camera orientations for the next steps. High reprojection errors usually indicates poor localization of the tie points in the alignment$$^4$$. Often around 50% of the points can be deleted to reach higher accuracy inside the adjusted orientations of the cameras. It is strictly necessary to optimize the camera positions after the filtration. The filter threshold is chosen as low as possible for the individual models (see following table).

### Dense Cloud Generation
The last step as preparation for the doming analysis is the dense point cloud generation. This is quickly done with medium quality settings and a mild filtering. Mild filtering is suitable because there is not any noise in the images, they are produced with low (\~base) ISO setting under perfect daylight conditions.

All Metashape processing steps are summarized in the following table.

|   |   | **internal \| free** | **precalibrated \| free** | **prelibrated \| fixed** |
|---------------|---------------|---------------|---------------|---------------|
| *A7R5* |  |  |  |  |
| **Alignment** | Quality | highest | highest | highest |
|  | Key Point Limit | 40e3 | 40e3 | 40e3 |
|  | Tie Point Limit | 10e3 | 10e3 | 10e3 |
| **Filter** | Repr. Error \< | 0.3 pix | 0.3 pix | 1.0 pix |
| **Dense Cloud** | Quality | medium | medium | medium |
|  | Filtering | mild | mild | mild |
|  |  |  |  |  |
| *A6000* |  |  |  |  |
| **Alignment** | Quality | highest | highest | highest |
|  | Key Point Limit | 40e3 | 40e3 | 40e3 |
|  | Tie Point Limit | 10e3 | 10e3 | 10e3 |
| **Filter** | Repr. Error \< | 0.1 pix | 0.1 pix | 0.1 pix |
| **Dense Cloud** | Quality | medium | medium | medium |
|  | Filtering | mild | mild | mild |
|  |  |  |  |  |
| *S1H* |  |  |  |  |
| **Alignment** | Quality | highest | highest | highest |
|  | Key Point Limit | 40e3 | 40e3 | 40e3 |
|  | Tie Point Limit | 10e3 | 10e3 | 10e3 |
| **Filter** | Repr. Error \< | 0.2 pix | 0.2 pix | 0.3 pix |
| **Dense Cloud** | Quality | medium | medium | medium |
|  | Filtering | mild | mild | mild |


After reconstruction the point clouds, a spherical fit and local variance measures are made to determine the geometric quality of the models

### Determine the doming error
The characteristics of the doming error is that the reconstructed area is warped in a spherical matter concave or convex: especially the edges of the observed area are suffering from offset relative to the central parts. As method to quantify the doming error a sphere is fitted to all dense points clouds. The radius is the parameter of interest to measure the magnitude of the doming.

### Local geometric noise
To differentiate between the global warping and local noise level inside the model the noise level is inspected in different regions inside each point cloud. This local quality of the model is measured in specified areas in the model center and models edges. For these areas, flat floor parts of the model are extracted. The smoothness of these regions is measured as variance and compared relative between the different reconstructions. The floor parts are flat floor tiles, but they are not perfectly aligned to the general ground level. The scan is so sensitive, that even smallest changes in orientation become visible. So just the variance, but the distance to a fitted plane on these tiles is calculated. That ensures that just the noise as variation from this surface is measured and no trends are included to the standard deviation measure. Pre-test showed such a noise for a simple extraction of the z-coordinates.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/Targets%20overiew.png">
  <figcaption><b>Figure 7</b> Overview local noise measurements. Red squares indicate areas that have been used for local noise measurements.</figcaption>
</figure>

# Results & Discussion
## Results Alignment
The alignment process in Metashpe delivers the internal camera calibration, tie points and camera orientations. The results from the alignment and model building is shown here:

|   |   | **internal \| free** | **precalibrated \| free** | **prelibrated \| fixed** |
|---------------|---------------|---------------|---------------|---------------|
| A7R5 |  |  |  |  |
| *Alignment* | RPE | 0.465 pix | 1.07 pix | 2.78 pix |
|  | RPE after filter | 0.436 pix | 0.809 pix | 1.76 pix |
|  | Tie Points initial | 68,654 | 147,622 | 145,843 |
|  | Tie Points after filter | 65,973 | 58,231 | 83,120 |
| *Dense Point Cloud* | Dense Points | 58 mio | 60 mio | 65 mio |
|  |  |  |  |  |
| A6000 |  |  |  |  |
| *Alignment* | RPE | 0.343 pix | 0.347 pix | 0.467 pix |
|  | RPE after filter | 0.168 pix | 0.18 pix | 0.175 pix |
|  | Tie Points initial | 495,787 | 496,829 | 464,619 |
|  | Tie Points after filter | 222,080 | 208,576 | 212,181 |
| *Dense Point Cloud* | Dense Points | 40 mio | 40 mio | 47 mio |
|  |  |  |  |  |
| S1H |  |  |  |  |
| *Alignment* | RPE | 0.395 pix | 0.395 pix | 0.461 pix |
|  | RPE after filter | 0.251 pix | 0.251 pix | 0.348 pix |
|  | Tie Points initial | 272,122 | 271,206 | 270,348 |
|  | Tie Points after filter | 137,655 | 137,217 | 176,649 |
| *Dense Point Cloud* | Dense Points | 29 mio | 29 mio | 29 mio |
|  |  |  |  |  |

Overall, the results of the internal camera calibration inside Metashape provides the best results for all cameras. This self-calibration with the recorded model images delivers the overall lowest reprojection errors. Fitlering is enhancing every alignment in every case. In terms of reprojection error, the A6000 surpasses the other two cameras. The S1H follows, the A7R5 shows the highest reprojection error, but one should keep in mind that this camera has nearly half the physical pixel size (in µm) then the S1H.

## Results Calibration
Results of the calibration includes the precalibration in from CalibIO and the self calibration inside Metashape and the comparison of both.

### Precalibration
The pre-calibration is done right before the image acquisition for the photogrammetric model, with all camera/lens combinations. For each Camera around 127-224 images are acquired with the ChArUco Target: A7R5 224 images, A6000 127 images, S1H 181 images.

Overall good results for the precalibration are reached. All 3 cameras delivers results with a mean reprojection error (RPE) better than 0.35 pix.

| Camera | mean RPE   | rms RPE    |
|--------|------------|------------|
| A7R5   | 0.3512 pix | 0.4595 pix |
| A6000  | 0.2512 pix | 0.3591 pix |
| S1H    | 0.1692 pix | 0.238 pix  |

### Internal calibration & precalibration values
After running models with all calibration methods, a comparison of the parameters is possible.

| \# | Parameter \[pix\] | A7R5 (internal) | A7R5 (external free) | A7R5 (external fixed) |
|---------------|---------------|---------------|---------------|---------------|
| 1 | F | 13099.7 | 13126.4 | 13262.9 |
| 2 | Cₓ | 23.631 | 28.5833 | 12.0082 |
| 3 | Cᵧ | -1.45571 | -8.23804 | 10.1438 |
| 4 | K₁ | -0.0595934 | -0.0565529 | -0.0252 |
| 5 | K₂ | 0.198088 | 0.166593 | 0.1368 |
| 6 | K₃ | 3.07501 | 3.25817 | 3.5487 |
| 7 | P₁ | 0.000684365 | 0.000732308 | 0.00016 |
| 8 | P₂ | 0.000323586 | 0.000341725 | 0.0008 |

| \# | Parameter \[pix\] | A6000 (internal) | A6000 (external free) | A6000 (external fixed) |
|---------------|---------------|---------------|---------------|---------------|
| 1 | F | 12603.8 | 12637.4 | 12656.0164 |
| 2 | Cₓ | 29.1638 | 33.158 | 33.5940 |
| 3 | Cᵧ | -24.0809 | -32.4546 | 3.7326 |
| 4 | K₁ | -0.0174475 | -0.0170159 | -0.0054 |
| 5 | K₂ | -0.651237 | -0.679063 | -0.7598 |
| 6 | K₃ | 8.83859 | 9.13826 | 9.7702 |
| 7 | P₁ | 0.00124773 | 0.00107892 | 0.0004 |
| 8 | P₂ | 0.000500207 | 0.000768108 | 0.0013 |

| \# | Parameter \[pix\] | S1H (internal) | S1H (external free) | S1H (external fixed) |
|---------------|---------------|---------------|---------------|---------------|
| 1 | F | 8935.8 | 8935.87 | 8940.1249 |
| 2 | Cₓ | -33.9712 | -34.0287 | -51.8360 |
| 3 | Cᵧ | 11.3013 | 11.2676 | 24.7661 |
| 4 | K₁ | -0.15781 | -0.157853 | -0.1616 |
| 5 | K₂ | 0.0050763 | 0.00549349 | 0.0583 |
| 6 | K₃ | 0.450305 | 0.448741 | 0.2522 |
| 7 | P₁ | -0.000200959 | -0.000202058 | -0.0005 |
| 8 | P₂ | -0.000310129 | -0.0003088 | -0.0002 |

A deviation between the different approaches for calibration is visible. Overall the A6000 and A7R5 seem to have more variation between the internal calibration and the precalibration parameters than the S1H. For both the A6000 and the A7R5 it is observable that the precalibration estimates a higher focal length (or camera constant). Also the estimated K₁ parameter for these two cameras are just half the magnitude in the precalibration then in the internal calibration. That is especially important because the K₁ is the lowest order component of the radial distortion, and most likely has the strongest coupling with the doming error. As stated earlier, the S1H camera with a different lens is the most stable one between the pre- and internal calibration. Camera constant varies in a 5 pixels between all calibrations for the S1H. Also the interesting K Parameters K₁ and K₂ are not changing much as for the other cameras.

To support the pure tabular view on the data of the calibration files, the distortion can also be visualized from the calibration files.


<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/CameraCalibrationFigures/Calibration_A7R5_v2_vs_A7R5_self_and_precalibration_3panel_func1.jpg">
  <figcaption><b>Figure 8</b> Comparison of camera calibration for A7R5. Top panel shows self calibration with Metashape and bottom row shows precalibrated images with ChAruCo board. CalibIO calibration on the left, Metashape calibration middle, difference at the right.</figcaption>
</figure>


*A7R5 (above):* The figures support what is visible from the models too. The A7R5 has a radial distortion, that is especially strong in the outermost corners. Interesting is the difference between precalibration and the internal calibration too: The both calibrations vary especially in the radial distortion in the outer edges. Both are strong there, but the precalibration by CalibIO is underestimating the distortion in the corners compared to Metashape. This will later be visible in the doming as well.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/CameraCalibrationFigures/Calibration_A7R5_v2_vs_A7R5_self_and_precalibration_3panel_func1.jpg">
  <figcaption><b>Figure 9</b> Comparison of camera calibration for A6000. Top panel shows self calibration with Metashape and bottom row shows precalibrated images with ChAruCo board. CalibIO calibration on the left, Metashape calibration middle, difference at the right.</figcaption>
</figure>


*A6000 (above):* The A6000 uses the same lens as the A7R5, but is APS-C. So with the 50 mm lens becomes a 75 mm (equivalent) with a roughly 1.5 crop factor. The images profit from the low center distortion of the lens, the distorted corners are cropped away. This becomes visible for all calibrations. The pure amount of correction is way less then for the both full frame cameras. In the example of the A6000 a un-symmetric behavior of the lens is present. This is due to the tangential distortion (P₁,P₂) or the principle point or both. The calibration from CalibIO vary mostly in the radial distortion, but not as extensive a in the A7R5.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/CameraCalibrationFigures/Calibration_A7R5_v2_vs_A7R5_self_and_precalibration_3panel_func1.jpg">
  <figcaption><b>Figure 10</b> Comparison of camera calibration for S1H. Top panel shows self calibration with Metashape and bottom row shows precalibrated images with ChAruCo board. CalibIO calibration on the left, Metashape calibration middle, difference at the right.</figcaption>
</figure>

*S1H (above):* The S1H is a full-frame camera as the A7R5. The camera shows a radial distortion. This is more widely spread around the image, but has a very symmetric character. It reaches pixel offsets from upt o \~75 pix as the A7R5. But other then the differences in the A7R5 , the S1H with its 50 mm lens stays exceptional stable between the between CalibIO and Metashape. The difference is at max \~1 pix, while the difference in the A7R5 is up to \~25 pix. The reason for this is not easy to determine here. I might is caused by manufacturing lens differences. Both lenses has high quality metal housings, the Sony lens features autofocus whereas the Contax lens does not. That mean the lens elements inside the lens just move when the camera is focused for a new distance. But this should be negligible and is most likely not the cause.

## Results doming
As described in the methods the doming error is estimated by a spherical fit to the dense point cloud data. The results show stronger and more moderate doming strenghts between the different cameras and calibration methods. The doming is in some cases visible with naked eyes in the height models of the reconstructions.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/A7R5_DenseCloud_medium_milfFiltering_precalibration_fixedCalib_p12changed_cropped.png">
  <figcaption><b>Figure 11</b> Height model of A7R5 with fixed precalibration.</figcaption>
</figure>

### Sphere fit
We can fit a sphere to the point cloud in order to determine the magnitude of a possible doming error in the generated dense point cloud. In order to do this a least square fit is done using the `scipy` package in Python.

|     | Camera | Calibration        | R (m)   | Z (m)    |
|-----|--------|--------------------|---------|----------|
| 1   | A7R5   | selfcalibration    | 765.65  | -765.65  |
| 2   | A7R5   | precalibration     | 477.18  | -477.18  |
| 3   | A7R5   | precalibration fix | 189.69  | -189.69  |
| 4   | A6000  | selfcalibration    | 1189.79 | -1189.79 |
| 5   | A6000  | precalibration     | 1000.90 | -1000.90 |
| 6   | A6000  | precalibration fix | 475.92  | -475.92  |
| 7   | S1H    | selfcalibration    | 1077.12 | -1077.12 |
| 8   | S1H    | precalibration     | 1110.51 | -1110.51 |
| 9   | S1H    | precalibration fix | 1129.19 | -1129.19 |

When looking at the doming errors it is important to define what is desired to see. As the surface is expected to be as flat as possible, the highest radius resembles the most desired reconstruction. The highest radius shows the lowest curvature in the surface. The Z coordinate of the origin of the sphere defines the direction of the curvature: concave or convex. A negative values shows that the origin of the sphere is located under the surface of the model. After the calibration and model reconstruction, it becomes clear that the precalibration delivers the strongest doming error in 2 of 3 cases. The best performer is the Sony A6000 with the highest radius from the Metashape internal calibration. This aligns with the fact, that the Sony A6000 has the lowest reprojection error in the alignment. For both Sony cameras the doming error increases strongly from the precalibrated values that was free during alignment to the pure precalibrated parameters that stayed fixed during alignment. The fixed precalibration values are the worst for both Sony cameras in terms of doming. The highest curved surface is the one of the A7R5. This is easily visible in the model (see figure above). The results from the S1H show a different behavior: parameters are nearly constant between the different calibration methods. The are close to the internal calibration from the A6000 but then even show lower curvature for the precalibrated values. It should be mentioned that the S1H showed the best results in the precalibration inside CalibIO.

### Local noise levels
To see if the local quality of the models is affected by the calibration in the same way as the doming error, this is tested alongside. As the models are very detailed (Millions of points on a \~4x4 m area), a lot of high frequency variation is present on local neighborhoods inside the models. To see if as low quality calibration also affects the local quality, small areas are extracted as described in the methods section. The observations from these three areas are summarized in the following figure.

<figure>
  <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/stats_Overview_plot.svg">
  <figcaption><b>Figure 12</b> Standard deviation inside the models in different regions. Number determines camera: 1: A6000 Dense Cloud internal calibration, 2: A6000 Dense Cloud precalibration fixed, 3: A6000 Dense Cloud precalibration free, 4: A7R5 Dense Cloud internal calibration, 5: A7R5 Dense Cloud precalibration fixed, 6: A7R5 Dense Cloud precalibration free, 7: S1H Dense Cloud internal calibration, 8: S1H Dense Cloud precalibration fixed, 9: S1H Dense Cloud precalibration free.</figcaption>
</figure>

It is visible that one camera shows different result then the rest. The A7R5 shows that what was looked for, that areas outside the center region contain more noise. That is just present for the one camera A7R5 and here just strong for the external calibration withCalibIO. The two other camera deliver different results. Except a small deviation in the one outside group, the A6000 noise floor stays constant over the hole model. The S1H is even more constant overall. In the S1H a slightly higher noise floor is detected for both outside groups. But with a much lower magnitude than the peaks in the A6000 and A7R5. So all together, a lower local quality in the outside regions for the A7R5 and very subtle for the S1H is indicated by the results. Speaking about a direct causal relationship to the doming error is to early. In this report there is indication, that bad calibration (especially underestimated radial distortion) lead to higher doming errors. But the local noise is likely not directly connected to the doming error, more to the just not fitting calibration. Not fitting calibration (especially the fixed one) forces to Metashape to work with a projection that is not aligning with the data well. So more noise is generated. So the higher doming error occur with more noise in some cases, but further research is needed to determine the exact results. It is usual for edges of models to have lower quality in photogrammetry in general.

# Conclusion
Overall the camera calibration show an strong influence on the doming error inside reconstructed models. The radial distortion, especially the K₁ parameter are likely influencing the doming error directly. This is found from the data collected here. In Both cases where the doming radius dropped strongly between internal and precalibration, the K₁ parameter had half its value, wheras K₂ and K₃ stayed nearly unchanged between cases (see Results Calibration). Second, the local quality for these cases was investigated. The results showed a simultaneous occurrence of higher noise with higher doming in 1/3 cameras strongly, other cameras changes are interpreted as nearly unremarkable, further discussion can be made. The overall noise for them is \< 0.1 mm as standard deviation. Besides the results concerning the geometric quality of the reconstructed models, the used equipment proved its strength in the one way or other. In the reconstruction the APS-C sensor format proved to be more as capable for high quality reconstructions. It performed with best RPE and the lowest doming error for the Metashape-only solution. So the cheaper APS-C camera delivered on point and proved it usability. Nevertheless is should be noted that it likely profited from the expensive high-quality lens and the fact that it has a crop sensor on this full-frame lens. The best calibration results together with the most stable lens parameters had reached the 40 year old manual lens. The reason for that has to be clarified with further testing. From the perspective of this report further testing of different lens/camera combinations with the same test area set-up would be highly interesting. Furthermore, as follow-up research more investigation in the role of K₁ in the doming is suggested. With a synthetic and incremental variation of the K₁ parameter in this real world setting. The resulting doming could be determined and compared to the results in this report.

# References
1:	Luhmann, Thomas and Maas, Hans-Gerd, Industriephotogrammetrie, Photogrammetrie und Fernerkundung, Springer Berlin Heidelberg, p. 105-155, 2017

2:	Fraser, Clive S. "Digital camera self-calibration", ISPRS Journal of Photogrammetry and Remote Sensing , Vol. 52, No. 4, p. 149-159, 1997

3:	Brown, Duane, Close-Range Camera Calibration, 1971

4:	Agisoft, Agisoft Metashape User Manual: Professional Edition, Version 2.2, 2025 

