---
title: Ball → Sound — Sonifying a Translucent Ball
date: 2026-08-12
type: exhibit
tags: [computer-vision, sonification, ableton]
images: []
draft: false
---

## About

Making a translucent ball audible: track it through a camera, map the trajectory to sound. The tracking side is honest engineering research — which is to say, documented failure included.

## The tracking problem

The baseline apparatus (OpenCV `TrackerMIL` + Hough single-ball detector, GoPro as webcam) lacks multi-object tracking, denoising, and stable IDs. Candidate replacement: DEVA (Cheng et al., ICCV 2023, arXiv:2309.03903), a decoupled video-segmentation framework.

I reimplemented DEVA from scratch, zero learned weights, 614 lines of OpenCV + numpy + scipy: pluggable segmenters, optical-flow mask propagation, exact branch-and-bound MWIS for the in-clip consensus, bipartite matching for merges. The synthetic demo passes exactly as the paper claims: bi-directional consensus denoises flicker (0 survivors); causal online mode keeps ghost IDs.

## The honest limitation

On the real 234-frame dataset of the translucent ball, it fragments badly (101 IDs). Root cause, diagnosed directly: dense optical flow cannot propagate a semi-transparent object — the background bleeds through, the flow field captures the camera, and masks drift. The learned propagator (XMem-class) is the next step, not more classical flow.

## Sound side

Ableton sound-design spec and TouchDesigner tracker spec define the mapping from trajectory to sound.

Related: [[listening-as-method]].
