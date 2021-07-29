import math,random,datetime, re, stat

### Magnitude consideration

def kmg(amount,kilo=1000, append='',thresh=15, nextup=0.9, rstrip0=True, extradigits=0, i_for_1024=True):
    """ For more easily skimmable sizes

        e.g.
             kmg(3429873278462) == '3.4T'
             kmg(342987327)     == '343M'
             kmg(34298)         == '34K'

             '%sB'%kmg(2342342324)                           == '2.3GB'
             '%sB'%kmg(2342342324, kilo=1024)                == '2.2GiB'
             '%sB'%kmg(2342342324, kilo=1024, extradigits=1) == '2.18GiB'
             '%sB'%kmg(19342342324, kilo=1024)                == '18GiB'
             '%sB'%kmg(19342342324, kilo=1024, extradigits=1) == '18GiB'  (because of rstrip0)

        Decimal/SI kilos by default, so useful beyond bytes.
        Specify kilo=1024 if you want binary kilos. By default this also adds the i.

        thresh is the controls where we take one digit away, e.g. for 1.3GB but 16GB.
        Default is at 15 which is entirely arbitrary. 
        Disable using None.

        nextup makes us switch to the next higher up earlier, e.g. 700GB but 0.96TB
        Disable using None.
 
        extradigits=1 (or maybe more) to unconditionally see a less-rounded number
        (though note rstrip can still apply)

        rstrip0     whether to take off '.0' if present (defaults to true)
        append      is mostly meant for optional space between number and unit.
    """
    ret = None

    mega = kilo*kilo
    giga = mega*kilo
    tera = giga*kilo
    peta = tera*kilo
    exa   = peta*kilo
    zetta = exa*kilo
    yotta = zetta*kilo

    if nextup==None:
        nextup = 1.0
    if thresh==None:
        thresh = 1000
    nextup = float(nextup)

    # Yes, could be handled a bunch more more compactly (and used to be)

    showdigits=0
    if abs(amount) < nextup*kilo: # less than a kilo; omits multiplier and i
        showval = amount
    else:
        for csize, mchar in ( (peta, 'P'),
                              (tera, 'T'),
                              (giga, 'G'),
                              (mega, 'M'),
                              (kilo, 'K'),
                              #(exa,  'E'),# exa, zetta, yotta is shown as peta amounts. Too large to comprehend anyway.
                              #(zeta, 'Z'),
                              #(yotta,'Y'),
           ):
            if abs(amount) > nextup*csize:
                showval = amount/float(csize)
                if showval<thresh:
                    showdigits = 1 + extradigits
                else:
                    showdigits = 0 + extradigits
                append += mchar
                if i_for_1024 and kilo==1024:
                    append += 'i'
                break

    ret = ("%%.%df"%(showdigits))%showval

    if rstrip0:
        if '.' in ret:
            ret=ret.rstrip('0').rstrip('.')

    ret+=append

    return ret


def parse_kmg(s, kilo=1000, listen_to_i=False):
    """ '1k'         --> 1024
        '2 MB'       --> 2097152
        '1.51Gflops' --> 1621350154
        Defaults to binary thousands.
        Looks for kmgtp.
        Ignores anything not [0-9kmgtp]        
        
        quick and dirty implementation, may need work.

        Kilo defailts to decimal kilos.
        If you want binary kilos, specify it, or set listen_to_i=True
        (for things like 4.5KiB).
        This is false by defauly because you ought to
        know the amount of preformatting you need to do
    """
    if listen_to_i and 'i' in s:
        kilo=1024

    mega=kilo*kilo
    giga=mega*kilo
    tera=giga*kilo
    peta=tera*kilo

    ns=re.sub(r'[A-Za-z]','',s) #s.rstrip('kmgtpKMGTPiIbB') # or just everything?
    if ns.count(',')==1: # pseudo-relocalization.
        ns=ns.replace(',','.') # e.g. for dutch people.
    try:
        ret=float(ns)
        sl=s.lower()
        # TODO: test whether it's right after the number, to avoid words with these letters messing things up.
        if 'k' in sl: 
            ret *= kilo
        elif 'm' in sl:
            ret *= mega
        elif 'g' in sl:
            ret *= giga
        elif 't' in sl:
            ret *= tera
        elif 'p' in sl:
            ret *= peta
        ret=int(ret)
        return ret
    
    except Exception as e:        
        print( "Didn't understand value %r"%ns )
        print( e )
        raise



def parse_hms(v):
    ''' string interval spec to seconds, e.g.  
         '1h30m' -> 5400, 
         '1 day, 30 min, 4 sec' -> 88204
        Very naive implementation (just looks for words starting with w,d,h,m,s)
    '''
    ret_sec = 0
    things = re.findall(r'([0-9.]+)\s*([a-z]+)[,;\s-]*', v.lower())
    if len(things)==0:
        try:
            ret_sec = float(v) # see if it's unitless, interpret as seconds
        except:
            raise ValueError("don't understand value %r"%unit)
    for num,unit in things:
        #print num,unit
        n = float(num)
        if unit[0]=='w':
            n *= 60*60*24*7
        elif unit[0]=='d':
            n *= 60*60*24
        elif unit[0]=='h':
            n *= 60*60
        elif unit[0]=='m':
            n *= 60
        elif unit[0]=='s':
            pass
        else:
            raise ValueError("don't understand time unit %r"%unit)
        ret_sec += n

    return ret_sec




# See sfloat below
def sfloat_na(f,                                  removetrail=1,  extradigits=0, estyleabove=100000):
    return sfloat(f, fixedwidth=0,  aligndigit=0, removetrail=removetrail, extradigits=extradigits, estyleabove=estyleabove)

def sfloat_noalign(f,                                  removetrail=1,  extradigits=0, estyleabove=100000):
    return sfloat(f, fixedwidth=0,  aligndigit=0, removetrail=removetrail, extradigits=extradigits, estyleabove=estyleabove)

def sfloat_align(f,  fixedwidth=10, aligndigit=4, removetrail=1,  extradigits=0, estyleabove=100000):
    return sfloat(f, fixedwidth,    aligndigit,   removetrail,    extradigits, estyleabove)

def sfloat(f,        fixedwidth=10, aligndigit=4, removetrail=1,  digits=None, extradigits=0, estyleabove=100000):
    ''' Idea: show only one or two significant digits at small scales,
        to make for easily skimmable figures by having their length (and alignment) indicate their scale.
        ...yes, this does defeat the scientific significant-digits approach. Easier to read, though.
        It's also sort of makeshift at best, or at least biased towards specific interests.

        Started because of eigenvector expression and other fractions that can work at different orders of magnitude. 
        Numbers printed like 3.2345e-3 and 4.2342e-5 take time to compare even though they are hugely different.
        Examples:
        
           3.66528e-08  -> '0'
           8.22697e-05  -> '0.000082'
           0.0717395048 -> '0.072'
           0.050000     -> '0.05'
           0.932929494  -> '0.9'
           0.988        -> '1.0'
           18.5608302   -> '18.5'
           6762.73408   -> '6763'
        Also note that *very* tiny numbers become 0, e.g.:
             1.49e-08  -> '0'

        You can force the amount of digits 
           e.g. to get mostly the alining/zero-strippin behaviour,
           or when you're consistently printing an array and just used digits_for_range
        
        removetrail will remove trailing zeroes, and the digit if that's all that's left. 
           0.00 -> 0
           0.50 -> 0.5
        (I'm still thinking whether this should be on or off by default)
        
        fixedwidth places it in a string that will be a given width
          (unless the thing you want to print is itself wider)
          meaning you can tell this function to make column-like output without wrapping that yourself
        
        aligndigit will try to add spaces so that the digit is some minimum area from the right edge of the string.
          Note that it will still move for small-enough numbers. This is by design, for my idea of inspectibility. E.g.
            '1000   '
            '  10.2 '
            '   1.0 '
            '   0.01'
          but:
            '0.00001'
       
        extradigits can be used to increase the amount of digits to show by some constant.

        It often make sense to use fixedwidth when you use aligndigit, and increase the former when you up the latter.
    '''
    if type(fixedwidth) in (int, #long,
                                float):
        fixedwidth=str(int(fixedwidth))
        
    af = abs(f)
    if af>estyleabove:
        ret= '%.1e'%f # '6.1e+07' style (in part to keep it shortinsh so that fixedwith makes sense)
        removetrail=0 # there's a digit before the e and there may be a trailing 0, but we don't want that removed.

    else: 
        if 0: # could do something clever here, say...
            digits = max(0,round( 1.+0.5*-math.log(af) ))
            # (still needs a af=max(af,machine_epsilon, or a test.)
        else:
            # but the below is easier to tweak :)

            if digits==None:
                if af==0.:        digits=0
                elif af<.00001:   digits=7
                elif af<.0001:    digits=6
                elif af<.001:     digits=5
                elif af<.01:      digits=4
                elif af<.1:       digits=3
                elif af<.5:       digits=3
                elif af<7:        digits=2
                elif af<100:      digits=1
                elif af<1000:     digits=0
                else: digits=0    # higher? show as integer

        digits += extradigits
        digits=max(0,digits) # negative extradigits can make that happen

        ret = ('%% .%df'%digits)%f

        if removetrail:
            #print "Removing trail from %r"%ret
            # remove trailing zeroes, and a dot if it's there afterwards.
            if '.' in ret:
                while ret.endswith('0'):
                #    print "Removing a zero"
                    ret=ret[:-1]
            if ret.endswith('.'):
                ret=ret[:-1]
            #print "Ended up with %r"%ret
        
    if 1:
        if aligndigit:
            if 'e' in ret:
                epos = ret.rindex('e')
                pos_after_e = len(ret)-epos-2
                aligndigit-=1
                if pos_after_e<aligndigit:
                    ret+=' '*(aligndigit-pos_after_e) 
            elif '.' in ret:
                aligndigit+=1 # cheat for off by 1
                dpos = ret.rindex('.')
                pos_after_dot = len(ret)-dpos
                #print 'positions after dot:',pos_after_dot
                aligndigit-=1
                if pos_after_dot<aligndigit:
                    ret+=' '*(aligndigit-pos_after_dot) 
            else:
                aligndigit+=1 # cheat for off by 1
                i=len(ret)-1
                while ret[i]==' ':
                    i-=1               
                final_spaces = len(ret)-i
                #print 'final spaces:',final_spaces
                if final_spaces<aligndigit:
                    ret+=' '*(aligndigit-final_spaces)
                
        if fixedwidth:
            ret = ('%% %ss'%fixedwidth)%ret
            
    return ret



def nsn(f, dig=2, chopdotzeroes=1, color=False):
    """ Prints a float with less-significant digits chopped off,
        both for small *and* large numbers.
        For example,
            nsn(.00000132894632, 2) == '1.3e-06'
            nsn(.00132894632, 2)    == '0.0013'
            nsn(1.32894632, 2)      == '1.3'
            nsn(13.2894632, 2)      == '13'
            nsn(132894632, 2)       == '130000000'
        Code needs cleanup.
        I suspect there is cleverer or at least more readable / less hacky code for this.
        May not always work well due to rounding errors.
    """
    sign=1
    if f<0:
        sign = -1
        f = abs(f)        

    m,e = frexp10(f)

    add=0
    if abs(f) < 1.0:
        add = 1
        
    roundto = -1-e+dig+add
    
    ret = str(  sign * round(f,roundto)  )
    if chopdotzeroes:
        ret=re.sub(r'[.]0+$','',ret)
        if ret.endswith('.0'):
            ret=ret[:-2]

    if color:
        try:
            import helpers_shellcolor as sc
            #ret = (
	    #  sc.white(ret[:-2])+
	    #  sc.gray(ret[-2:-1])+
            #  sc.darkgray(ret[-1:])	
            #)
        except ImportError:
            pass

    return ret
            


def _machine_epsilon(func=float):
    ret = func(1)
    while func(1)+func(ret) != func(1):
        ret_last = ret
        ret = func(ret) / func(2)
    return ret
    

def digits_for_range(npo, sigma=None):
    ''' sfloat by default scales a number according to the amount of digits in the mnumber itself.
        When printing a list of numbers from the same data, it can make sense to adjust that to the
        range of those values

        Takes a numpy array, python list, or such.

        TODO: clean up. A lot. Replace? Abandon?
    '''
    import numpy
    machine_epsilon = _machine_epsilon()
    if npo.dtype.kind in 'ui':
        return 0

    if numpy.amax( numpy.mod(npo,1) )< machine_epsilon:   # there may be a better moethod than mod
        return 0
        
    if sigma:
        mn  = numpy.mean(npo)
        std = dumpy.std(npo)
        mi = mn-sigma*std
        ma = mn+sigma*std
    else:
        mi  = numpy.amin(npo)
        ma  = numpy.amax(npo)

    if abs(mi)<machine_epsilon:
        dmi = 0         
    else:
        dmi = max(0,( 0.52*-math.log( abs(mi) ) ))
    if abs(ma)<machine_epsilon:
        dma = 0
    else:
        dma = max(0,( 0.52*-math.log( abs(ma) ) ))
    dr = max(0,( 0.52*-math.log( max(machine_epsilon,ma-mi) ) ))

    cd = min(dmi,dma)+2
    cd = round(cd)

    return cd



#for i in (0.00001,0.0001,0.001,0.01,0.1,0,1,10,100):
#    print
#    import numpy
#    print digits_for_range( ((numpy.random.wald(0.99,9,30)/10.)**4)/10. )
#    print digits_for_range( ((numpy.random.normal(0.,2.,10)/10.)**2) )



def frexp10(x):
    """ e.g.
          1.3E5           ~=  (1.3, 5) 
          1.32894632e-06) ~=  (0.13, -5)
    """
    import math
    try:
        exp = int(math.log10(x))
        return x / 10**float(exp), exp
    except (OverflowError,ValueError):
        return x,0
    except NameError: 
        print( "You forgot to import math" )
        raise
    except Exception as e: 
        print( x )
        raise           






## Date and time related

def shortish_dt(unixtime_or_datetime, strftime='%b %d %H:%M', omit_today=False):
    ''' Meant for recent dates - gives a datetime (or unix time)
        in the form "Mar 07 10:32".
        You might want "%b %d %H:%M" for "Mon Mar 07 10:32" instead.
    '''
    try:
        if type(unixtime_or_datetime) in (type(''),):
            unixtime_or_datetime = float(unixtime_or_datetime) # try to interpret as unixtime-as-string

        if type(unixtime_or_datetime) in (int,float):
            unixtime_or_datetime = datetime.datetime.fromtimestamp(unixtime_or_datetime)

        if omit_today and unixtime_or_datetime.date() == datetime.date.today():
            tt = strftime
            for dayrelevant in '%A %a %d %e %b %B'.split():
                tt = tt.replace(dayrelevant,'')
            tt = tt.strip()
            if len(tt)>0: # only if we didn't just remove everything (you had a date-only strftime argument)
                strftime = tt
        return unixtime_or_datetime.strftime(strftime)
    except:
        raise
        return ''

    
def nicetimedelta(td, parts=2, future='', joinon=', '):
    '''
        Takes a timedelta, or an int or float figure (of seconds),
        and presents a human-readable summary,
        using (by default) the largest two relevant time sizes.
        
        Examples:        
        nicetimedelta(239487)                           == " 2 days, 18 hours"
        nicetimedelta(datetime.timedelta(seconds=2394)) == "39 minutes, 54 seconds"
    '''
    if type(td) in (int, float):
        td = datetime.timedelta(seconds=td)
    
    minute_length = 60.
    hour_length   = 60.*minute_length
    day_length    = 24.*hour_length
    month_length  = 30.437*day_length
    year_length   = 365.25*day_length
    ret=[]
    sleft = td.total_seconds()

    if sleft<0:
        ret.append(future)
        sleft = abs(sleft)

    if sleft>year_length:
        amt_year = int(sleft/year_length)        
        sleft-=year_length*amt_year
        if amt_year==1:
            ret.append('%2d year '%amt_year)
        else:
            ret.append('%2d years'%amt_year)

    if sleft>month_length:
        amt_month = int(sleft/month_length)        
        sleft-=month_length*amt_month
        if amt_month==1:
            ret.append('%2d month '%amt_month)
        else:
            ret.append('%2d months'%amt_month)
        
    if sleft>day_length:
        amt_day = int(sleft/day_length)        
        sleft-=day_length*amt_day
        if amt_day==1:
            ret.append('%2d day '%amt_day)
        else:
            ret.append('%2d days'%amt_day)

    if sleft>hour_length:
        amt_hour = int(sleft/hour_length)
        sleft-=hour_length*amt_hour
        if amt_hour==1:
            ret.append('%2d hour '%amt_hour)
        else:
            ret.append('%2d hours'%amt_hour)

    if sleft>minute_length:
        amt_minute = int(sleft/minute_length)
        sleft-=minute_length*amt_minute
        if amt_minute==1:
            ret.append('%2d minute '%amt_minute)
        else:
            ret.append('%2d minutes'%amt_minute)

    ret.append('%2d seconds'%sleft)
    return joinon.join(ret[:parts])


def nicetimelength(sec, long=False, joinon=' ', parts=2, future=''):
    """ Takes a relative amount of time (seconds as float/int, or a timedelta)
        Returns a string describing that is human terms

         e.g. nicetimelength(767)        == '12min 47sec',
              nicetimelength(2615958475) == '82yr  11mo',
    """
    if type(sec) is datetime.timedelta:       
       sec = sec.days*86400 + sec.seconds

    vals = [
        #('century','centuries','cent', 60.*60.*24.*365.*100. ),
        ('year',   'years',    'yr',   60.*60.*24.*365.      ),
        ('month',  'months',   'mo',   60.*60.*24.*30.6      ),
        ('week',   'weeks',    'wk',   60.*60.*24.*7         ),
        ('day',    'days',     'dy',   60.*60.*24.           ),
        ('hour',   'hours',    'hr',   60.*60.               ),
        ('minute', 'minutes',  'min',  60.                   ),
        #('second', 'seconds',  'sec',  1.                    ),
    ]
    ret=[]
    left = sec

    if left<0:
        ret.append(future)
        left = abs(left)

    roundme=False
    if left>10:
        roundme=True
    for one,many,shorts,insec in vals:
        if left>insec:
            howmany = int(left/insec)
            left -= howmany*insec
            if long:
                if howmany==1:
                    ret.append( '1 %s'%(one) )
                else:
                    ret.append( '%d %s'%(howmany,many) )
            else: # short form
                ret.append('%2d%-3s'%(howmany,shorts))
    if left>=0.:
        if roundme:
            if long:
                ret.append( '%d seconds'%(left) )
            else:
                ret.append( '%dsec'%(left) )
        else:
            if long:
                ret.append( '%s seconds'%(sfloat(left,fixedwidth='')) )
            else:
                ret.append( '%ssec'%(sfloat(left,fixedwidth='', digits=2)) )
                        
    return joinon.join(ret[:parts])



def min_sec(sec,second_digits=1,left_pad=2):
    """ takes float value, represents as minutes, seconds e.g. 62.33242 -> '1m2.3s'
        secondDigits refers to the digits after the decimal point to print,
        left_pad to the left padding on the seconds (for things to line up). Examples:

        min_sec(1.3)     == '0m01.3s'
        min_sec(13)      == '0m13.0s'

        min_sec(5.3,0)   == '0m05s'
        min_sec(5.3,0,0) == '0m5s'
    """
    format_string = "%%dm%%0%d.%dfs"%(left_pad,second_digits)
    return format_string%(sec/60.,sec%60.)
        









## string kneading
    
def stringify_list(ls):
    """ string conversion of all elements in a list,
        e.g. stringify_list([1,'2',u'3'])  -> ['1', '2', u'3']

        Mostly a support function for some other things here.
    """    
    if type(ls) is list:
        return list('%s'%s  for s in ls)
    else: # tuple. Or something you shouldn't have handed in without specific expectation.
        return tuple('%s'%s  for s in ls)





def comma(ls, connector='and', serial=True, f=stringify_list):
    """ comma(['a', 'b']) -> 'a and b',
        comma(['a', 'b', 'c'], connector='or') -> 'a, b, or c'
        comma([1,2,3],'') -> '1, 2, 3'     (basically identical to ', '.join([1,2,3]))
        serial includes or excludes the serial comma (a.k.a. Oxford comma, Harvard comma). Default: include.

        if f!=None, it is a callable applied to the list first.
                    by default, this is used to ensure all elements are strings.
    """
    sc=''
    if serial:
        sc=','

    if f!=None:
        ls=f(ls)
    #handle different lengths
    if len(ls)<2: #case catches both empty string and one-element list. 
        return ''.join(ls)  #We like nice default behaviours.
    if len(ls)==2:
        return '%s %s %s'%(ls[0],connector,ls[1])
    else: #>2
        return '%s%s %s %s'%( ', '.join(ls[:-1]), sc, connector, ls[-1]  )

# unused?
#def surround(s, prepend='',append=''):
#    """ If (space-stripped) string is nonempty,
#        this prepends and appends something (to the original string).
#        for example, ('',          '(ISSN: ',')') -> ''   and
#                     ('1234-5678 ','(ISSN: ',')') -> '(ISSN: 1234-5678 )'
#    """
#    if len(s.strip())>0:
#        s='%s%s%s'%(prepend,s,append)
#        return s

                    
# unused?
#def bracket(s,pa='()'):
#    """ brackets a string if it.strip() is nonempty. """
#    if len(s.strip())>0:
#        s='%s%s%s'%(pa[0],s,pa[1])
#    return s







## Specific purpose

# filesystem related
def mode_minusstyle(mode):
    ''' takes a file mode bits (probably from stat),
        returns drwx------ style representation.
    '''
    ret=['-', '-','-','-', '-','-','-', '-','-','-']
    if mode&stat.S_IFREG: pass
    elif mode&stat.S_IFDIR: ret[0]='d'
    elif mode&stat.S_IFIFO: ret[0]='p'
    elif mode&stat.S_IFCHR: ret[0]='c'
    elif mode&stat.S_IFBLK: ret[0]='b'
    elif mode&stat.S_IFLNK: ret[0]='l'
    elif mode&stat.S_IFSOCK: ret[0]='s'
 
    if mode&stat.S_IRUSR: ret[1]='r'
    if mode&stat.S_IWUSR: ret[2]='w'
    if mode&stat.S_IXUSR: ret[3]='x'
    if mode&stat.S_IRGRP: ret[4]='r'
    if mode&stat.S_IWGRP: ret[5]='w'
    if mode&stat.S_IXGRP: ret[6]='x'
    if mode&stat.S_IROTH: ret[7]='r'
    if mode&stat.S_IWOTH: ret[8]='w'
    if mode&stat.S_IXOTH: ret[9]='x'

    if mode&stat.S_ISUID:
        if ret[3]=='x':
            ret[3]='s'
        else:
            ret[3]='S'
        
    if mode&stat.S_ISGID:
        if ret[6]=='x':
            ret[6]='s'
        else:
            ret[6]='S'

    if mode&stat.S_ISVTX:
        if ret[9]=='x':
            ret[9]='t'
        else:
            ret[9]='T'

    return ''.join(ret)




# cluster stuff
def summarize_nodelist(l, joinon=', ', uniq=True, sort=True):
    " If you have nodes called 'node1', 'node2', 'node3', 'node5' etc, this will summarize them like '1..3, 5' "
    l=sorted(l)

    n=[]
    o=[]
    for e in l:
        if e.startswith('node'):
            n.append( int(e[4:]) )
        else:
            o.append(e)
    if uniq:
        n=list(set(n))
    if sort:
        n=sorted(n)
    ret=[]
    st = n[0]
    en = st
    i=1
    while i<len(n):
        e=n[i]
        if e != n[i-1]+1:
            if st==en:
                ret.append('%s'%st)
            #elif st+1==en:
            #    ret.append('%s,%s'%(st,en))
            else:
                ret.append('%s..%s'%(st,en))
            st=n[i]
            en=st
        else:
            en=e
        i+=1
    if st==en:
        ret.append('%s'%st)
    else:
        ret.append('%s..%s'%(st,en))
    ret.extend(o)
    return joinon.join(ret)




if __name__=='__main__':
    testvals = (0,  .00000132894632,  .00132894632,  1.32894632,  13.2894632, 132894632)
    
    for v in testvals:
        print( 'frexp10( %-24s )     =  %r'%(v,frexp10(v)) )
    print

    for dig in (2,3,1):
        for v in testvals:
            print( 'nsn( %-25r,%2r )  =  %r'%(v,dig, nsn(v,dig)) )
        print




    examples = []
    for _ in range(2):
        examples.append( random.uniform(0.0000000001,0.00000005) )
    for _ in range(2):
        examples.append( random.uniform(0,0.0001) )
    for _ in range(2):
        examples.append( random.uniform(0,0.1) )
    for _ in range(2):
        examples.append( random.uniform(0,1) )
    for _ in range(3):
        examples.append( random.uniform(1,100) )
    for _ in range(2):
        examples.append( random.uniform(100,100000) )
    examples.append( random.uniform(100000,200000) )

    examples.sort()
    
    print
    for example in examples:
        print( 'sfloat( %17s ) -> %20r'%( example, sfloat(example) ) )
    print
    print




    for i in range(1,4):
        v = random.randint(1,i*300) + 0.01*random.randint(1,i*3000)
        print( "%13s seconds is %s"%(v,nicetimelength(v)) )
    for i in range(1,6):
        v = random.randint(1,i*3000)+random.randint(1,i*3000000000)
        print( "%13s seconds is %s"%(v,nicetimelength(v)) )




def tablify(d, omit_table_element=False):
    '''
       Takes a tuple/list of tuples/lists,
       treats them as rows of data to be printed as a HTML table.

       By default writes a complete table.
       omit_table_elements=True can make sense to add rows into an existing table.

       Example:
         print tablify( [['a','b','c'],
                         [ 4,  5,  0.00001 ]] )
       Returns:
        <table>
         <tr>
          <td>a</td>
          <td>b</td>
          <td>c</td>
         </tr>
         <tr>
          <td>4</td>
          <td>5</td>
          <td>6</td>
         </tr>
        </table>
    '''
    ret=[]
    def f(o): # treat floats nicely
        #if type(o)==float:
        #    return ('%.4f'%o).rstrip('0')
        #else:
            return cgi.escape(str(o))
    if not omit_table_element:
        ret.append('<table>\n')    
    for r in d:
        ret.append('<tr>')

        if type(r) in (tuple,list):
            ret.extend('\n <td>%s</td>'%f(i)  for i in r )
        else:
            ret.append('\n <td>%s</td>'%f(r))
            
        ret.append('\n</tr>')
            
    if not omit_table_element:
        ret.append('\n</table>')
    return ''.join(ret)


    
        

