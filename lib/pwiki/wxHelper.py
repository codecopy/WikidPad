from   wxPython.wx import wxNewId, wxSystemSettings_GetMetric, wxSYS_SCREEN_X, \
        wxSYS_SCREEN_Y

from wx.xrc import XRCCTRL, XRCID

class wxIdPool:
    def __init__(self):
        self.poolmap={}

    def __getattr__(self, name):
        """Returns a new wx-Id for each new string <name>.
 
        If the same name is given twice, the same id is returned.
        
        If the name is in the XRC id-table its value there will be returned
        """
        try:
            return XRCID(name)
        except:
            try:
                return self.poolmap[name]
            except KeyError:
                id=wxNewId()
                self.poolmap[name]=id
                return id


GUI_ID = wxIdPool()
GUI_ID.__doc__="All purpose standard Gui-Id-Pool"

 
class XrcControls:
    """
    Convenience wrapper for XRCCTRL
    """
    def __init__(self, basepanel):
        self.__basepanel = basepanel

    def __getattr__(self, name):
        return XRCCTRL(self.__basepanel, name)
        
    def __getitem__(self, name):
        return XRCCTRL(self.__basepanel, name)
    

def setWindowPos(win, pos=None, fullVisible=False):
    """
    Set position of a wxWindow, but ensure that the position is valid.
    If fullVisible is True, the window is moved to be full visible
    according to its current size. It is recommended to call
    setWindowSize first.
    """
    if pos is not None:
        currentX, currentY = pos
    else:
        currentX, currentY = win.GetPositionTuple()
        
    screenX = wxSystemSettings_GetMetric(wxSYS_SCREEN_X)
    screenY = wxSystemSettings_GetMetric(wxSYS_SCREEN_Y)
    
    # fix any crazy screen positions
    if currentX < 0:
        currentX = 10
    if currentY < 0:
        currentY = 10
    if currentX > screenX:
        currentX = screenX-100
    if currentY > screenY:
        currentY = screenY-100
        
    if fullVisible:
        sizeX, sizeY = win.GetSizeTuple()
        if currentX + sizeX > screenX:
            currentX = screenX - sizeX
        if currentY + sizeY > screenY:
            currentY = screenY - sizeY

    win.SetPosition((currentX, currentY))


def setWindowSize(win, size):
    """
    Set size of a wxWindow, but ensure that the size is valid
    """
    sizeX, sizeY = size
    screenX = wxSystemSettings_GetMetric(wxSYS_SCREEN_X)
    screenY = wxSystemSettings_GetMetric(wxSYS_SCREEN_Y)

    # don't let the window be > than the size of the screen
    if sizeX > screenX:
        sizeX = screenX-20
    if sizeY > screenY:
        currentY = screenY-20

    # set the size
    win.SetSize((sizeX, sizeY))


def getTextFromClipboard():
    """
    Retrieve text or unicode text from clipboard
    """
    from wxPython.wx import wxTheClipboard, wxDataObjectComposite, wxDataFormat, \
            wxCustomDataObject, wxDF_TEXT, wxDF_UNICODETEXT
    from StringOps import lineendToInternal, mbcsDec
    import array

    cb = wxTheClipboard
    cb.Open()
    try:
        dataob = wxDataObjectComposite()
        cdataob = wxCustomDataObject(wxDataFormat(wxDF_TEXT))
        udataob = wxCustomDataObject(wxDataFormat(wxDF_UNICODETEXT))
        cdataob.SetData("")
        udataob.SetData("")
        dataob.Add(udataob)
        dataob.Add(cdataob)

        if cb.GetData(dataob):
            if udataob.GetDataSize() > 0 and (udataob.GetDataSize() % 2) == 0:
                # We have unicode data
                # This might not work for all platforms:   # TODO Better impl.
                rawuni = udataob.GetData()
                arruni = array.array("u")
                arruni.fromstring(rawuni)
                realuni = lineendToInternal(arruni.tounicode())
                return realuni
            elif cdataob.GetDataSize() > 0:
                realuni = lineendToInternal(
                        mbcsDec(cdataob.GetData(), "replace")[0])
                return realuni
            else:
                return ""
    finally:
        cb.Close()


def copyTextToClipboard(text): 
    from wxPython.wx import wxTheClipboard, wxDataObjectComposite, wxDataFormat, \
            wxCustomDataObject, wxDF_TEXT, wxDF_UNICODETEXT
    from StringOps import lineendToOs, mbcsEnc
    import array

    cdataob = wxCustomDataObject(wxDataFormat(wxDF_TEXT))
    udataob = wxCustomDataObject(wxDataFormat(wxDF_UNICODETEXT))
    realuni = lineendToOs(text)
    arruni = array.array("u")
    arruni.fromunicode(realuni+u"\x00")
    rawuni = arruni.tostring()
    # print "Copy", repr(realuni), repr(rawuni), repr(mbcsenc(realuni)[0])
    udataob.SetData(rawuni)
    cdataob.SetData(mbcsEnc(realuni)[0]+"\x00")

    dataob = wxDataObjectComposite()
    dataob.Add(udataob)
    dataob.Add(cdataob)

    cb = wxTheClipboard
    cb.Open()
    try:
        cb.SetData(dataob)
    finally:
        cb.Close()


        