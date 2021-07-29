import os
import sys
import time
import array
import math

import numpy
import numpy.fft
import scipy
import scipy.ndimage

import helpers_ffmpeg

''' This was an experiment in moodbar, adding equal loudness and critical bands.

    I may implement it in something more portable once I'm satisfied. I may be too lazy.


    Mono 16-bit is hardcoded in places.  Sample rate could be more easily changed.

    Two-process and takes more than one core, but less than two fully because ffmpeg is held up by our calculations.


    TODO: 
    - see if pydub makes everything better. Which is also using ffmpeg, but very likely more mature than my code.
    - check for presence of ffprobe and ffmpeg before running
    - see whether https://github.com/spezifisch/pymoodbar is better than this in most ways.

    CONSIDER: use a power-of-two sample rate, for FFT speed, if ffmpeg allows it.
'''



### dB(B) coorection  (specifically that bcause meant for intermediate loudness.  Sure it's not really for music, but easy)
_dbb_lut_db = [] # index is hz, elements are dB
_dbb_lut_f  = [] # index is hz, elements are factor

def _dbb_genlut(uptohz=22050):
    ''' Returns dB adjustment according to dB(B) filter at a given (integer) frequency
        (returned values max out at about -0.20dB)
    '''
    _dbb_lut_db.append( 0 ) # 0 for 0Hz (DC)
    _dbb_lut_f.append( 0 )
    for hz in range(1,uptohz+1):
        f2 = float(hz)**2
        f3 = float(hz)**3
        a = 148840000.0  # 12200.**2
        b = 424.36       # 20.6**2
        c = 25122.25     # 158.5**2
        Rb= (a * f3 )/( (f2+b)*(f2+a)*math.sqrt(f2+c) )
        
        db_adjust   = 0.17 + 20.*math.log(Rb)
        factor_adjust = 10.**(0.05*db_adjust)
        _dbb_lut_db.append( db_adjust )
        _dbb_lut_f.append( factor_adjust )
   
def dbb_db(hz):
    ' this function assumes the lookuptable has been generated; this module calls that at module scope (i.e. happens at import time) '
    if len(_dbb_lut_db)==0:
        _dbb_genlut()
    hz=int(hz)
    return _dbb_lut_db[hz]

def dbb_factor(hz):
    ' this function assumes the lookuptable has been generated; this module calls that at module scope (i.e. happens at import time) '
    if len(_dbb_lut_f)==0:
        _dbb_genlut()
    hz=int(hz)
    return _dbb_lut_f[hz]





### Frequency-to-bark,   to accumulate per bark band
# The usual implementation is just a few explicit thresholds.
# This lookup table is lazy and overkill, but was handy while comparing critical band functions...
_bark_lut = []

def _bark_genlut(uptohz=22050):
    for hz in range(uptohz+1):
        _bark_lut.append( bark_traunmuller(hz) )
      
def bark_traunmuller(hz, mn=0, mx=23):
    ''' Critical band rate (Hz->Bark), according to Traunmuller 1990.
        The result is truncated to 0..23 (inclusive) by default
        in part because the formula itself returns <0 for <40Hz, 
    '''
    v = (26.81*float(hz))/(1960.+float(hz)) - 0.53
    v = max(v, mn)
    v = min(v, mx)
    return int(v)

def bark(hz):
    if len(_bark_lut)==0:
        _bark_genlut()
    hz = int(hz)
    return _bark_lut[hz]




#### Decoding and helpers ##########################

def covering_windows(ary,  window_size,  min_overlap):
    ''' Returns a bunch of windows of a given size, from a possibly-larger array. Made for time series, so 1D.
    
        In moodbar context primarily to be able to work on 1/1000th at a time, but not FFT tha all at once
        because that's terrible when a track is on the order of an hour (that'd be ~200ksamples).

        Instead, we'd want to take much smaller windows however many it takes to cover that 
        and average their results.
        

        In addition to using all all samples, while guaranteeing a minimum overlap (e.g. for FFT windowing reasons)
        In other words, find the smallest amount of steps that has at least that amount of overlap.

        min_overlap     > 1 is interpreted as amount of samples,
        min_overlap in 0..1 is interpreted as a fraction of window_size
          Note that for FFT and window-function reasons, more than ~0.3 is overly expensive 
          and more than 0.5 doesn't make sense
        
        Note that since this assumes all data must be looked at,
          we are biased to sometimes choose a rather higher overlap than requested,
          particularly if the window_size isn't much smaller than the input size
          e.g. 4096 with window_size 512 and min_overlap 0   is 8 steps of size 512 (0 overlap)
               4096 with window_size 512 and min_overlap 1   is 9 steps of size 448 (64.0 overlap)
               4096 with window_size 512 and min_overlap 128 is 11 steps of size 358.4 (153.6 overlap)
    '''
    w, = ary.shape
    
    if w < window_size: # TODO: think about this more.
        yield ary
    
    else:
        fmi = float(min_overlap)
        if fmi>0.0 and fmi<1.0:
            min_overlap = int(math.ceil(fmi*window_size))
            #print "min_overlap from float (%.3f * %d) means %d "%(fmi, window_size, min_overlap)
        
        # brute force this, I'm too lazy to think about it right now - though I expect it's just a sub and div. Ahem :)
        wsteps = None
        for numsteps in range( int( max(2,w / window_size)), int(w/2) ): # sane limits
            st = numpy.linspace( window_size, w, numsteps )
            #print window_size, w, numsteps, st
            stepsize = st[1]-st[0]
            #print stepsize
            overlap = window_size-stepsize
            if overlap >= min_overlap:
                #print "Dividing width %s into %d steps (stepsize is %.1f) gives %.1f overlap"%(w,numsteps,  stepsize,overlap)
                wsteps = numsteps
                break

        for xoff in numpy.linspace(0, w-window_size, wsteps):
            fromx = int(xoff)
            tox   = int(math.floor(fromx+window_size))
            #print 'x',xoff, ' ', fromx, '..', tox, tox-fromx
            yield ary[fromx:tox]


class DecodeError(Exception):
    pass



###
_hcache = {}
def hanning(size):
    ' cache because 99%+ of these will be the same, and occasionally other sizes '
    if size in _hcache:
        return _hcache[size]
    else:
        ret = numpy.hanning(size)
        _hcache[size]=ret
        return ret
    
    
def make_mood(mediafilename):
    '''Given a media filename (probably mp3, ogg, or such) 

       What it does:
       - get length   (using ffprobe) (to be able to do the second point and third points streaming-style)
       - split into 1000 equal-sized chunks
       - stream-decode file  (using ffmpeg)   (should take ~1sec of CPU  per 4MB of MP4)
       - FFT each chunk
       - reweigh buckets for human perception:
         - sum into Bark buckets (so non-linear)
         - db(B) to adjust bucket amplitudes for perceptive
        
       Returns:
       - a 1000x24 uint8 numpy matrix (bark bands)
       - a 1000x3 uint8 numpy matrix (moodbar RGBs)
         (You could save these to binary data with ary.tostring())
       ...or None,None if it decides it can't.

       TODO:
       - optimize, once I've played with and settled on all the weighing
       - deal better with few-second files
    '''    
    sample_rate = 22050 
    # TODO: figure out cost/benefit against FFT speed (Resampling to 22050 adds maybe 30% on top of decode calculations.)
    # TODO: see if ffmpeg can output arbitrary sample rates
                                    
    estlength_sec = helpers_ffmpeg.get_length(mediafilename, decode=False)
    nsamples = estlength_sec * sample_rate
    # Note that since our use is just Bark bands, we can get away with 1024 or 2048

    if nsamples < 128000:    # ..5sec
        return None,None
        #overlapsize = 8
        #fftsize     = 64
    elif nsamples < 256000:  # ..11sec
        overlapsize = 16
        fftsize     = 128
    elif nsamples < 512000:  # ..23 secs
        overlapsize = 32
        fftsize     = 256
    elif nsamples < 1024000: # ..46 secs
        overlapsize = 32
        fftsize     = 512
    else: # most cases
        overlapsize = 64
        fftsize     = 1024
    #print nsamples,fftsize,overlapsize
    #    print "SKIP, too small (%s sec (%d samples) for %r)"%(estlength_sec, nsamples, mediafilename)
    #    # See if we can just force fftsize smaller instead?
    #    return None,None
    bucketsize  = int( 1+fftsize/2 )

    
    chunklen_samples = int( nsamples / 1000. )
    # note: int will truncate so this will add up time-error-wise.
    # right now I choose not to care, but I should rewrite the logic for this.

    #print 'Length estimate (ffprobe): ~%.3f seconds, ~%d samples'%( estlength_sec, nsamples )
    #print "Which would be ~%d samples @ %dHz"%(estlength_sec * sample_rate, sample_rate)
    #print "Each 1/1000-length chunk is ~%d samples"%(chunklen_samples)

    # our first goal is to sum into bark-bands per 1000th-length segment
    bark_ary = numpy.zeros( (24,1000), dtype=numpy.float32 ) 
    try:
        chunksample_gen = helpers_ffmpeg.stream_audio(mediafilename, sample_rate, chunk_samples=chunklen_samples) # generator

        samplepos = 0 # keep track of how much data we saw
        for i, chunksamples in enumerate(chunksample_gen):
            
            if i==1000: # TODO: remove the need for this? (it's because we under-read a little, see chunklen_samples)
                break
            if len(chunksamples)==0: # TODO: remove the need for this?
                break
            #print "chunk %s gets samples %d..%d (of %d)"%(i, samplepos, samplepos+len(chunksamples), nsamples,) # for debug of that time error
            
            samplepos += chunksamples.shape[0]

            if 0:
                # show progress in song-time terms  (was also double-check with stdout entions)
                at_seconds = float(samplepos) / sample_rate
                sys.stdout.write( "at %dm%02ds (of ~%dm%02ds)  in %r\n"%(
                    at_seconds/60, at_seconds%60,  estlength_sec/60, estlength_sec%60,
                    os.path.basename(mediafilename)
                    ))
                sys.stdout.flush()
            
            # constants given the above
            approx_width_hz = float( sample_rate/2. )/float( fftsize/2 )
            barkbuckets     = numpy.zeros(bucketsize, dtype=numpy.uint8)
            factoradjusts   = numpy.zeros(bucketsize, dtype=numpy.float32)
            for fi in range(bucketsize):
                approx_center = (0.5+fi)*approx_width_hz  
                barkbuckets[fi]   = bark(approx_center)
                factoradjusts[fi] = dbb_factor( approx_center )

            for windowsamples in covering_windows(chunksamples, fftsize, overlapsize): 
                #if len(windowsamples)==0: # TODO: remove the need. This shouldn't happen?
                #    raise ValueError('bug in code, covering_windows outputted something %d long'%len(windowsamples))
                
                # TODO: pad if smaller because we baked in size assumptions - length of the last chunk will typically be shorter
                
                windowsamples *= hanning( len(windowsamples) )
                
                #print "chunk %d window %d: %d samples"%(i,wi, len(windowsamples))
                ft = numpy.fft.rfft( windowsamples )
                amp = numpy.abs( ft ) # amplitude spectrum

                #pwr = amp**2  # PSD gives more contrasty spectrograms, but I like there being more to color.
                amp /= fftsize # normalize 

                # TODO: compare to decibel (via log)
                
                # reminder: bark_ary is a 24-by-1000-sized thing,
                #           amp is 1+fftsize/2 sized to be mapped into 24 via barkbuckets,  and summed into bark_ary
                #barkbuckets looks something like 0 0 0 0 0 1 1 1 1 2 2 2 2 3 3 3 3 3 4 4 4 4 4 5 5 5 5 5 6 6 6 6 6 6 6
                #                                 7 7 7 7 7 7 8 8 8 8 8 8 8 8 9 9 9 9 9 9 9 9 9 etc
                # so this, while not the most efficient, is understandable and brief
                values, counts = numpy.unique(barkbuckets, return_counts=True)
                for bbuck,cnt in zip(list(values),list(counts)):
                    #print i,  windowsamples.shape
                    try:
                        bark_ary[bbuck][i] = amp[barkbuckets==bbuck].sum()/cnt
                    except Exception as e:
                        pass
                        #if i>900:
                        #    break   
                        #pass
                        #print mediafilename
                        #print e
                        #sys.exit(0)
                        
        for dump in chunksample_gen: # TODO: remove the need
            pass
            
    except DecodeError:
        at_seconds = float(samplepos) / sample_rate
        #print "Decode error at %dm%02ds (of %dm%02ds)"%(at_seconds/60, at_seconds%60,  estlength_sec/60, estlength_sec%60)
        diffsec = abs(at_seconds-estlength_sec)
        if diffsec > 3:
            print( "Decode before end, difference is %.2f seconds"%diffsec)
            raise
        else:
            print("Decode error at end (%.1f sec difference to estimated length) - small difference, probably something like stray APEv2, fine."%diffsec)

    # CONSIDER: a fixed-dB range instead of either of these.    
    if 0:
        # normalize barks overall (it's basically a bark-style spectrogram)
        hperc = numpy.percentile(bark_ary,90)    
        bark_ary /= (hperc/255.)
    elif 0:
        # normalize per band. This is less valid, but more colorful.
        for barkband in range(24):
            hperc = numpy.percentile(bark_ary[barkband],97)
            if hperc !=0:
                bark_ary[barkband] /= (hperc/255.)
    else:
        pass
        #bark_ary *= 2 # most things are not the loudest possible, soo this spreads the distribution to cover most of the ~255 scale
                
    #import pandas, matplotlib.pyplot as plt
    #df = pandas.DataFrame(data=bark_ary).T
    #print df
    #print df.describe()
    #plt.imshow(bark_ary, cmap='gray', vmin=0, vmax=255)
    #plt.show()
    
    ### Generating a more classic RGB moodbar just means summing 24 bark_ary rows into 3 somehow.
    # there's a shorter way of doing this, which I'll do when I'm done tweaking
    colorweight = (5.0, 5.0, 4.0, 3.0,                               # lo  (red)
                   2.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,                  # mid (blue)
                   1.0,1.0,1.0,1.0,1.0,1.0,2.0,2.0,2.0,3.0,3.0,5.0)  # hi  (green)
    mood_ary = numpy.zeros( (3,1000), dtype=numpy.float32 )
    mood_ary[0] += bark_ary[0]*colorweight[0]    #  ~50Hz
    mood_ary[0] += bark_ary[1]*colorweight[1]    #  150
    mood_ary[1] += bark_ary[2]*colorweight[2]    #  250 #bassy ends hereish
    mood_ary[1] += bark_ary[3]*colorweight[3]    #  350
    mood_ary[1] += bark_ary[4]*colorweight[4]    #  450
    mood_ary[1] += bark_ary[5]*colorweight[5]    #  550
    mood_ary[1] += bark_ary[6]*colorweight[6]    #  650
    mood_ary[1] += bark_ary[7]*colorweight[7]    #  700
    mood_ary[1] += bark_ary[8]*colorweight[8]    #  850
    mood_ary[1] += bark_ary[9]*colorweight[9]    # 1000
    mood_ary[2] += bark_ary[10]*colorweight[10]  # 1150
    mood_ary[2] += bark_ary[11]*colorweight[11]  # 1350
    mood_ary[2] += bark_ary[12]*colorweight[12]  # 1600
    mood_ary[2] += bark_ary[13]*colorweight[13]  # 2100  
    mood_ary[2] += bark_ary[14]*colorweight[14]  # 2500
    mood_ary[2] += bark_ary[15]*colorweight[15]  # 2900
    mood_ary[2] += bark_ary[16]*colorweight[16]  # 3400
    mood_ary[2] += bark_ary[17]*colorweight[17]  # 4000
    mood_ary[2] += bark_ary[18]*colorweight[18]  # 4800
    mood_ary[2] += bark_ary[19]*colorweight[19]  # 5800
    mood_ary[2] += bark_ary[20]*colorweight[20]  # 7000
    mood_ary[2] += bark_ary[21]*colorweight[21]  # 8500
    mood_ary[2] += bark_ary[22]*colorweight[22]  #10500
    mood_ary[2] += bark_ary[23]*colorweight[23]  #13500
    

    
    # Try to get a decent spread of most colors via some basic factor correction
    #  (also factor decrease, since we just did a many-buckets-to-one we just did)
    #  consider there's an effect from equal-loudness, but also from the unequal summing just now)
    #  also keep in mind 0=red, 1=blue, 2=green

    #df = pandas.DataFrame(data=mood_ary).T
    #print df.describe()
    #plt.imshow(bark_ary, cmap='gray', vmin=0, vmax=255)
    #plt.show()
    
    mood_ary[0] *= 0.12 
    mood_ary[1] *= 0.18
    mood_ary[2] *= 0.90

    #df = pandas.DataFrame(data=mood_ary).T
    #print df.describe()

    
    #mx = numpy.max(mood_ary)
    #mood_ary /= mx
    #mood_ary[0] = 1.0  * (mood_ary[0]**2.1)
    #mood_ary[1] = 0.55 * (mood_ary[1]**2.8)
    #mood_ary[2] = 0.28 * (mood_ary[2]**2.8)    
    #mood_ary *= mx

    #mood_ary *= 3
    #mood_ary /= 3
    
    #bark_ary = scipy.ndimage.maximum_filter(bark_ary, size=(1,4))
    bark_ary = scipy.ndimage.percentile_filter(bark_ary, 70, size=(5,2)) # make it seem more blocky, but still retain some spectrogram
    #mood_ary = scipy.ndimage.gaussian_filter(mood_ary, sigma=(0.6,0.2))

    #bark_ary 
    
    #if normalize_moodbar:
    # normalize moodbar per band (CONSIDER: maybe not? and/or maybe first take out bottom percentile?)
    # and scale to 0..255 for rgb image
    #hperc0 = numpy.percentile(mood_ary[0], 70) # lowish percentile to bring out the lower parts (and clip the higher)
    #hperc1 = numpy.percentile(mood_ary[1], 70)
    #hperc2 = numpy.percentile(mood_ary[2], 70)
    #if hperc0+hperc1+hperc2>0:
    #    if 0:
    #        mood_ary[0] /= hperc0/255.
    #        mood_ary[1] /= hperc1/255.
    #        mood_ary[2] /= hperc2/255.
    #    else:
    #        mood_ary /= ((hperc0+hperc1+hperc2)/3)/255.

    mood_ary[mood_ary<0]=0
    mood_ary[mood_ary>255]=255


    # make spectral things more visible (after moodbar thing, to not affect color)
    mx = numpy.max(bark_ary)
    bark_ary  /= mx
    bark_ary **= 0.35
    bark_ary  *= mx
    
    bark_ary[bark_ary<0]   = 0
    bark_ary[bark_ary>255] = 255    
    
    return bark_ary.T.astype(numpy.uint8), mood_ary.T.astype(numpy.uint8)

        


def read_mood(filename):
    ''' Reads a .mood file into one flat array, which will probably be 3000 items long '''
    stob = os.stat(filename)
    f = open(filename)
    data = f.read()
    data = array.array('B',data).tolist()
    f.close()
    return data


def mood_image(filename, height=20, width=None):
    ''' Given the path to a standard 3-band .mood image, will generate a PIL image for it. 

        One color per width (rgb mix, stretched up to height)
        width by the file size (which in practice should always be 1000 but we're resistant to others)

        You can rescale to a new width (interpolated) by supplying one. Default is not to do so.

        (TODO: be resistant against ridiculous widths from both file size and from resize request)
    '''
    from PIL import Image, ImageFilter
    data = read_mood(filename)
    oo256 = 1./256.
    numsamples = len(data)/3
    img = Image.new('RGB',(numsamples,1) )
    for i in range(0,len(data),3):
        r,g,b = data[i:i+3]
        r = int( ((r*oo256)**0.57)*255 )
        g = int( ((g*oo256)**1.2)*255 )
        b = int( ((b*oo256)**1.2)*255 )
        img.putpixel( (i/3,0), (r,g,b)  )
    newsize = list(img.size)
    if height:
        newsize[1]=height
    if width:
        newsize[0]=width
    newsize = tuple(newsize)
    if img.size != newsize:
        #print newsize
        if newsize[0]<1000: # if scaling down, blur first. CONSIDER: do this in other methods too?
            #print "BLUR %.2f"%(1000./newsize[0])
            img = img.filter( ImageFilter.BoxBlur( 300./newsize[0] ) )
        img = img.resize( newsize )
    return img


def mood_image3(filename, height=21, width=None):
    ''' like mood_image, but shows three bands, with the r, g, b separately. Was partly a debug thing.
    '''
    from PIL import Image, ImageFilter
    # could play with things like horizonal median?
    data = read_mood(filename)
    oo256 = 1./256.
    
    numsamples = len(data)/3
    img = Image.new('RGB',(numsamples,3) )
    for i in range(0,len(data),3):
        r,g,b = data[i:i+3]
        img.putpixel( (i/3,0), (r,0,0)  )
        img.putpixel( (i/3,1), (0,g,0)  )
        img.putpixel( (i/3,2), (0,0,b)  )
        
    newsize = list(img.size)
    if height:
        newsize[1] = height
    if width:
        newsize[0] = width
    newsize = tuple(newsize)
    if img.size != newsize:
        img = img.resize( newsize, Image.NEAREST ) # assuming it's just vertical, this may be a little faster- but CONSIDER BILINEAR is more generic?
    return img

    
def fancy_image(barkary, moodary):
    ''' Own experiment mixing moodbar's colors with the bark spectrogram we made
             
        Takes the output pair from make_mood:
        - the 24-band bark version while we still have it,
        - the more typical 3-band one we could read later),
        (we could work from just barkary, as moodary is just weighed from it),
        uses both to make effectively is a mood-colored 1000x24px bark-spectrogram image 
    '''
    from PIL import Image
    spe = Image.new('RGB',(1000,24) )

    # color it like the standard moodbar, one color for each time interval.
    for i in range(0,1000):
        lo, mid, hi = moodary[i][0], moodary[i][1], moodary[i][2] # could be weighted from barkary
        for bark in range(24):
            val = barkary[i][bark]
            fval = float(val)/256.
            spe.putpixel( (i,23-bark),  #23-   puts low freqs at bottom, not top
                          (int(lo*fval),int(hi*fval),int(mid*fval))  )
                          # note this deviates from moodbar: jere blue is mid, green is high

    return spe



style_ascii    = ' .-~=#'
style_ascii    = ' .oO'
style_vertical = u' \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2589'
style_shades   = u' \u2591\u2592\u2593\u2589'

def mood_text(filename, width=78, color=True, truecolor=False, style=style_vertical):
    ''' RGB-colored, Unicode-block-characters-using line of terminal goodness '''
    import helpers_shellcolor as sc # TODO: deal with absence
    
    im = mood_image(filename, height=1, width=width)
    
    def char_for_v255(i, charset=style):
        f = float(i)/256.
        l = len(charset)
        i = f*l
        #print i,charset[int(i)]
        return charset[int(i)]

    ret = []
    for x in range(im.size[0]):
        r,g,b = im.getpixel( (x,0) )
        l = 0.3*(r+g+b)
        c = char_for_v255(l)
        # CONSIDER: consider saturation, not just 'is 1 more than the others'
        if truecolor:
            ret.append( sc.true_colf(c, r,g,b) )            
        elif color:
            ret.append( sc.closest_from_rgb255(r,g,b, mid=150)(c) )
        else:
            ret.append( c )        
    return ''.join(ret)
    
