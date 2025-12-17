---
title: 'Camera Calibration and Mitigating Doming Effects'
author: "Florian Josephowitz"
author_profile: true
date: 2025-12-17
toc: true
toc_sticky: true
toc_label: "Camera Calibration with Calib.IO and Metashape"
header:
  overlay_image: https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/FlorianJosephowitz_figures/untitled_3_crop.jpg
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

