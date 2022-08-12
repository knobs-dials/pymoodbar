# pymoodbar

Python reimplementation of moodbar (see the paper mentioned below for the concept), plus some experiments.

Is a first version, treat with care. Also, (I need to rethink the normalization used)
<br/><br/>

Right now, this is more experiment than drop-in. 

See the links section for things that are probably faster, and generate the .mood files the same way as before.

I wrote this partly for coding exerise, as a testbed to play with some audio, critical band, and equal loudness code, to try creating moodbar-style images with spectral detail, to see how useful it might be as a fingerprint or comparison sort of thing, and maybe later things like beat and rhythm.

Also because the original moodbar implementation annoying to get to compile due to dependencies on older gstreamer.  This one wraps the CLI ffmpeg instead.
(but others have dealt with that better - see the github links below)



## Dependencies
* numpy, scipy (for FFT)
* PIL (for mood-to-image code)
* ffmpeg executable being in the PATH


## moodbar-generate
- runs ffmpeg/avconv in a subprocess and asks it for a mono PCM stream,
- does some FFTs, windowing, 
- applies equal-loudness curve, 
- sorts energy into Bark-style critical bands.
- Generates 
  - the classic RGB-per-1000th-song .mood file (though not weighed the same way)
  - a PNG that is a Bark-style spectrogram, colored by the .mood colors. A few examples of those:

![A few examples: lofi, reggae, rock, calm electro, crust, indie band, ethereal/vocal](screenshots/examples.png?raw=true)

By default, moodbar-generate assumes the parameters are filenames - I think I did this to act as a drop-in.


If you want to recurse into directories, use -r and directory arguments. 

It will then first do a directory treewalk to figure out which files need to be generated (and which stray .mood files could be removed),
before it starts generating.  Yhis can make it slow to start.


For futher arguments:

```
Usage: moodbar-generate [options]

Options:
  -h, --help            show this help message and exit
  -r, --recursive       Recurse directories. Default is to only work on
                        specified file(s). Most options apply only in
                        combination with -r.
  --no-remove           Don't remove .mood files without according media file
  --force-remove        If the remove step thinks it might throw away too
                        much, and you think it's okay, force it with this.
  --no-generate         Only report what we would generate, but don't do it.
  --force-redo          Generate even if one exists already (probably avoid
                        combining with -r unless you mean it)
  --redo-age=REDO_AGE   Generate if older than this amount of days (used for
                        debugging)
  --shuffle             Shuffle generation jobs (makes ETA a little more
                        accurate because of mixed sizes)
  --png-only            Only write the .png file, not the .mood
  -z PARALLEL, --parallel=PARALLEL
                        How many processes to run in parallel. Defaults is
                        detecting number of cores.
  -n, --dry-run         Say what we would generate/remove, don't actually do
                        it.
  -v, --verbose         Print more individual things.

```


## moodbar-text (plaything)

Shell output, with fancy unicode graph stuff and true color option (`-t`) because without that it'll be 8-color and ugly. 

Doesn't have much use, but looks pretty:
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
- reconsider normalizaton, and consider replaygain
- double check that the FFT and sound code actually makes sense
- actually implement moodbar-correlate
- Look at further optimizations for the analysis, it still takes a few seconds per song
- do STFT with overlapping windows?  (bunch more work, little effect)
- look at using PyDub (or similar) instead of my own ffmpeg wrapper?
- look at
    - https://github.com/spezifisch/pymoodbar (py wrapper around the analysis part in C?)
    - https://github.com/globeone/moodbar  (drop-in command, C?)
    - https://github.com/exaile/moodbar  (drop-in command, C?)


## See also 
- G Wood, S O'Keefe (2005), "[On Techniques for Content-Based Visual Annotation to Aid Intra-Track Music Navigation](https://www.google.com/search?q=On%20Techniques%20for%20Content-Based%20Visual%20Annotation%20to%20Aid%20Intra-Track%20Music%20Navigation%20pdf)"
