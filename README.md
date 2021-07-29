# pymoodbar

Python (numpy, scipy) implementation of moodbar (see the paper mentioned below for the concept), plus some experiments, in particular trying for a little more detail:

First version, treat with care.


In general, if you want a drop-in that is fast, or generates the .mood files the same way, you probably do NOT want this one.

...because I made this partly for exerise,
 partly because I wanted an easier testbed to experiment with various transforms (like critical bands and equal loudness),
 partly because I wanted images with more spectral detail, and maybe later things like beat and rhythm,
 partly because the original was annoying to get to compile, and partly because I wanted to see how useful it might be as a fingerprint or comparison sort of thing.



## Dependencies
* numpy, scipy
* PIL (for mood-to-image code)
* ffmpeg/avconv being in the PATH, currently on linux


## moodbar-generate
- runs ffmpeg/avconv in a subprocess and asks it for a mono PCM stream,
- does some FFTs, windowing, 
- applies equal-loudness curve, 
- sorts energy into Bark-style critical bands.
- Generates 
  - the classic RGB-per-1000th-song .mood file
  - and a PNG that is a Bark-style spectrogram, colored by the .mood colors. A few examples of those:

![A few examples: lofi, reggae, rock, calm electro, crust, indie band, ethereal/vocal](screenshots/examples.png?raw=true)

By default it assumes the parameters are filenames (I think I did this to act as a drop-in).

If you want to recurse into directories, use -r. 

Keep in mind it will then first do a scan for which .mood files can be removed, and which need to be generated.
This treewalk will make it slowish to start.

For futher arguments:

```
Usage: moodbar-generate [options]

Options:
  -h, --help            show this help message and exit
  -r, --recursive       Recurse directories. Default is to only work on
                        specified file(s). Most options apply only in
                        combination with -r.
  --no-remove           Don't remove apparently lone moods
  --force-remove        If the remove step thinks it might throw away too much
                        and you think it's okay, force it with this.
  --no-generate         Only report what we would change, but don't do it.
  --force-redo          Generate even if one exists already
  --redo-age=REDO_AGE   Generate if older than this amount of days
  --shuffle             Shuffle jobs (makes ETA a little more accurate because
                        of mixed sizes)
  --smallest-first      Do smallest files first
  --largest-first       Do largest files first
  -z PARALLEL, --parallel=PARALLEL
                        How many processes to run in parallel. Defaults is
                        detecting number of cores.
  -n, --dry-run         Say what we would generate/remove, don't actually do
                        it.
  -v, --verbose         Print more individual things.
```


## moodbar-text (plaything)

Shell output, with fancy unicode graph stuff and truecolor (`-t`, it'll be 8-color and ugly without). Because why not?
![text-mode output, unsorted selection of songs](screenshots/textmood_tc.png?raw=true) 

```
Usage: moodbar-text [options]

Options:
  -h, --help            show this help message and exit
  -w WIDTH, --width=WIDTH
                        Width. Default is to detect it from the shell
  -a, --style-ascii     Draw with just ASCII characters
  -b, --style-verticalbars
                        Draw with vertical bars (Unicode) (default)
  -s, --style-shades    Draw with shaded blocks (Unicode)
  -n, --nocolor         Don't use color codes.
  -t, --truecolor       Use true-color codes.
  -v, --verbose         Print more individual things.

```

## moodbar-correlate  (experiment)

Based on the ideas that...
- you can probably find duplicates   (moodbar images already makes it easier to visually inspect suspected duplicates)
- given some options, you can try to avoid harsh genre changes based on similar high/low distribution


## TODO:
- check that the FFT sound code actually makes sense
- do STFT with overlapping windows
- actually implement moodbar-correlate
- Look at further optimizations for the analysis, it still takes a few seconds per song
- look at using PyDub (or similar) instead of my own ffmpeg wrapper
- look at
    - https://github.com/spezifisch/pymoodbar (py wrapper around the analysis part in C?)
    - https://github.com/globeone/moodbar  (drop-in command, C?)
    - https://github.com/exaile/moodbar  (drop-in command, C?)


## See also 
- G Wood, S O'Keefe (2005), "[On Techniques for Content-Based Visual Annotation to Aid Intra-Track Music Navigation](https://www.google.com/search?q=On%20Techniques%20for%20Content-Based%20Visual%20Annotation%20to%20Aid%20Intra-Track%20Music%20Navigation%20pdf)"
