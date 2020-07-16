# pymoodbar

Python (numpy, scipy) implementation of moodbar, plus some experiments.

![A few examples: lofi, reggae, rock, calm electro, crust, indie band, ethereal/vocal](examples.png?raw=true)


Why?

Partly for exerise,
 partly because I wanted an easier testbed to experiment with various transforms (like critical bands and equal loudness),
 partly because I wanted a variant that shows more spectral detail, and maybe later things like beat and rhythm,
 partly because the original was annoying to get to compile, 
 and I wanted to see how useful it might be as a fingerprint or comparison sort of thing.

Currently runs ffmpeg/avconv in a subprocess and asks it for a PCM stream.

## Dependencies:
* numpy, scipy
* PIL (for mood-to-image code)
* ffmpeg/avconv being in the PATH, currently on linux



## Further experiments
 
- moodbar-text - unicode graphs and stuff
![text-mode output](textmood.png?raw=true) 


- moodbar-correlate - idea like that
     - finding duplicates
     - given some options, you can try to avoid harsh genre changes based on similar high/low distribution


## TODO:
- Look at further optimizations for the analysis, it still takes a few seconds per song
- look at using PyDub (or similar) instead of my own ffmpeg wrapper
- look at
    - https://github.com/spezifisch/pymoodbar (py wrapper around the analysis part in C?)
    - https://github.com/globeone/moodbar  (drop-in command, C?)
    - https://github.com/exaile/moodbar  (drop-in command, C?)

## See also 
- G Wood, S O'Keefe (2005), "[On Techniques for Content-Based Visual Annotation to Aid Intra-Track Music Navigation](https://www.google.com/search?q=On%20Techniques%20for%20Content-Based%20Visual%20Annotation%20to%20Aid%20Intra-Track%20Music%20Navigation%20pdf)"
