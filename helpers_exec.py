
import subprocess
import os


_whichcache = {}

def which(findcmd, raise_if_missing=True, cached=True):
    ''' wrapper around the unix "which" command, e.g.
          which( 'ls' ) == '/bin/ls'

        By default it caches the result,
        because we actually call which (subprocess sorta expensive)
            and most people don't actively shuffle their executables around
        so only the first call is a subprocess, and repeated calls are cheap

        (could consider imitating it, though it'd be hard to guarantee)
    '''
    if findcmd in _whichcache:
        #print "CACHEHIT %r -> %r"%( findcmd, _whichcache[findcmd]  )
        return _whichcache[findcmd]


    if not os.path.exists('/usr/bin/which'):
        raise OSError('Could not find which whch command to run')

    cmd = ['/usr/bin/which']
    cmd.append(findcmd)

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out,err = p.communicate()
    out = out.strip()
    if len(out)>0:
        ret = out
        _whichcache[findcmd] = ret
    else:
        if raise_if_missing:
            raise OSError('Could not find %r'%findcmd)
        else:
            ret = None
    return ret


def which_fallback(findcmds, raise_if_missing=True, cached=True):
    ''' like which(), but returns the first hit in a list of command names
          e.g. which_fallback( ['pigz','gzip'] )
    '''
    if type(findcmds) in (str,unicode):
        findcmds = [findcmds]

    for findcmd in findcmds:
        pathto = which(findcmd, raise_if_missing=False, cached=cached)
        if pathto:
            return pathto
    if raise_if_missing:
        raise OSError('Could not find %r'%findcmds)
    else:
        return None


def setproctitle(tostring=None):
    ''' If the setproctitle module is installed, uses it to set the process title,
        so that you can tell things apart in top/ps.
        You can hand in a specific string.
        Defaults to the script filename being run from.
    '''
    import sys
    try:
        import setproctitle
        if tostring==None:
            tostring = os.path.basename(sys.argv[0])
        setproctitle.setproctitle( tostring )
    except ImportError:
        pass



def num_gpus(fallback=None):
    import glob
    # TODO: more and better test cases, fallback style
    return len( glob.glob('/dev/nvidia?') )


def num_cpus(fallback=None):
    # I have a much better version somewhere.
    cprocs = 0
    try:
        f = open('/proc/cpuinfo')
        for line in f:
            if 'processor' in line:
                cprocs += 1
    except:
        raise
    finally:
        f.close()

    if cprocs==0:
        return fallback
    else:
        return cprocs


def jobsplit(l, numlists=1):
    ' Split one list into a given number of approximately equal-sized ones '
    # Yes, I know there's an itertools way. It's unreadable.
    ret = []
    for i in range(numlists):
        ret.append( list() )
    for i,elem in enumerate(l):
        ret[i%numlists].append(elem)
    return ret


if __name__ == '__main__':
    print 'CPUs:',num_cpus()
    print 'GPUs:',num_gpus()

    print jobsplit(range(17), 5)
