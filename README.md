# pymoodbar

Python (numpy, scipy) implementation of moodbar.

![A few examples: lofi, reggae, rock, calm electro, crust, indie band, ethereal/vocal](examples.png?raw=true)

Partly for exerise,
partly because I wanted an easier testbed to experiment with various transforms (like critical bands and equal loudness),
partly because I wanted a variant that shows more spectral detail, and maybe later things like beat and rhythm,
partly because the original was annoying to get to compile,
and wanted to see how useful it might be as a fingerprint or comparison sort of thing.

Currently runs ffmpeg/avconv in a subprocess and asks it for a PCM stream.


## Dependencies:
* numpy, scipy
* PIL (for mood-to-image code)
* ffmpeg/avconv being in the PATH, currently on linux


## TODO:
- look at using PyDub instead of my own ffmpeg wrapper
- Look at further optimizations, it takes a few seconds per song.
- look at 
    - https://github.com/spezifisch/pymoodbar (py wrapper around the analysis part in C?)
    - https://github.com/globeone/moodbar  (drop-in command, C?)
    - https://github.com/exaile/moodbar  (drop-in command, C?)

## See also 
- G Wood, S O'Keefe (2005), "[On Techniques for Content-Based Visual Annotation to Aid Intra-Track Music Navigation](https://www.google.com/search?q=On%20Techniques%20for%20Content-Based%20Visual%20Annotation%20to%20Aid%20Intra-Track%20Music%20Navigation%20pdf)"
