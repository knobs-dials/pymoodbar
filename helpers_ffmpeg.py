'''
    Experimenting with how robustly we can use ffmpeg CLI command to be a waveform reader for us,
    so that we don't have to deal with binary linking with the ffmpeg libraries (or similar).

    In the current use we ask ffmpeg for 16-bit mono, and return chunk_samples-sized float32 numpy arrays at a time.

    I wanted this to be a generator for streaming reasons, and it turned out detecting decode failure involves,
    so it became a more messy threaded thing because. It may be possible to simplify that.

    TODO:
    - detect ffmpeg/ffprobe ahead of time rather than just assuming they're there, fail out with proper message properly
      - detect avconv as well as ffmpeg
    - rethink the thready details, it may mean the process may not get cleaned up?
'''

import os
import time
import numpy
import threading
import subprocess
try:
    import Queue
except:
    import queue as Queue


def get_length(filename, decode=False): #, debug=False
    """ Gets media length, in seconds, using ffprobe. 

        I've seen this be off by 0.5 seconds,
        but often is close to 0.05 seconds or so (a value seemingly related to media frame size, e.g. of MP3?)

        Note that 0.05 for a 240-second song is a few thousandths off.
    """
    # CONSIDER: AV_LOG_FORCE_NOCOLOR in environ
    command = [ 'ffprobe',
                '-i', filename, '-show_entries', 'format=duration',
                #'-v', 'level+info',   # on stderr
                '-v', 'level+warning',   # on stderr
                '-of', 'csv=p=0' ] # strips the structure, leaves just the single value.  Could also consider flat, compact, json, xml
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    # TODO: look at retcode, like 'not such file'?
    
    try:
        return float( out.strip() )
    except:
        if b'misdetection possible' in err:
            msg = '- seems to not be audio file: %r'%filename
        else:
            msg = "- ffprobe's response was:\n%s)"%(err.strip())
        raise ValueError("Failed to read length %s"%(msg,))
        


def _err_reader(fh, buf, sharedstate):
    ''' Reads ffmpeg's stderr, in part because it seems the best possible indication of decode errors.

        I don't think I can use universal_newlines when I want the same process's stdout to be binary, so we do it ourselves.
    '''
    line = b''
    while True:
        ch = fh.read(1) 
        #print( "READCH=%r"%ch )
        if len(ch)==0:
            sharedstate['finished'] = True  # EOF, without having previously quit because errors.
            if len(line)>0: # output what's left
                buf.append(line)
            break
        if ch in b'\r\n': # newline?  output line
            #print( '[stderr]'+repr(line) )
            buf.append(line)
            line = b''
        else:
            line += ch
            # last line doesn't necessarily get a newline, so test is more interesting
            if line.startswith(b'Error while decoding stream'):
                #print( '[stderr]'+repr(line) )
                sharedstate['failed'] = True
                # we could break now
                buf.append(line) # which is incomplete but still useful
                break
                #...CONSIDER: not doing so, somehow reading up to EOF
                
        
def _out_chunker(fh, output, bytesperchunk, sharedstate):
    ''' Read ffmpeg's stdout, which contains the raw audio stream, 
        and puts() its data to output, which is expected to be a queue (because thread-safe).
        of uint16 numpy arrays arrays.

        Note that we don't do the "did we read 0 bytes" EOF test on this stream (stdout)
        because it may EOF early when failing on errors.
        It's actually up to stderr handler to decide whether we finished okay or not.
    ''' 
    bbuffer = b''
    bytes_seen = 0
    while len(sharedstate)==0: # will stop on finished or failed
        justreadbytes = fh.read(bytesperchunk)
        bbuffer += justreadbytes
        if len(justreadbytes)==0:  # we're at EOF, but this thread can't itself tell whether we are fine, or crashed.
            continue

        while len(bbuffer) >= bytesperchunk:
            #print "regular - current buffer byte len %d,  bytes previously seen %d"%(len(bbuffer),bytes_seen)
            now = bbuffer[:bytesperchunk]
            bbuffer = bbuffer[bytesperchunk:]
            bytes_seen+= len(now)
            #print "  now returning %d bytes worth of audio; now at %d "%(len(now), bytes_seen)
            audio = numpy.fromstring(now, dtype=numpy.int16).astype(numpy.float32)
            output.put( audio ) # will block when full, because queue
            
        if len(sharedstate)>0:
            if 'finished' in sharedstate: # then finish up before returning
                # then there will be fewer than chunk_size bytes left in bbuffer,
                # which we still want to output
                bytes_seen+= len(bbuffer)
                #print "finishing; buflen %d; bytes_seen %d"%(len(bbuffer), bytes_seen)
                audio = numpy.fromstring(bbuffer, dtype=numpy.int16).astype(numpy.float32)
                output.put( audio )
            break

        
def stream_audio(filename, sample_rate, chunk_samples, debug=False):
    """ Given 
        * any file that ffmpeg can play the audio from,
        * the sample rate you want it in
        * how many samples per chunk you want

        Yields a series of float32 numpy arrays (mono, for now)
        which will be chunk_samples-sized (except for the last)

        There are some lefovers from the first version loading the entire song in one numpy array,
        but that was always going to be replaced by streaming - an hour-long track would eat all your RAM.
     
        This function raises ValueError when ffmpeg fails out.
         There is an interesting footnote to this: sometimes the things e.g. the MPEG muxer trips over
         I consider to be non-issues, so like an APEv2 tag at the end (such as that added by mp3gain). 
         So you _may_ want to decide that if the decoded length is within about a second of the length ffprobe estimates, all is well.
         TODO: make it more defined/known whether we get the last samples, or might quit early.
        Raises IOError if the file does not exist
    """
    # hardcoded(ish) because it simplifies the only way I currently call it.
    bytesperchunk = chunk_samples*2 # because 2 bytes per sample, otherwise the numpy conversion is ehh
    format_string = 's16le'
    numchannels   = 1  # mono

    # TODO: suppress stderr coloring via NO_COLOR
    command = [
        'ffmpeg',
        '-i', filename,
        '-f', format_string,      '-acodec', 'pcm_'+format_string,
        '-ar', str(sample_rate),  '-ac', str(numchannels),
        '-af', 'volume=replaygain=track',
        # verbosity of stderr. default is info
        '-v', 'level+info',   
        #'-v', 'level+warning',
        '-']
    #print ' '.join(command)
    if debug:
        print( ' '.join(command) )

    if not os.path.exists( filename): # saves a subprocess
        import errno
        raise IOError( errno.ENOENT, os.strerror(errno.ENOENT), filename)
    
    subproc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  bufsize=bytesperchunk)

        
    sharedstate = {} # we need an object, to pass around by reference (rather than a primotive, by value).  This could be done more elegantly, yes.
    err_lines = []
    out_chunks = Queue.Queue(10) # threadsafe producer/consuner, with a max amount of items.
    err_thread = threading.Thread(target=_err_reader, args=(subproc.stderr, err_lines, sharedstate))
    err_thread.start()
    out_thread = threading.Thread(target=_out_chunker, args=(subproc.stdout, out_chunks, bytesperchunk, sharedstate))
    out_thread.start()
    try:
        seen_samples = 0
        while True:
            while out_chunks.qsize()>0: 
                audiosamples = out_chunks.get() # will block, consider using timeout?
                seen_samples += audiosamples.shape[0]
                secs = float(seen_samples)/sample_rate
                if debug:
                    print( "at %d samples, = %.2f seconds, = %dm%02ds"%(seen_samples, secs, secs/60, secs%60 ) )
                yield audiosamples
            if 'failed' in sharedstate: # either of those will eventually become true
                if debug:
                    print( '[%s] FAILED'%filename )
                break
            if 'finished' in sharedstate:
                if debug:
                    print( '[%s] FINISHED'%filename )
                break
            retcode = subproc.poll()
            #if retcode!=None: # so, ffmpeg generally returns nonzero on errors, but not always.
            #    deal with quiet success
            #    it will however tell us it's finished. 
            #    print retcode
            #    sleep(1) # give the err-reader some time to process all input
            #    break
            time.sleep(0.05)

        if debug:
            print( '[%s] ERRWAIT '%filename )
        err_thread.join()
        if debug:
            print( '[%s] ERRWAITOK '%filename )
        
        # note that in theory, both finished and failed can be set, and failed should take precedence
        if 'failed' in sharedstate:
            subproc.terminate() # note: catch   OSError: [Errno 3] No such process
            if debug:
                print( '\n'.join(err_lines[-4:]) )
            #raise ValueError('ffmpeg reported decode failure for %r'%filename)
        
        if debug:
            print( '[%s] OUTWAIT '%filename )
        out_thread.join()
        if debug:
            print( '[%s] OUTWAITOK '%filename )
        
        if 'failed' in sharedstate:
            raise ValueError('ffmpeg reported decode failure for %r'%filename)
        
    finally:
        pass
        # TODO: remember what cleanup we need to do exactly.
        #subproc.stdout.close()
        #subproc.stderr.close()


        
if __name__ == '__main__':
    ' Try to decode each mentioned file, as a test ' 
    import sys
    for filename in sys.argv[1:]:
        try:
            samplerate  = 44100
            samplecount = 0

            start_time = time.time()
            for chunk in stream_audio(filename, sample_rate=44100, chunk_samples=44100, debug=True):
                samplecount+=len(chunk)
            took_time = time.time() - start_time

            lens=float(samplecount)/samplerate
            print( "Decoded %s samples (%dm%.1fs) from %r in %.1f seconds (%dx)"%(
                samplecount,
                lens/60, lens%60,
                filename,
                took_time,
                lens/took_time,
                ) )
        except IOError as e:
            print( e )
