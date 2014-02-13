import datetime as dt
import os, logging, mosHelper

# Time to clean house and delete old raw files.

def clearProcFiles():
    # Grab a reference to the existing logger.
    # This only works if the script calling this function has
    # already called mosHelper.setUpTheLogger().
    module_logger = logging.getLogger('mosgraphics.clearProc')

    dictDirNames = mosHelper.getDirNames()
    contents = os.listdir(dictDirNames['proc'])

    module_logger.info('Deleting %s processed files', len(contents))
    for fn in contents:
        fullname = os.path.join(dictDirNames['proc'], fn)
        os.remove(fullname)


def cleanHouse():
    # Grab a reference to the existing logger.
    # This only works if the script calling this function has
    # already called mosHelper.setUpTheLogger().
    module_logger = logging.getLogger('mosgraphics.cleanHouse')

    dictDirNames = mosHelper.getDirNames()

    # Can probably rewrite mosplots.calc_dates based on the work here. Perhaps
    # in the ample free time with which all forecasters are blessed. Maybe use
    # xrange instead, also?
    #
    # Alright, here's the deal. The UTC date may be in the future compared to the
    # local date at times, so we'll toss in some negative numbers just to be sure the
    # early day runs (00z, 06z) won't get accidentally deleted.
    # Next, grab the current YYYY-MM-DD (local time) and use that as a starting point
    # from which to calculate which files to keep. Some of the filenames may not exist
    # yet, but that's OK. The important thing is that they won't be deleted. Yeah, that
    # makes total sense...
    hrsToKeep = {}
    hrsToKeep['MEX'] = [-24, -12, 0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 132, 144, 156, 168, 180, 192, 204, 216]
    hrsToKeep['MAV'] = [-24, -18, -12, -6, 0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]
    hrsToKeep['MET'] = [-36, -24, -12, 0, 12, 24, 36, 48, 60, 72, 84]
    #hrsToKeep['ECE'] = [-24, 0, 24, 48, 72, 96, 120, 144, 168, 192, 216]
    #hrsToKeep['ECS'] = [-24, 0, 24, 48, 72, 96]

    # Now. You're looking at now, sir. Everything that happens now, is happening now.
    # What happened to then?
    # We passed then.
    # When?
    # Just now. We're at now now.     
    rightnow = dt.datetime.now()

    # But not anymore! Choose 0 o'clock as a baseline. It makes the math easier.
    nowish = dt.datetime(year = rightnow.year, month = rightnow.month, day = rightnow.day, hour = 0)

    keyIter = hrsToKeep.iterkeys()

    # Loop over time to create filenames to keep
    for key in keyIter:
        keepfiles = []
        for hr in hrsToKeep[key]:
            mostype = key.lower()
            goback = dt.timedelta(hours = hr)
            prev = nowish - goback
            Y = prev.strftime('%Y')
            M = prev.strftime('%m')
            D = prev.strftime('%d')
            H = prev.strftime('%H')
            appendme = mosHelper.makeFilenames(mostype, 'ABCD', Y, M, D, H)['raw']
            keepfiles.append(appendme)
            
        keepfiles = set(keepfiles)
        
        # get the contents of the raw files directory for this mostype
        rawfiles = set(mosHelper.listRawFiles(mostype))
        
        # Suppose set1 = ([f1, f2, f3, etc.]) contains the filenames to keep, and
        # set2 = ([f0, f1, f2, f3, f4, f5, f6]) has the names of all raw files.
        # Then set2.difference(set1) is the set of files to delete.
        delme = rawfiles.difference(keepfiles)

        module_logger.info('%s are marked for deletion from %s', delme, mostype.upper())

        for fn in delme:
            fullname = os.path.join(dictDirNames['raw'], fn)
            os.remove(fullname)
