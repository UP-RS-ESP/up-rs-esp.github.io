---
title: 'Linux Setup Suggestion: Tiling Window Manager'
author: "Bodo Bookhagen"
author_profile: true
date: 2025-11-02
toc: true
toc_sticky: true
toc_label: "Building an Efficient Research Environment with a Tiling Window Manager"
header:
  overlay_image: https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Windows_tiling_manager/tmux_nvim_ssh_pane_clip.png 
  overlay_filter: 0.3
  caption: "Tiling Window manager with tmux"
read_time: false
tags:
  - Window Tiling Manager
  - Archlinux
  - Omarchy
  - tmux
---

Tiling window managers create efficient, distraction-free workspaces that are particularly well-suited for coding, writing, and scientific research. Unlike traditional desktop environments where windows overlap, a tiling window manager arranges windows in non-overlapping frames—maximizing screen space and minimizing the need for a mouse. In this post, I'll describe my personal setup, the reasoning behind it, and the tools that make my workflow fast, minimal, and enjoyable.

# Introduction
There are many ways to set up a work environment, and ultimately, everyone needs to find what fits their workflow best. You can choose between operating systems — macOS, Windows, or Linux — and, within each, there are countless window managers, editors, and toolchains to explore. This post isn't about convincing you which system is "best". Instead, I'll walk through the setup that helps me stay productive, organized, and visually content.

## A bit of background
I'm an old-school Unix user — Linux has been my home since the mid-1990s (yes, I ran it on an i486 and a Pentium). While I happily use a mouse for graphics-related tasks like mapping or working in Google Earth, I'm far more comfortable navigating my system via the keyboard. It's faster, more efficient, and perfect for laptop use — especially since I've never truly gotten used to touchpads.

**Minimalism and focus:** I like a clean, distraction-free workspace. I don't need pop-up notifications, weather widgets, or constant alerts cluttering my screen. When I'm coding or writing, I turn off email and focus on the task at hand. A minimal interface helps me think clearly and stay immersed in the work.

**My everyday tools:** Most of my time is spent in the terminal—specifically at the [bash](https://www.gnu.org/software/bash/) prompt and inside [neovim](https://neovim.io/). After twenty years of using [vim](https://www.vim.org/), I finally migrated to Neovim and haven't looked back. My setup is highly customized, full of shortcuts, aliases, and plugins that streamline daily tasks.

**One thing at a time:** I prefer working with a single application per workspace. On Linux, these are called workspaces; on macOS, Spaces. I typically keep separate workspaces for email, web browsing, the shell, and specialized tools like QGIS or Metashape.
This workflow naturally led me to tiling window managers. They automatically arrange windows in clean, non-overlapping tiles. When a new window opens, it simply appears beside the others — no dragging, resizing, or hunting for hidden windows.

# Previous Setups
For years, I worked on [Ubuntu](https://ubuntu.com/), but I eventually decided to move away from it — at least for my laptop and smaller work environments. The introduction of [snap](https://snapcraft.io/) packaging in Ubuntu didn't sit well with me; I felt I was losing too much control over my system. For example, I ran into repeated issues with Thunderbird until I uninstalled the snap version and compiled it manually. Similarly, compiling certain scientific tools (like GAMIT, see also known issues: https://geoweb.mit.edu/gg/issues.php#ubuntu) became unnecessarily difficult. That said, I still use [Ubuntu Server LTS](https://ubuntu.com/download/server) for our Remote Sensing Cluster at the University of Potsdam — it's stable, reliable, and well-maintained.

I experimented with [i3](https://i3wm.org/) on top of [XFCE](https://www.xfce.org/). I found [Arch Linux](https://archlinux.org/) and XFCE to be a useful combination. It worked well, though it lacked visual polish. Later, I ran [Manjaro](https://manjaro.org/) with XFCE, which offered a good balance between performance and usability.

For terminal work, I used [kitty](https://sw.kovidgoyal.net/kitty/). It's fast and elegant but lacks advanced session management features like multiplexing and remote handling found in [tmux](https://github.com/tmux/tmux/wiki) or GNU [screen](https://www.gnu.org/software/screen/).

# My Current Tiling Window Manager Setup
**A word of warning: if you're coming from a traditional Windows or macOS environment, tiling window managers will feel unfamiliar at first. There are no icons, minimal graphical menus, and most navigation happens via keyboard shortcuts. But once you get used to it, it's hard to go back.**

After months of experimenting with Ubuntu, XFCE, and i3, I returned to my old favorite: Arch Linux. Recently, I discovered a sleek Arch-based distribution called [Omarchy](https://omarchy.org/), built around the [Hyprland](https://hypr.land/) tiling window manager running on Wayland. Omarchy uses  [Alacritty ](https://github.com/alacritty/alacritty) as its terminal emulator, which integrates beautifully with Neovim and tmux. The system feels fast, modern, and visually refined—without sacrificing minimalism. It even includes thoughtful shortcuts, like convenient screenshot tools reminiscent of older macOS features. What I appreciate most is that Omarchy comes well pre-configured out of the box, so it's immediately usable and efficient. At the same time, all configuration files are centrally organized and fully customizable, making it easy to tweak or extend the environment as your workflow evolves.


## The core of my workflow
I run Alacritty in fullscreen with tmux managing multiple panes and sessions. This combination is lightweight, responsive, and ideal for research workflows.

To enhance integration, I use [omarchy-tmux]( https://github.com/joaofelipegalvao/omarchy-tmux), which provides seamless shortcuts between tmux and the desktop environment. In Neovim, I use [vim-slime](https://vimawesome.com/plugin/vim-slime) or the newer [tmux.nvim](https://github.com/aserowy/tmux.nvim)) plugin for direct interaction between panes. This setup allows me to edit code locally and execute it remotely — instantly and securely—without extra software or configurations. For instance, I can have Neovim open in one pane and an active SSH session to a remote HPC cluster in another. Selecting code in visual mode and sending it to the remote shell happens with a simple keybinding — no mouse, no lag, no fuss.

<center>
<figure>
  <a href="tmux_nvim_ssh_panes.png">
    <img src="https://github.com/UP-RS-ESP/up-rs-esp.github.io/raw/master/_posts/Windows_tiling_manager/tmux_nvim_ssh_panes.png" alt="tmux neovim setup">
  </a>
  <figcaption>Figure 1: Example tmux setup. The left pane runs Neovim locally, while the right pane connects to a remote HPC server via SSH. Code can be selected and executed remotely with a single keystroke — fast, efficient, and distraction-free.</figcaption>
</figure>
</center>

# Conclusion
Tiling window managers are not for everyone. They demand time, patience, and a willingness to break old habits. But once mastered, they offer a fluid, efficient, and distraction-free environment that's hard to beat—especially for scientific work and coding-heavy research. If you value focus, keyboard-driven workflows, and a clean aesthetic, a tiling window manager might just transform the way you work.

