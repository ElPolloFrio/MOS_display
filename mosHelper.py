import string, os, logging
import datetime as dt

# A series of helper functions for working with mos stuff

def getDirNames():
    # Hard-code the relative paths only once, then call this function
    # elsewhere.
    dictDirNames = {}
    
    # All the files and subfolders live here
    # LMK's laptop
    dictDirNames['home'] = 'C:\\Users\\LMK\\Documents\\MOS_display'
    # X:\ testing
    #dictDirNames['home'] = 'X:\\9-Applications\\Content\\MosGraphics'
    # Fileserver scheduled task
    #dictDirNames['home'] = 'D:\\Common$\\9-Applications\\Content\\MosGraphics'

    # Directory for output images
    dictDirNames['img'] = 'images'

    # Directory for raw files downloaded from MDL
    dictDirNames['raw'] = 'raw_files'

    # Directory for processed files for individual stations
    dictDirNames['proc'] = 'processed_files'

    # Directory for log files
    dictDirNames['logs'] = 'logs'
    
    return dictDirNames


def listRawFiles(mostype):
    # mostype is a 3-letter abbreviation
    mostype = mostype.lower()

    # Raw files have the following form:
    # nnn-YYYY-MM-DD-CCz.txt
    # nnn = 3-letter model abbreviation (mex, met, mav), lowercase
    # YYYY = year
    # MM = month
    # DD = day
    # CC = cycle (00, 06, 12, 18)
    # z is constant and refers to the UTC timezone, lowercase

    dictDirNames = getDirNames()
    contents = os.listdir(dictDirNames['raw'])
    rawfiles = []

    for item in contents:
        if (item.startswith(mostype)) & (item.endswith('z.txt')):
            rawfiles.append(item)

    return rawfiles


def listProcFilesByStation(staname):
    # staname is a 4-alphanumeric abbreviation (e.g., KSTL, K3LF, NSTU)
    #
    # For a given station, this function will list which processed
    # files are available.

    staname = staname.upper()

    # Processed files have the following form:
    # NNN-SSSS-YYYYMMDD_CC
    # NNN = 3-letter model abbreviation (MET, MAV, MEX, etc.), uppercase
    # SSSS = 3-alphanumeric station abbreviation (3LF, STL, UIN, etc.)
    # YYYY = 4 digit year
    # MM = 2 digit month
    # DD = 2 digit day
    # CC = 2 digit cycle time (00, 06, 12, 18)

    dictDirNames = getDirNames()
    contents = os.listdir(dictDirNames['proc'])
    
    procFiles = []

    for item in contents:
        if (staname in item):
            procFiles.append(item)

    return procFiles


def getLatestFilename(mostype, staname):
    # mostype is a 3-letter abbreviation
    # staname is a 4-alphanumeric abbreviation (KSTL, K3LF, TIST, etc.)
    #
    # For a given station and MOS type, this function returns the filename
    # of the most recent processed file.

    # Processed files have the following form:
    # NNN-SSSS-YYYYMMDD_CC
    # NNN = 3-letter model abbreviation (MET, MAV, MEX, etc.), uppercase
    # SSSS = 4-alphanumeric station abbreviation (3LF, STL, UIN, etc.)
    # YYYY = 4 digit year
    # MM = 2 digit month
    # DD = 2 digit day
    # CC = 2 digit cycle time (00, 06, 12, 18)
    
    mostype = mostype.upper()
    staname = staname.upper()
    prefix = '%s-%s' % (mostype, staname)

    dictDirNames = getDirNames()
    contents = os.listdir(dictDirNames['proc'])

    procFiles = []

    for item in contents:
        if item.startswith(prefix):
            procFiles.append(item)

    # Since the filenames include YYYYMMDD_CC, the last item in the list is
    # the most recent file.
    return procFiles[-1]


def load_file(filename):
    # Load a text file for processing.
    # Returns the file contents as a really big string.
    #
    # 'filename' is a complete filename, including the extension
    fileobj = open(filename, mode = 'rt')
    data = fileobj.read()
    fileobj.close()
    return data


def parseStations(stalist, data):
    # 'stalist' is a list of station identifiers for which to create processed files
    # 'data' is a really big string as returned by load_file.
    # output filename has this form:
    # NNN-SSSS-YYYYMMDD_CC
    # NNN = 3 letter model abbreviation
    # SSSS = 4 alphanumeric station identifier
    # YYYYMMDD = date
    # CC = cycle

    dictDirNames = getDirNames()
    
    modelNames = {'ECMX':'ECE', 'ECM':'ECS', 'NAM':'MET', 'GFSX':'MEX', 'GFS':'MAV'}
    indivStations = data.split('                                                                     \n')
    for item in indivStations:
        try:
            lines = item.split('\n')
            header = lines[0].split()
            staname = header[0]
            mostype = header[1]
            rundate = header[4].split('/')
            runtime = header[5]
            # preserve (or insert) leading zeros for month and day
            #fileDate = ('%s%02d%02d' % (rundate[2], int(rundate[0]), int(rundate[1])))
            #fileTime = runtime[0:2]
            #filename = ('%s-%s-%s_%s' % (modelNames[mostype], staname, fileDate, fileTime))
            dictFn = makeFilenames(modelNames[mostype], staname, rundate[2], rundate[0], rundate[1], runtime[0:2])
            filename = dictFn['proc']
            if staname in stalist:
                #print 'Saving', filename
                fullname = os.path.join(dictDirNames['proc'], filename)
                fileobj = open(fullname, 'w')
                fileobj.writelines(item)
                fileobj.close()
        except:
            #don't care about lines that are just newlines
            # On reflection, this may not be an entirely kosher use of try/except. Read up on this.
            pass


def setStations():
    # In retrospect, it would make more sense to keep a master list of stations with such
    # useful columns as CWA and state. Then these lists could be constructed from a
    # master list instead of being built laboriously by hand. Actually they'd be dictionaries. And
    # it would make the mapping steps easier, too.
    stalist = {}
    stalist['LSX'] = ['K3LF', 'KALN', 'KBLV', 'KCOU', 'KCPS', 'KENL', 'KFAM', 'KJEF', 'KPPQ', 'KSAR', 'KSET', 'KSLO', 'KSTL', 'KSUS', 'KUIN']
    stalist['SGF'] = ['KAIZ', 'KJLN', 'KSGF', 'KTBN', 'KUNO', 'KVIH']
    stalist['EAX'] = ['KCDJ', 'KDMO', 'KIRK', 'KIXD', 'KLXT', 'KMCI', 'KMKC', 'KOJC', 'KSTJ', 'KSZL']
    stalist['EAX_lite'] = ['KCDJ', 'KIRK', 'KIXD', 'KMCI', 'KSTJ', 'KSZL']
    stalist['ILX'] = ['K1H2', 'KAAA', 'KAJG', 'KBMI', 'KCMI', 'KDEC', 'KDNV', 'KFOA', 'KGBG', 'KIJX', 'KLWV', 'KMTO', 'KOLY', 'KPIA', 'KPRG', 'KRSV', 'KSPI', 'KTAZ', 'KTIP']
    stalist['ILX_lite'] = ['K1H2', 'KBMI', 'KCMI', 'KFOA', 'KIJX', 'KPIA', 'KSPI', 'KTAZ']
    stalist['PAH'] = ['KCIR', 'KCGI', 'KCUL', 'KEHR', 'KEVV', 'KFWC', 'KHOP', 'KHSB', 'KM30', 'KMDH', 'KMVN', 'KMWA', 'KOWB', 'KPAH', 'KPOF']
    stalist['LOT'] = ['KARR', 'KC09', 'KDKB', 'KDPA', 'KGYY', 'KIGQ', 'KIKK', 'KJOT', 'KLOT', 'KMDW', 'KORD', 'KPNT', 'KPWK', 'KRFD', 'KRPJ', 'KUGN', 'KVPZ', 'KVYS']
    stalist['DVN'] = ['KAWG', 'KBRL', 'KC75', 'KCID', 'KCWI', 'KDBQ', 'KDVN', 'KEOK', 'KFEP', 'KFFL', 'KFSW', 'KIIB', 'KIOW', 'KMLI', 'KMPZ', 'KMQB', 'KMUT', 'KMXO', 'KSFY', 'KSQI', 'KVTI']
    stalist['DMX'] = ['KADU', 'KAIO', 'KALO', 'KAMW', 'KAXA', 'KBNW', 'KCAV', 'KCIN', 'KCNC', 'KCSQ', 'KDNS', 'KDSM', 'KEBS', 'KEST', 'KFOD', 'KIKV', 'KLWD', 'KMCW', 'KMIW', 'KOTM', 'KOXV', 'KPEA', 'KTNU']
    stalist['MPX'] = ['KACQ', 'KAEL', 'KANE', 'KAQP', 'KAXN', 'KBBB', 'KCBG', 'KCFE', 'KDXX', 'KEAU', 'KFBL', 'KFCM', 'KFRM', 'KFSE', 'KGDB', 'KGHW', 'KGYL', 'KHCD', 'KJMR', 'KJYG', 'KLJF', 'KLUM', 'KLVN', 'KLXL', 'KMGG', 'KMIC', 'KMKT', 'KMOX', 'KMSP', 'KMVE', 'KOEO', 'KOVL', 'KOWA', 'KPNM', 'KRCX', 'KRGK', 'KRNH', 'KROS', 'KRPD', 'KRWF', 'KSGS', 'KSTC', 'KSTP', 'KSYN', 'KULM']

    stalist['HNL'] = ['PHHI', 'PHIK', 'PHJH', 'PHJR', 'PHKO', 'PHLI', 'PHMK', 'PHNG', 'PHNL', 'PHNY', 'PHOG', 'PHSF', 'PHTO']
    stalist['HUN'] = ['KHSV', 'KMSL', 'KDCU', 'KMDQ', 'K4A9']        
        
    stalist['SJU'] = ['TJBQ', 'TJMZ', 'TJNR', 'TJPS', 'TJSJ']
    stalist['Caribbean'] = ['TIST', 'TISX', 'TKPK', 'TNCM', 'MUGM']
    stalist['Pacific'] = ['PMDY', 'NSTU']

    stalist['TEST'] = ['PHNL', 'NSTU', 'KORD', 'PAJN', 'PABR', 'TIST', 'TJMZ', 'KGSH', 'KOUN', 'KONT']

    return(stalist)


def transformFilename(fn):
    # Given a filename of either processed or raw form, return a
    # dictionary containing the mostype, staname, year, month, day,
    # and cycle. fn is a string.
    #
    # Raw files have this form:
    # nnn-YYYY-MM-DD-CCz.txt
    # nnn = 3-letter model abbreviation (mex, met, mav), lowercase
    # YYYY = year
    # MM = month
    # DD = day
    # CC = cycle (00, 06, 12, 18)
    # z is constant and refers to the UTC timezone, lowercase
    #
    # processed files have this form:
    # NNN-SSSS-YYYYMMDD_CC
    # NNN = 3 letter model abbreviation
    # SSSS = 4 alphanumeric station identifier
    # YYYYMMDD = date
    # CC = cycle

    # Note that if an improperly formatted string is passed to this
    # function, the errors won't be caught and it will probably end
    # up in the 'else' part of the if-else flow. Probably need to add some
    # regex checking up here to be sure that the argument fits the pattern
    # of either a raw file or a processed file. Or at least a length check.

    dictParms = {}

    if fn.endswith('z.txt'):
        # raw file
        dictParms['mostype'] = fn[0:3]
        # staname is not defined for raw files
        dictParms['staname'] = ''
        dictParms['year'] = fn[4:8]
        dictParms['month'] = fn[9:11]
        dictParms['day'] = fn[12:14]
        dictParms['cycle'] = fn[15:17]
    else: 
        # processed file
        dictParms['mostype'] = fn[0:3]
        dictParms['staname'] = fn[4:8]
        dictParms['year'] = fn[9:13]
        dictParms['month'] = fn[13:15]
        dictParms['day'] = fn[15:17]
        dictParms['cycle'] = fn[18:20]

    filenames = makeFilenames(dictParms['mostype'], dictParms['staname'], dictParms['year'], dictParms['month'], dictParms['day'], dictParms['cycle'])
    if fn.endswith('z.txt'):
        # original file was a raw file. No station name was given. This is
        # here as a placeholder for future development work.
        pass
    else:
        # original file was a processed file. Construct its parent raw file name.
        dictParms['raw'] = filenames['raw']

    return dictParms


def makeFilenames(mostype, staname, year, month, day, cycle):
    # Construct filenames for raw files and processed files
    # based on the mostype, station name, year, month, day, and cycle.
    #
    # Raw files have this form:
    # nnn-YYYY-MM-DD-CCz.txt
    # nnn = 3-letter model abbreviation (mex, met, mav), lowercase
    # YYYY = year
    # MM = month
    # DD = day
    # CC = cycle (00, 06, 12, 18)
    # z is constant and refers to the UTC timezone, lowercase
    #
    # processed files have this form:
    # NNN-SSSS-YYYYMMDD_CC
    # NNN = 3 letter model abbreviation
    # SSSS = 4 alphanumeric station identifier
    # YYYYMMDD = date
    # CC = cycle

    dictFn = {}
    # preserve (or insert) leading zeros for month and day
    dictFn['proc'] = ('%s-%s-%s%02d%02d_%s' % (mostype.upper(), staname.upper(), year, int(month), int(day), cycle))
    dictFn['raw'] = ('%s-%s-%02d-%02d-%02dz.txt' % (mostype.lower(), year, int(month), int(day), int(cycle)))

    return dictFn


def processFromSavedFiles(mostype, staname, forceReprocess = 'False'):
    # mostype is a 3-letter abbreviation
    # staname is a 4-alphanumeric abbrevation (KSTL, K3LF, TIST, etc.)
    #
    # For a given station and MOS type, find [some of|all of} the appropriate raw
    # files on disk and process them to create individual station files.
    #
    # This function may be called with either 2 or 3 arguments. If it is called
    # with 2 arguments (mostype, staname), then it will check to see which
    # processed files already exist and skip those. If it is called with
    # 3 arguments (mostype, staname, 'True'), then it will force reprocessing
    # and (re)create individual station files for all of the appropriate raw
    # files which are found on disk. Use this option if there was an error in
    # processing the raw files and it is necessary to re-process them all.

    mostype = mostype.lower()
    staname = staname.upper()

    rawfiles = set(listRawFiles(mostype))
    dictDirNames = getDirNames()

    # Start with a list of all processed files found
    # for that station. For each processed filename,
    # create the filename of its parent raw file. Then
    # check the set of raw files to see if it's there. If
    # it is, remove it. That leaves only the raw files
    # for which a processed file does not yet exist. Another
    # way to do it would be to build a set of raw files from
    # the list of processed files, then use the set.difference
    # method.
    procfilelist = listProcFilesByStation(staname)
    for item in procfilelist:
        if forceReprocess:
            pass
        else:
            parentfile = transformFilename(item)['raw']
            rawfiles.discard(parentfile)

    rawfilelist = list(rawfiles)
    if (len(rawfilelist) > 0):
        for f in rawfilelist:
            fullname = os.path.join(dictDirNames['raw'], f)
            d = load_file(fullname)
            parseStations(staname, d)

    # original
    #rawfiles = listRawFiles(mostype)
    #dictDirNames = getDirNames()
    #for f in rawfilelist:
    #    fullname = os.path.join(dictDirNames['raw'], f)
    #    d = load_file(fullname)
    #    parseStations(staname, d)


def setUpTheLogger():
    # someone set up us the logger?
    #
    # Even though logging does slow down the scripts, it's worth the
    # time penalty because a log facilitates troubleshooting, especially
    # if something breaks when I'm not on shift.
    
    # Define a unique log file suffix based on the date/time and
    # output each log to a logs directory.
    dictDirNames = getDirNames()
    rightnow = dt.datetime.now()
    filename = 'mosgraphics_%s.log' % rightnow.strftime('%Y%m%d-%H%M%S')
    log_filename = os.path.join(dictDirNames['logs'], filename)
    
    # Create the logger object
    logger = logging.getLogger('mosgraphics')
    logger.setLevel(logging.INFO)
    
    # Create a file handler to log messages to a text file
    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.INFO)
    
    # Create a console handler with the same alert level as the file handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Create a formatter and add it to the handlers
    logformatter = logging.Formatter('%(asctime)s - %(name)-22s - %(levelname)s - %(message)s')
    fh.setFormatter(logformatter)
    ch.setFormatter(logformatter)
    
    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    # Log some headers
    logger.info('-------------------------------------------')
    logger.info('----------starting a new run---------------')
    logger.info('-------------------------------------------')
    
    return logger
