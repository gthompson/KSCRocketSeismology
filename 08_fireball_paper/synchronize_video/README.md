# Python conversion starter

This folder converts the MATLAB architecture described in the uploaded
`README_video_sync` into two separable pieces:

1. `polarization.py`
   - metadata-driven sensor rotation to ZNE using ObsPy
   - ZNE -> ZRT
   - ZNE -> LQT
   - explicit sliding covariance eigenanalysis
   - linearity, rectilinearity, planarity
   - azimuth and incidence of principal axis
   - optional TwistPy complex-signal ellipticity

2. `video_sync.py`
   - one or more local video files, each with an absolute UTC start time
   - timestamp-based video frame retrieval using PyAV
   - full-window/scrolling waveform panels
   - optional polarization scroller
   - frame rendering to PNG
   - ffmpeg assembly to MP4

3. `example_falcon9_sync.py`
   - skeleton showing how the modules connect.

## Why ellipticity is separate

Classic real covariance eigenanalysis naturally gives rectilinearity/linearity
and planarity. "Ellipticity" has several definitions and a true polarization
ellipse is better estimated from the complex analytic signal. TwistPy's
`TimeDomainAnalysis3C` implements that approach, so `polarization.py` exposes
it as the preferred ellipticity calculation rather than silently defining a
different quantity.

## Install

```bash
pip install numpy scipy matplotlib obspy av
pip install twistpy   # optional
```

You also need `ffmpeg` on PATH to assemble PNG frames into MP4.

## Next conversion step

For a faithful Falcon 9 port, map the numerical values in
`+falcon9/rocketEventConfig20160901.m` into `SyncConfig`, then replace the
placeholder waveform selectors and overlay delays in `example_falcon9_sync.py`.
