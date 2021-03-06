---
title: 'Using an iPad or Samsung Galaxy with Android as Whiteboard'
author: "Bodo Bookhagen"
author_profile: true
date: 2020-10-24
permalink: 
toc: true
toc_sticky: true
toc_label: "iPad and Android-as-Whiteboard"
header:
read_time: false
tags:
  - Ubuntu
  - Android
  - iPad
  - Galaxy
  - Whiteboard
  - teaching
  - PDF
  - Annotating
---

Can you use your Samsung Galaxy or iPad as an input device / whiteboard for online teaching?

We are especially interested in a setup that also works with the online teaching environment [BBB (Big Blue Button)](https://bigbluebutton.org/). There are different commercial options available for iOS and Windows - but I am working on Ubuntu. In the past weeks, I have been searching for an easy and straight forward way to link an Ubuntu Desktop system with a touch-sensitive iPad or Samsung Galaxy - mostly for teaching purposes and as a white-board replacement.

**Note that the iPad and Galaxy Note Series will not replace a professional graphics and drawing tablet. This is a low-cost solution, because most of us own a tablet.**

I found and looked at the following two options:

1. There is [GfxTablet+](https://www-fourier.ujf-grenoble.fr/~demailly/GfxTablet+.html) that is build on the older (and now unmaintained [GfxTablet](https://github.com/rfc2822/GfxTablet)). This contains a driver `networktablet+` that emulates an input device in X11. Using an app on Android (*GfxTablet+.apk*), you can connect via Wifi to the host and mirror your stylus output. However, I found this difficult to control (although other users really liked it) and I could not draw on existing images or graphs and could not annotate PDFs. This does not work for iOS.
2. [Weylus](https://github.com/H-M-H/Weylus) uses a similar input device scheme, but mirrors the screen in a web browser on your tablet. The input is considerable more laggy with a few ms delay. But the big bonus is that you can control any open window on your desktop in your webbrowser on the tablet, including shell and other software that requires keyboard and mouse input. Since I am not using an Android tablet for extensive hand writing (there is much better hardware available for that), but rather edit and annotate/enhance existing images, [Weylus](https://github.com/H-M-H/Weylus) is a good option.

# Installation
Installation of Weylus is straightforward. Get the latest binary releases from
[https://github.com/H-M-H/Weylus/releases](https://github.com/H-M-H/Weylus/releases) and setup the `uinput` device as described on their [github page](https://github.com/H-M-H/Weylus).

When starting `weylus`, you should use a passphrase. Identify your IP - I found the NVIDIA hardware acceleration to be slightly faster and turned it on (see below). *Make sure your firewall allows access to the port.*

<figure>
    <a href="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/images/weylus1.png"><img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/images/weylus1.png"></a>
    <figcaption>Setup screen (use proper binding address) and turn on hardware acceleration if applicable.</figcaption>
</figure>


# Running Weylus
For drawing on sheets and PDFs, the [Xournal++](https://github.com/xournalpp/xournalpp) app comes in handy. It allows to annotate PDFs and images and has a variety of drawing options. Also, you can directly add LaTeX equations and you can combine input from a Stylus Pen with keyboard input.

From your Android device use *Chrome* (I didn't succeed in using the Samsung Webbrowser) or *iPAD's Safari* and log in to your device. When you are successfully logged in, select the application you want to work in (this could also be *gimp*) and start drawing!

<p float="middle">
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/images/Android_screenshot.jpg" width="45%"/>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/images/apple_ipod_weylus_example.png" width="45%"/>
</p>
*Above screenshots on left is from an Android Galaxy Note S6 at first login. You can select a specific application or your entire desktop. Right side shows screenshot from an iPad showing xournal++ with edits on an image (copy and paste from a Jupyter Notebook).*


<p float="middle">
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/images/Weylus_BBB_write1.png" width="45%"/>
<img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/images/Weylus_BBB_write2.png" width="45%"/>
</p>
*Left side: You can control BBB from the iPad/Android tablet. Right side: Make sure to increase display size to full screen. All icons and tools on the left-hand side can be controlled with the Stylus/Pencil from the tablet. Screenshots taken with an iPad and Apple Pencil.*

# Combing [Weylus](https://github.com/H-M-H/Weylus), [Xournal++](https://github.com/xournalpp/xournalpp), PDF presentations and [OBS](https://obsproject.com/)
In a typical teaching environment and setting, you mix PDF/Powerpoint presentation and whiteboard usage. We are recording our PDF Presentations presented in a window with [OBS](https://obsproject.com/) and can switch to a different window when recording. This allows to activate the Xournal++ window when using the Android tablet as whiteboard. It requires some clicking (activating different windows for recording), but with some practice it goes smoothly and allows a seamless integration of whiteboard recordings and presentations.

<div style="text-align:center;">
<video width="960" height="540" controls>
  <source src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/mp4/RSE_WS20_L02_weylus_clip.mp4" type="video/mp4" width="960" height="540" frameborder="0" scrolling="no"  allowfullscreen>
</video>
</div>

<script type="text/javascript"> DiscourseEmbed = { discourseUrl: 'https://discourse.up-rs-esp-3.geo.uni-potsdam.de/', discourseEmbedUrl: 'https://up-rs-esp.github.io//Android-as-Whiteboard_I/' };
(function() { var d = document.createElement('script'); d.type = 'text/javascript'; d.async = true; d.src = DiscourseEmbed.discourseUrl + 'javascripts/embed.js'; (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(d); })(); </script>

