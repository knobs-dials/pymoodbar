# pymoodbar

Python implementation of moodbar.

Partly for exerise,
partly because I wanted an easier testbed to experiment with various transforms (like critical bands and equal loudness),
partly because I wanted a variant that shows more spectral detail, and maybe later things like beat and rhythm,
partly because the original was annoying to get to compile,
and wanted to see how useful it might be as a fingerprint or comparison sort of thing.



Runs ffmpeg/avconv in a subprocess and asks it for a PCM stream.

ffmpeg rather than gstreamer (as used by the original mooodbar) because I didn't
like the unknowns of the gstreamer interface, varying with compilation and installaton state.
Which is entirely stubborn, yes, because this is probably similarly fragile.



Dependencies:
* numpy, scipy
* PIL (for mood-to-image code)
* ffmpeg/avconv being in the PATH, currently on linux



TODO:
- Look at further optimizations, it takes a few seconds per song.

