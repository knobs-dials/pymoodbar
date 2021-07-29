import time
#import numpy
import sys

import helpers_format
import helpers_shellcolor as sc # only for style_invert


style_simple     = '.='
style_angle      = '.>>>>>>>>>>>='  # cheating to make it fairly certain there's a > as a head
style_O          = ' O'
style_3O         = ' .oO'
style_E          = ' .-+=#'
style_spinascii  = ' -\\|/-\\|/-\\|/-\\|/-\\|/='
style_vertical   = u' _\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2589' # doesn't look good in all fonts
style_horizontal = u' \u258F\u258E\u258D\u258C\u258B\u258A\u2589\u2588'  # doesn't look good in all fonts
style_shades     = u' \u2591\u2592\u2593\u2589'                          # doesn't look good in all fonts
style_mouse      = '~(,,)">'      # see code
style_invert     = 'DUMMY_INVERT' # see code


def pmean(data):
    return float(sum(data))/len(data)

def _sumsquare(data):
    mean = pmean(data)
    return sum(float(v-mean)**2  for v in data)

def pstd(data):
    " (population) standard deviation "
    n = len(data)
    ss = _sumsquare(data)
    pvar = ss/n
    return pvar**0.5



class ProgressBar(object):
    ''' Progress bar,
        with basic statistics, so that we can say "will be done in two hours, +- fifteen minutes"
        (currently using mean and std, which is a not-exactly-accurate first version)

        tl;dr:
        - Initialize: pb = ProgressBar(numjobs)
        - optional: call pb.start() when you start processing
          (optional because it's implied by the first increment, but doing so yourself means the ETA is a little closer to correct)
        - call pb.increment() when you finish jobs  (if you finish in chunks, hand in their size)
        - call pb.simple() when you want it to do the printing for you
          which will only print when it hasn't done so in a while (avoids throttling by program's own tty output)
          there are some helpers if you want more manual control.
        - optional: after you're done, call a call pb.simple(forcedraw=True) (of pb.forcedraw()), so that it shows at 100%

        - don't call this ridiculously often. Say, counting stats of 5000000 files individually means this code will be your bottleneck.
          in that case, increment() in relative bulk

        TODO:
        - variant not based on counts, but on each job's start and finish time
          (overkill for trivial jobs, but more accurate for long-running ones.
           also allows slightly fancier bar)
        - allow "...at the rate seen in the last five mintes", or more trend analysis based ETA.          

        CONSIDER:
        - ability to separately count jobs that fail immediately, so that we could skip them in ETA
    '''
    def __init__(self, numjobs=0, style=None, colnum=None, interval_sec=0.3):
        ' colnum defaults to detecting (which itself might fallback to a built in value, currently 60) '
        self.jobs = numjobs
        self.done = 0
        if style:
            self.style = style
        else:
            #self.style = style_3O
            #self.style = style_simple
            #self.style = style_horizontal
            self.style = style_invert
            #self.style = style_mouse
        self.last_time = None
        self.last_report = None
        self.times = []
        self.colnum = colnum
        self.interval_sec = interval_sec
        # mainly so that eta() doesn't bork before the first increment()
        self.mean = 0
        self.std = 0
        try: # react to window changes on platforms that send sigwinch (e.g. excludes windows)
            import signal
            signal.signal(signal.SIGWINCH,  lambda signum,sframe: self._sigwinch_trigger() )
        except: # haven't figured out all the things that might fail
            pass

    def _sigwinch_trigger(self):
        self.cols(update=True)
        
    def set_numjobs(self, numjobs):
        ' In case you change your mind later (or like argumentless construction) '
        self.jobs = numjobs

    def start(self):
        ''' To get the timing of the first job right, call this when you start it. 
            If you're lazy and job are short, you can count on the first increment_jobs() to set it.
        '''
        self.last_time = time.time()
        self.last_report = time.time()

    def increment(self, amt=1):
        ''' Signal that you've finished amt jobs (default 1) since the last time you called this. 
        '''
        if amt==0: # if people do increment(amt=len(batch)) on an empty batch.
            return 
        if self.last_time == None:
            self.last_time = time.time()
        if self.last_report == None:
            self.last_report = time.time()

        now = time.time()
        taken = now - self.last_time
        self.done = min( self.done+amt, self.jobs )

        self.times.append( (taken)/float(amt) )
        #print self.times
        self.last_time = time.time()
        
        self.mean = float( pmean( self.times  ) )
        self.std  = float( pstd(  self.times ) )


    ## Stuff related to showing it
    def cols(self, update=False, fallback=60):
        ''' Reads the amount of columns from the tty.
            Then stores it and returns this cached value, unless you call this with update 
            If tty will not cooperate, we fall back to the passed-in fallback,
            which by default is conservative
        '''
        if self.colnum == None or update:
            #print "Updating cols from TTY"
            try:
                import helpers_shellcolor
                self.colnum = int(helpers_shellcolor.tty_size()['cols'])
            except:
                self.colnum = fallback
        return self.colnum

    

    def bar(self, forcecols=None):
        ''' returns the bar as a string.  
            Width taken from self.cols(), which should follow window resizes. Width can also be forced.  '''
        ret = ['']

        amounts = self.amounts()
        eta = '  ETA: %s'%self.eta()
        
        if self.style == style_invert:
            aftertxt = ''#eta
        else:
            aftertxt = ' %s %s'%(amounts, eta)    
            
        if forcecols:
            havecols = forcecols
        else:
            havecols = self.cols()

        barcols = havecols - (2+len(aftertxt))

        if self.style == style_invert:
            intxt = amounts
            intxt+= '    '+eta
            intxt = '%s%s'%( ' '*  int( (barcols-len(intxt))/2),  intxt )
        else:
            intxt = ''
        
        if self.jobs == 0:
            ret.append('no jobs queued')
        else:
            #ret = ['[']
            if self.style == style_mouse:
                frac = float(self.done)/float(self.jobs)
                mouse  = list(style_mouse)
                cheese = list('<')
                ret.extend( [' ']*barcols )
                ret[-len(cheese):] = cheese
                nosepos = max(0, int(frac*barcols))
                mouselen = max(0, min(len(mouse),nosepos))
                if nosepos>0:
                    ret[1+nosepos-mouselen:1+nosepos] = mouse[-mouselen:]               
            else:
                # 0..1 fraction for the entire range
                donefrac   = float(self.done)/float(self.jobs)
                fullchars  = int(donefrac*barcols)
                emptychars = max(0, barcols-(fullchars+1))

                if self.style == style_invert:
                    #s = ' %d%% done ' %(100.*donefrac)
                    s = intxt
                    str1 = ('%%-%ds'%(fullchars))%s[:fullchars]
                    str2 = ('%%-%ds'%(emptychars))%s[fullchars:]
                    ret.append( sc.BLACK+sc.BGWHITE + str1 )
                    ret.append( sc.WHITE+sc.BGBLACK + str2 )
                    ret.append( sc.RESET )
                else:
                    #The one inbetween is basically whatever fractions represent its start and end
                    # rescaled to 0..1 
                    blockfrac = 1./barcols # each block represents this much of the whole

                    # we need the point between the drawn boxes and the next one
                    partfrac = (donefrac*barcols) - int(donefrac*barcols)
                    # and rescale that to 0..1, or rather, 0..amountofchars

                    #print barcols,fullchars,emptychars
                    ret.append( self.style[-1]*fullchars )
                    if donefrac<1.0:
                        ret.append( self.style[ int(partfrac*len(self.style)) ] )
                    ret.append( self.style[0]*emptychars )
                    # TODO: think about this boundary cases, I didn't care when I wrote this ^^
                    
            #ret.append(']')
        ret.append(aftertxt)
        return ''.join(ret)

    def amounts(self):
        return '%d / %d'%(self.done, self.jobs)

    def eta(self, as_str=True):
        ''' If as_str==True, it returns a printable string. 
            If False, it returns a 2-tuple, the stdev-based range we're guessing it will be done in (unix timestamps)
        '''

        now = time.time()

        if self.jobs == 0:
            if as_str:
                return 'N/A'
            else:
                return now
        elif self.done==0: # maybe should be if not( at least 5 or at least 1% )
            return '(calculating)'
        else:
            left = max(0,  self.jobs - self.done)
            rest_time = self.mean*left
            rest_std  = self.std*left


            #TODO: better date formatting, e.g. omit day if it's today
            if as_str:
                if rest_std < 50:
                    return '~%s'%helpers_format.shortish_dt( now+rest_time+rest_std, omit_today=True )
                else:
                    return "between %s and %s"%(
                        helpers_format.shortish_dt( max(now,now+rest_time-0.2*rest_std), omit_today=True ),
                        helpers_format.shortish_dt( now+rest_time+0.5*rest_std, omit_today=True ),
                        )
            else:
                return (now+rest_time-rest_std, now+rest_time+rest_std)

        
    def time_to_report(self, interval=None, reset=True):
        ''' Is it time to report again, according to this minimum interval?  (When it returns True, it resets the counter, assuming you will act on it). 
            Interval defaults to what was handed into the constructor. 
               Handing in true returns True, mostly for a case in simple()
        '''
        if interval == True:
            return True
        if interval == None:
            interval = self.interval_sec
        if time.time() - self.last_report > interval:
            if reset:
                self.last_report = time.time()
            return True
        return False



    def simple(self, width=None, interval=None, print_for_me=sys.stderr, alsoflush=True, sameline=True, forcedraw=False):
        ''' Laziness function, one that lets you just call this and not worry:

            By default it prints a new bar, with a maximum speed (via a minimum interval),
              or, if it wasn't time to update it yet, does nothing.              
        
            Interval defaults to what was handed into the constructor.
            If interval==True, it always acts.   
              ...use of forcedraw is functionally identical,
                 but more clearly shows the intent in your calls.

            sameline (Default true) prints on the same line, assuming ANSI
              you may want to not do this if you're also outputting a bunch of other stuff.

            if print_for_me == None, it returns a string (or None)
               if it's not none, it's expected to be a stream we can write() on.
        '''
        if interval == None:
            interval = self.interval_sec
        if interval == True or forcedraw:
            act = True
        else:  # I think the following can't deal with True, TODO: check
            act = self.time_to_report(interval=interval, reset=True)
        
        if not act:
            return None
        else:
            s = ''
            if sameline:
                s+='\r\x1b[2K' # carriage resturn, erase line
            s += self.bar()

            if print_for_me:
                print_for_me.write( s + '\r') # extra carriage return so that any other messages overwrite the line, instead of starting from near its end
                if alsoflush:
                    print_for_me.flush()
            else:
                return s
            
    def forcedraw(self):
        self.simple(forcedraw=True)

    def debug_print(self):
        import helpers_format
        left = max(0,  self.jobs - self.done)
        print( "Jobs are taking %.3fsec on average, stdev %.3f"%(self.mean, self.std))
        print( 'Did %d jobs of %d'%(self.done, self.jobs))
        #print "Time left: %s (+- %s)"%(
        #    helpers_format.nicetimedelta( self.mean*left ),
        #    helpers_format.nicetimedelta( self.std*left ),
        #    )
        
        #print self.bar()

        #try:
        #    import helpers_histogram
        #    helpers_histogram.print_histogram( numpy.array( self.times ) )
        #except ImportError:
        #    print "no helpers_histogram"
        


def main():
    import random
    import sys
    
    styles = [ ('(default)',None) ]
    for name in dir(sys.modules[__name__]):
        if name.startswith('style_'):
            styles.append(  (name, getattr(sys.modules[__name__], name))  )
        
    jobbase = 120
    colnum = None#75
    for name, style in sorted(styles):
        simjobs = random.randint( int(0.9*jobbase), int(1.1*jobbase) )

        try:
            print( "Style %r"%name )
            pb = ProgressBar( simjobs, style, colnum=colnum, interval_sec=0.1)
            pb.start()
            for i in range(simjobs):
                wait = abs(random.gauss(0.09, 0.11))# + random.gauss(0.41, 0.2))
                #print 'Sleeping',wait
                time.sleep( wait )

                pb.increment( )
                pb.simple() 

                #pb.debug_print()
            pb.simple(forcedraw=True)
            print
        except KeyboardInterrupt:
            print
            pass # skip to next
    
    
if __name__=='__main__':
    main()
