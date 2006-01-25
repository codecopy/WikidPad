## -*- coding: ISO-8859-1 -*-

"""
Various string operations, like unicode encoding/decoding,
creating diff information for plain byte sequences
"""



import threading

from struct import pack, unpack

import difflib, codecs
from codecs import BOM_UTF8, BOM_UTF16_BE, BOM_UTF16_LE
from os.path import splitext

import cStringIO as StringIO

from Utilities import DUMBTHREADHOLDER

import srePersistent as re

LINEEND_SPLIT_RE = re.compile(r"\r\n?|\n")


from Configuration import isUnicode, isOSX


# To generate dependencies for py2exe
import encodings.utf_8, encodings.latin_1



# ---------- Encoding conversion ----------


utf8Enc = codecs.getencoder("utf-8")
utf8Dec = codecs.getdecoder("utf-8")
utf8Reader = codecs.getreader("utf-8")
utf8Writer = codecs.getwriter("utf-8")

def convertLineEndings(text, newLe):
    """
    Convert line endings of text to string newLe which should be
    "\n", "\r" or "\r\n". If newLe or text is unicode, the result
    will be unicode, too.
    """
    return newLe.join(LINEEND_SPLIT_RE.split(text))

def lineendToInternal(text):
    return convertLineEndings(text, "\n")
    


if isOSX():      # TODO Linux
    # generate dependencies for py2app
    import encodings.mac_roman
    mbcsEnc = codecs.getencoder("mac_roman")
    mbcsDec = codecs.getdecoder("mac_roman")
    mbcsReader = codecs.getreader("mac_roman")
    mbcsWriter = codecs.getwriter("mac_roman")
    
    def lineendToOs(text):
        return convertLineEndings(text, "\r")
   
else:
    # generate dependencies for py2exe
    import encodings.mbcs
    mbcsEnc = codecs.getencoder("mbcs")
    mbcsDec = codecs.getdecoder("mbcs")
    mbcsReader = codecs.getreader("mbcs")
    mbcsWriter = codecs.getwriter("mbcs")

    # TODO This is suitable for Windows only
    def lineendToOs(text):
        return convertLineEndings(text, "\r\n")


if isUnicode():
    def uniToGui(text):
        """
        Convert unicode text to a format usable for wx GUI
        """
        return text   # Nothing to do
        
    def guiToUni(text):
        """
        Convert wx GUI string format to unicode
        """
        return text   # Nothing to do
else:
    def uniToGui(text):
        """
        Convert unicode text to a format usable for wx GUI
        """
        return mbcsEnc(text, "replace")[0]
        
    def guiToUni(text):
        """
        Convert unicode text to a format usable for wx GUI
        """
        return mbcsDec(text, "replace")[0]


def unicodeToCompFilename(us):
    """
    Encode a unicode filename to a filename compatible to (hopefully)
    any filesystem encoding by converting unicode to '=xx' for
    characters up to 255 and '$xxxx' above. Each 'x represents a hex
    character
    """
    result = []
    for c in us:
        if ord(c) > 255:
            result.append("$%04x" % ord(c))
            continue
        if c in u"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"+\
                u"{}[]()+-*_,.%":   # Allowed characters
            result.append(str(c))
            continue
        
        result.append("=%02x" % ord(c))
        
    return "".join(result)


def strToBool(s, default=False):
    """
    Try to interpret string (or unicode) s as
    boolean, return default if string can't be
    interpreted
    """
    
    if s is None:
        return default
    
    # Try to interpret as integer
    try:
        return int(s) != 0
    except ValueError:
        # Not an integer
        s = s.lower()
        if s in (u"true", u"yes"):
            return True
        if s in (u"false", u"no"):
            return False
            
        return default


# TODO More formats
def fileContentToUnicode(content):
    """
    Try to detect the text encoding of content
    and return converted unicode
    """
    if content.startswith(BOM_UTF8):
        return utf8Dec(content[len(BOM_UTF8):], "replace")[0]
    else:
        return mbcsDec(content, "replace")[0]
        
        
def wikiWordToLabel(word):
    """
    Strip '[' and ']' if non camelcase word and return it
    """
    if word.startswith(u"[") and word.endswith(u"]"):
        return word[1:-1]
    return word


def removeBracketsFilename(fn):
    n, ext = splitext(fn)
    return wikiWordToLabel(n) + ext


def revStr(s):
    """
    Return reversed string
    """
    s = list(s)
    s.reverse()
    return u"".join(s)
    
def splitkeep(s, delim):
    """
    Similar to split, but keeps the delimiter as separate element, e.g.
    splitkeep("aaabaaabaa", "b") -> ["aaa", "b", "aaa", "b", "aa"]
    """
    result = []
    for e in s.split(delim):
        result.append(e)
        result.append(delim)
        
    return result[:-1]


def matchWhole(reObj, s):
    """
    reObj -- Compiled regular expression
    s -- String to match
    
    Similar to reObj.match(s), but returns MatchObject only if the 
    whole string s is covered by the match, returns None otherwise
    """
    mat = reObj.match(s)
    if not mat:
        return None
    if mat.end(0) < len(s):
        return None
        
    return mat
    


## Copied from xml.sax.saxutils and modified to reduce dependencies
def escapeHtml(data):
    """
    Escape &, <, and > in a unicode string of data.
    """

    # must do ampersand first

    return data.replace(u"&", u"&amp;").replace(u">", u"&gt;").\
            replace(u"<", u"&lt;").replace(u"\n", u"<br />\n")


def unescapeRe(text):
    """
    Unescape things like \n\f. Throws exception if unescaping fails
    """
    return re.sub(u"", text, u"", 1)


def htmlColorToRgbTuple(html):
    """
    Calculate RGB integer tuple from html '#hhhhhh' format string.
    Returns None in case of an error
    """
    if len(html) != 7 or html[0] != "#":
        return None
    try:
        r = int(html[1:3], 16)
        g = int(html[3:5], 16)
        b = int(html[5:7], 16)
        return (r, g, b)
    except:
        return None
        
def rgbToHtmlColor(r, g, b):
    """
    Return HTML color '#hhhhhh' format string.
    """
    return "#%02X%02X%02X" % (r, g, b)
    


# ---------- Support for serializing values into binary data (and back) ----------
# Especially used in SearchAndReplace.py, class SearchReplaceOperation

class SerializeStream:
    def __init__(self, fileObj=None, stringBuf=None, readMode=True):
        """
        fileobj -- file-like object to wrap.
        readmode -- True; read from fileobj, False: write to fileobj
        """
        self.fileObj = fileObj 
        self.readMode = readMode

        if stringBuf is not None:
            if self.readMode:
                self.fileObj = StringIO.StringIO(stringBuf)
            else:
                self.fileObj = StringIO.StringIO()

    def isReadMode(self):
        """
        Returns True iff reading from fileObj, False iff writing to fileObj
        """
        return self.readMode
        
    def setBytesToRead(self, b):
        """
        Sets a string to read from via StringIO
        """
        self.fileObj = StringIO.StringIO(b)
        self.readMode = True

        
    def useBytesToWrite(self):
        """
        Sets the stream to write mode writing to a byte buffer (=string)
        via StringIO
        """
        self.fileObj = StringIO.StringIO()
        self.readMode = False

        
    def getBytes(self):
        """
        If fileObj is a StringIO object, call this to retrieve the stored
        string after write operations are finished, but before close() is
        called
        """
        return self.fileObj.getvalue()
        
    
    def writeBytes(self, b):
        self.fileObj.write(b)
        
    def readBytes(self, l):
        return self.fileObj.read(l)
        
    def serUint32(self, val):
        """
        Serialize 32bit unsigned integer val. This means: if stream is in read
        mode, val is ignored and the int read from stream is returned,
        if in write mode, val is written and returned
        """
        if self.isReadMode():
            return unpack(">I", self.readBytes(4))[0]   # Why big-endian? Why not? 
        else:
            self.writeBytes(pack(">I", val))
            return val


    def serInt32(self, val):
        """
        Serialize 32bit signed integer val. This means: if stream is in read
        mode, val is ignored and the int read from stream is returned,
        if in write mode, val is written and returned
        """
        if self.isReadMode():
            return unpack(">i", self.readBytes(4))[0]   # Why big-endian? Why not? 
        else:
            self.writeBytes(pack(">I", val))
            return val


    def serString(self, s):
        """
        Serialize string s, including length. This means: if stream is in read
        mode, s is ignored and the string read from stream is returned,
        if in write mode, s is written and returned
        """
        l = self.serUint32(len(s))

        if self.isReadMode():
            return self.readBytes(l)
        else:
            self.writeBytes(s)
            return s


    def serUniUtf8(self, us):
        """
        Serialize unicode string, encoded as UTF-8
        """
        if self.isReadMode():
            return utf8Dec(self.serString(""), "replace")[0]
        else:
            self.serString(utf8Enc(us)[0])
            return us


    def serBool(self, tv):
        """
        Serialize boolean truth value
        """
        if self.isReadMode():
            b = self.readBytes(1)
            return b != "\0"
        else:
            if tv:
                self.writeBytes("1")
            else:
                self.writeBytes("\0")
            
            return tv


    def close(self):
        """
        Close stream and underlying file object
        """
        self.fileObj.close()


def boolToChar(b):
    if b:
        return "1"
    else:
        return "\0"
        
def charToBool(c):
    return c != "\0"


def strToBin(s):
    """
    s -- String to convert to binary (NOT unicode!)
    """
    return pack(">I", len(s)) + s   # Why big-endian? Why not?
    
def binToStr(b):
    """
    Returns tuple (s, br) with string s and rest of the binary data br
    """
    l = unpack(">I", b[:4])[0]
    s = b[4 : 4+l]
    br = b[4+l : ]
    return (s, br)




# ---------- Breaking text into tokens ----------

class Token(object):
    __slots__ = ("__weakref__", "ttype", "start", "grpdict", "text", "node")
    
    def __init__(self, ttype, start, grpdict, text, node=None):
        self.ttype = ttype
        self.start = start
        self.grpdict = grpdict
        self.text = text
        self.node = node
        
    def __repr__(self):
        return u"Token(%s, %s, %s, <dict>, %s)" % (repr(self.ttype), repr(self.start), repr(self.text), repr(self.node))


class Tokenizer:
    def __init__(self, tokenre, defaultType):
        self.tokenre = tokenre
        self.defaultType = defaultType
        self.tokenThread = None

    def setTokenThread(self, tt):
        self.tokenThread = tt

    def getTokenThread(self):
        return self.tokenThread

    def tokenize(self, text, formatMap, defaultType, threadholder=DUMBTHREADHOLDER):
        textlen = len(text)
        result = []
        charpos = 0    
        
        while True:
            mat = self.tokenre.search(text, charpos)
            if mat is None:
                if charpos < textlen:
                    result.append(Token(defaultType, charpos, None,
                            text[charpos:textlen]))
                
                result.append(Token(defaultType, textlen, None, u""))
                break
    
            groupdict = mat.groupdict()
            for m in groupdict.keys():
                if not groupdict[m] is None and m.startswith(u"style"):
                    start, end = mat.span()
                    
                    # m is of the form:   style<index>
                    index = int(m[5:])
                    if charpos < start:
                        result.append(Token(defaultType, charpos, None,
                                text[charpos:start]))                    
                        charpos = start
    
                    result.append(Token(formatMap[index], charpos, groupdict,
                            text[start:end]))
                    charpos = end
                    break
    
            if not threadholder.isCurrent():
                break

        return result



# ---------- Handling diff information ----------


def difflibToCompact(ops, b):
    """
    Rewrite sequence of op_codes returned by difflib.SequenceMatcher.get_opcodes
    to the compact opcode format.

    0: replace,  1: delete,  2: insert

    b -- second string to match
    """
    result = []
    # ops.reverse()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        elif tag == "replace":
            result.append((0, i1, i2, b[j1:j2]))
        elif tag == "delete":
            result.append((1, i1, i2))
        elif tag == "insert":
            result.append((2, i1, b[j1:j2]))

    return result


def compactToBinCompact(cops):
    """
    Compress the ops to a compact binary format to store in the database
    as blob
    """
    result = []
    for op in cops:
        if op[0] == 0:
            result.append( pack("<Biii", 0, op[1], op[2], len(op[3])) )
            result.append(op[3])
        elif op[0] == 1:
            result.append( pack("<Bii", *op) )
        elif op[0] == 2:
            result.append( pack("<Bii", 2, op[1], len(op[2])) )
            result.append(op[2])

    return "".join(result)



def binCompactToCompact(bops):
    """
    Uncompress the ops from the binary format
    """
    pos = 0
    result = []
    while pos < len(bops):
        t = ord(bops[pos])
        pos += 1
        if t == 0:
            d = unpack("<iii", bops[pos:pos+12])
            pos += 12
            s = bops[pos:pos+d[2]]
            pos += d[2]
            
            result.append( (0, d[0], d[1], s) )
        elif t == 1:
            d = unpack("<ii", bops[pos:pos+8])
            pos += 8
            
            result.append( (1, d[0], d[1]) )
        elif t == 2:
            d = unpack("<ii", bops[pos:pos+8])
            pos += 8
            s = bops[pos:pos+d[1]]
            pos += d[1]
            
            result.append( (2, d[0], s) )

    return result            


def applyCompact(a, cops):
    """
    Apply compact ops to string a to create and return string b
    """
    result = []
    apos = 0
    for op in cops:
        if apos < op[1]:
            result.append(a[apos:op[1]])  # equal

        if op[0] == 0:
            result.append(op[3])
            apos = op[2]
        elif op[0] == 1:
            apos = op[2]
        elif op[0] == 2:
            result.append(op[2])
            apos = op[1]

    if apos < len(a):
        result.append(a[apos:])  # equal

    return "".join(result)


def applyBinCompact(a, bops):
    """
    Apply binary diff operations bops to a to create b
    """
    return applyCompact(a, binCompactToCompact(bops))


def getBinCompactForDiff(a, b):
    """
    Return the binary compact codes to change string a to b.
    For strings a and b (NOT unicode) it is true that
        applyBinCompact(a, getBinCompactForDiff(a, b)) == b
    """

    sm = difflib.SequenceMatcher(None, a, b)
    ops = sm.get_opcodes()
    return compactToBinCompact(difflibToCompact(ops, b))
