import os


#def safe_new_filename(filename, **kwargs):
#     '''
#         A combination of filesystemsafe() and newfilename().
#         See their docstrings for the parameters.
#         
#         This is the no-thinky function I'm often looking for for things like downloaders.
#     '''
#     safer = filesystemsafe(filename, **kwargs)
#     safer_new = unique(safer, **kwargs)
#     return safer_new

def filesystemsafe(filename, mode='loose', truncbytelen=250, spacemode='_'):
    ''' Takes a string to be used as a filename,

        Returns a variant that is probably safe and sane to use on the filesystem.
      
        May well truncate things, to try to avoid the common 255-byte-per-filename max length

        Does not guarantee it's safe in that you won't overwrite something;
           (for that, you may want to combine with unique())

        Mode can be:
        - 'loose': Removes:
                     /
                     \
                     NUL
                     invalid UTF8 (will mangle codepage stuff)
                     whitespace other than spaces
                     escapes (to avoid console muck)
                     and most non-printable characters
        - 'loose_nospace': like loose, but also remove spaces
         
        - 'base64': the filesystem-safe variant that uses [A-Za-z0-9-_] (the URL variant)
           Reversible if short enough and you know about those two substitutions.
           Keep in mind that you may run into max-filename-length errors
           (often 255 chars, meaning )
        - 'base32': safe for case-insensitive filesystems. Longer than the original
        TODO:
        - 'strict': removes most characters that aren't [A-Za-z0-9 ._-]
           Less sensible for non-western-european text.


        spacemode can be:
        - False: no special treamtment
        - a string: replace spaces with these.  "_" or perhaps "." can be sensible.
    '''
    if mode in ('loose', 'loose_nospace'):
        import helpers_unicode
        filename = filename.replace('\x00','') # invalid almost everywhere.
        filename = filename.replace('/','')
        filename = filename.replace('\\','') # and can avoid some weird escape interpretation
        filename = filename.decode('utf8','ignore')
        filename = filename.encode('utf8')
        filename = helpers_unicode.remove_nonprintable(filename) # removes most unicode side effects (except things like rtl?)
        # Thhe range-for-escapes thing is probably redundant now:
        if mode=='loose':
            for i in range(1,0x20): # assume NUL is gone already
                filename = filename.replace( chr(i), '') # escapes are a bad idea. Not only \x1b is dangerous with ANSI
                
        filename = filename.replace('\n','')
        filename = filename.replace('\r','')
        filename = filename.strip()  # whitespace at edges can confuse some programs
        
    elif mode=='base64':
        import base64
        filename = base64.b64encode(s).rstrip('=')
        filename = filename.replace('+','-')
        filename = filename.replace('/','_')

    elif mode=='base32':
        import base64
        filename = base64.b32encode(filename).rstrip('=')
        
    else:
        raise ValueError('mode %r not implemented'%mode)
    
    return filename
    



def unique(filename, add_pattern='_zpn4', addatmostdigits=2, casemode='ignore', verbose=False):
    ''' "give me a filename _like_ this, but one that does not exist yet."

        For example, if you ask for 'test.txt' a few times, you might get
        '/path/test.txt', '/path/test_0001.txt', '/path/test_0002.txt', etc.

        Keep in mind that with a lot of files in a directory, this is never efficient,
        and this code will race with other instances of this code.
 
        If you want more scalability, either do the split-to-directories thing, 
          or easier, determine a good pattern once and stick with it, or use randomness (e.g. UUIDs).
        If you have many workers on shared storage, that means thinking up front.
           (Also that you're probably doing it wrong in that you should be using a database smarter than a filesystem)

        Notes:
        - Uses an absolute path for things to avoid some weird behaviour
        
        add_pattern can be
        - 'bracketcount', like how Windows does it.
             If there's a File.jpg, make File (1).jpg, etc.
             Implies a listdir, which can sometimes be slow.
        - '_zpn3' or with other number: adds something like '_004',
             before the extension (if present)
             The final number in this spec is the amount of digits to pad with.
             It is suggested you use >=4. While it will continue with more digits when
               necessary, it will only do so if that adds at most two (by default) digits,
               because when you have a series like _1.txt and _2.txt, you may want
               _2_0001.txt rather than 0003.txt since that can be confusing in some situations.
               To avoid that, hand a large number into addatmostdigits
             Implies a listdir, which can sometimes be slow.
        - 'random': adds a random character.
             avoids a listdir, since it assumes it usually leads to a unique filename.

        casemode can be: (TODO: implement this)
        - "strict": for interaction with windows, which can get confused and make mistakes
                    when it seems filenames which mathch if case-insensitive.

        - "ignore": we don't care. Usually good enough for *nix.
        
    '''
    def _fn_frombits(dirname, basename, ext=None):
        ''' Specific-case helper used by unique '''
        if ext==None:
            return os.path.join(dirname, basename)
        else:
            return os.path.join(dirname, '%s.%s'%(basename,ext))
    
    if not os.path.isabs(filename):
        filename = os.path.abspath(filename)
        
    while os.path.exists(filename):
        parts = fn_parts(filename)
        dirname   = parts['dir']
        #basename  = parts['base']
        noext = parts['noext']
        ext       = parts['ext']
        if verbose:
            print( "filename %r exists, varying with %r"%(filename, add_pattern) )

        #if add_pattern=='bracketcount':# should only happen once, since we figure out something unique now. 
        #    similar = glob.glob('%s/%s*'%(dirname,basename)) #TODO: need special case for when ext!=None?
        #    # filter with re like '%s\([0-9]+\)' ?
            
        if add_pattern=='random':
            import random
            noext+=random.choice('abcdefghijklmnopqrstuvwxyz')

        elif add_pattern.startswith('_zpn'): # will leave the while to loop until we find one.
            digits = int(add_pattern[4:])
            ibo = 1
            if '_' in noext:
                bb,bo = noext.rsplit('_',1)
                try:
                    # could test more, e.g. whether there is no text in bo
                    if len(bb)<digits-addatmostdigits:
                        raise ValueError('Looks like an original series numbering we may not want to continue')
                    ibo = int(bo)                    
                    ibo+=1
                    noext=bb
                    
                except: # underscore present, but it was for something else. Add our own
                    ibo=1
            noext = ('%%s_%%0%dd'%digits)%(noext,ibo)
            # when we need more digits than asked for, this will simply no longer be padded (or lexically sortable)
            
        else:
            raise ValueError("Don't know that way of generating an alternate filename")

        filename = _fn_frombits(dirname, noext, ext)
    if verbose:
        print( "Done, chose %r"%filename )
    return filename
    



def fn_parts(pathstr):
    """ For a given path, returns a dict with
        dirname, basename, basename without extension, extension

        for extensions, we split only on the last dot.
 
        For example: 
'/q/a.b/base.xml' --> {'ext': 'xml',  'base': 'base.xml',  'noext': 'base',  'dir': '/q/a.b',  fullpathnoext: '/q/a.b/base'}
           'aa.b' --> {'ext': 'b',    'base': 'aa.b',      'noext': 'aa',    'dir': '',        fullpathnoext: 'aa'}
           'bare' --> {'ext': None,   'base': 'bare',      'noext': 'bare',  'dir': '',        fullpathnoext: 'bare'}

         Note that 'ext':None  (it's most ly there to make fn_fromparts easier)
    """
    dirn   = os.path.dirname(pathstr)
    basen  = os.path.basename(pathstr)
    dotinbase = basen.rfind('.')
    if dotinbase==-1:
        noext=basen
        ext=None
    else:
        noext = basen[:dotinbase]
        ext   = basen[dotinbase+1:]
    return {'dir':dirn, 'base':basen , 'noext':noext , 'ext':ext, 'fullpathnoext':os.path.join(dirn,noext) }





def is_nonbinary(filename=None, data=None, amt=200):
    """ Given either a filename or some data from it,
        returns whether this is probably a text file or not.
        Cheap imitation of file magic.
        amt controls how much of data we use (or how much to read from the filename)

        Written for 'is this possibly a log' test, so specialcases compressed files because of log rotation.
    """
    if data==None:
        if filename==None:
            raise ValueError("You need to give either a filename or some of the file's content data")
        else:
            f=open(filename)
            data=f.read(amt)
            f.close()

    if data[:2]=='\x1f\x8b': # gzip magic
        #print( 'Ignoring, is Gzip' )
        return False

    elif data[:3]=='BZh':    # bzip2 magic.  There's also 'BZ0' for bzip1, but meh.
        #print( "Ignoring, is bzip2" )
        return False

    # list of ordinals
    ol = list(ord(ch) for ch in data[:amt])
    printable,nonprintable=0,0
    for o in ol:
        if o>=0x20 and o<0x7f:
            printable+=1
        else:
            nonprintable+=1

    if nonprintable==0: #only printable - this is text.
        return True

    else:
        # could be made slightly cleverer, but this is probably enough.
        printable_ratio = float(printable)/float(nonprintable+printable)
        if printable_ratio>0.95: # assume that's enough
            return True
        else:
            return False
    





def main():
    import random

    # mostly tests the filesystem-safe (and console-safe) thing
    for i in range(30):
        bs=''

        # completely random bytestring
        for bsl in range(130):
            bs += chr(random.randint(0,255))            
            
        #print
        #print( repr(bs) )
        #print( filesystemsafe(bs,'loose') )
        print( unique(filesystemsafe(bs,'loose')) )

        
if __name__=='__main__':
    main()
