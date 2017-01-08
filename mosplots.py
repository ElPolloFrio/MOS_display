import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import datetime as dt
import matplotlib.dates as mpd
import string, re, os, logging, mosHelper

# written: Dec 2012 (LMK)
#
# Make pretty pictures of MOS plots to evaluate, at a glance, the run to run
# variation across several runs for X, N, P12, and any other elements I might
# define in the future. 

# Take as input: MOS type, station name, and model run date/time
# Keep a rolling archive of text files to create these graphics

def load_file(filename):
    # Load a text file of a single station for processing.
    # Returns the file contents as a list of strings (one line per string).
    #
    # 'filename' is a complete filename, including the extension
    fileobj = open(filename, mode = 'rt')
    data = fileobj.readlines()
    fileobj.close()
    return data 


def find_info(data):
    # Parse a single station's text file to find relevant information.
    # Returns a dictionary of station name, mos type, run date, and run time.
    #
    # 'data' is in the form returned by load_file.
    
    # toss newlines
    for x in range(0, len(data)):
        data[x] = data[x].replace('\n', '')
        
    # Parse the header line for station name, type of MOS, and model run.
    if 'MOS GUIDANCE' in data[1]:
        infoline = data[1] #MET, MAV, MEX
    else:
        infoline = data[0] #ECE and ECS (local files)
    #match words, treating 9/13/2013 as a word
    # This RE fails to handle 10/01/2013 correctly (splits as 10/01, 2013)
    #r = re.compile(r'\w[/]?[\w]+[/]?[\w]+')
    r = re.compile(r'\w+[/]?[\w]+[/]?[\w]+')
    info = r.findall(infoline)
    staname = info[0]
    mostype = info[1] + ' ' + info[2] + ' ' + info[3]
    rundate = info[4]
    runtime = info[5] + ' ' + info[6]
    dictInfo = {'STANAME':staname, 'MOSTYPE':mostype, 'RUNDATE':rundate, 'RUNTIME':runtime}
    return dictInfo


def thisrun_as_dt(info):
    # Create a datetime object representing the model run date/time.
    # Returns a datetime object.
    #
    # 'info' is a dictionary of the form returned by find_info.
    # info['RUNDATE'] must be of the form MM/DD/YYYY.
    # info['RUNTIME'] must be of the form HHMM UTC.

    rundate = info['RUNDATE']
    runtime = info['RUNTIME']
    M, D, Y = rundate.split('/')
    H = runtime[0:2]
    MM = runtime[2:4]
    thisrun = dt.datetime(int(Y), int(M), int(D), int(H), int(MM))
    return thisrun


def calc_dates(thisfile, info):
    # Given a type of MOS and its run date and run time, calculate the
    # dates (and associated filenames) needed to produce a complete graphic.
    # Returns two lists:
    #    prevruns, a list of datetime objects (including the current run)
    #    prevfiles, a list of filenames to access for a single station (including the current file)
    #
    # 'thisfile' is the filename of the file for which to calculate previous dates.
    # 'info' is a dictionary returned by find_info.
    
    mostype = info['MOSTYPE']
    thisrun = thisrun_as_dt(info)
    # start the list of previous runs/files with the first run/file to make looping easier later
    prevruns = [thisrun]
    # DO NOT initialize 'prevfiles' with 'thisfile', otherwise the first file will end up
    # listed twice because of the looping operation below
    prevfiles = []
    if 'ECMX' in mostype:
        # ECMX MOS GUIDANCE = ECE (AWIPS)
        # 00z runs for the previous 7 days (7 cycles)
        numhrs = [24, 48, 72, 96, 120, 144, 168]
    elif 'ECM' in mostype:
        # ECM MOS GUIDANCE = ECS (AWIPS)
        # 00z runs for the previous 2 days (2 cycles)
        numhrs = [24, 48]
    elif 'NAM' in mostype:
        # NAM MOS GUIDANCE = MET (AWIPS)
        # 12z and 00z runs going back 2-ish days (5 cycles)
        numhrs = [12, 24, 36, 48, 60]
    elif 'GFSX' in mostype:
        # GFSX MOS GUIDANCE = MEX (AWIPS)
        # 12z and 00z runs going back 7-ish days (15 cycles)
        numhrs = [12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 132, 144, 156, 168, 180]
    elif 'GFS' in mostype:
        # GFS MOS GUIDANCE = MAV (AWIPS)
        # 12z, 18z, 00z, 06z runs going back 2-ish days (12 cycles)
        numhrs = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]
    for hr in numhrs:
        wayback = dt.timedelta(hours = hr)
        prevruns.append(thisrun - wayback)
        
    dictParms = mosHelper.transformFilename(thisfile)
    for item in prevruns:
        #Note: change the line below if the file naming convention changes
        #prevfiles.append(thisfile[0:9] + item.strftime('%Y%m%d_%H'))
        # Use functions from mosHelper for consistency in case of filename convention changes.
        appendme = mosHelper.makeFilenames(dictParms['mostype'], dictParms['staname'], item.strftime('%Y'), item.strftime('%m'), item.strftime('%d'), item.strftime('%H'))['proc']
        prevfiles.append(appendme)
        
    return prevruns, prevfiles


def yoinkFromMOS(data, wxelement):
    # Pull out the fcst hr line, max/min or min/max line, PoP12 line, etc.
    #
    # Returns a horizontal numpy array (horiz numpy arrays will facilitate select-by-index
    # operations later).
    #
    # Note that the returned array includes the initial label ('X/N', 'P12', etc.) to facilitate
    # troubleshooting in other parts of the script, but only if that wxelement exists in the MOS. 
    #
    # 'data' is in the form returned by load_file. 'wxelement' is a string, as
    # defined below. To add support for a new element (e.g., wind), it must
    # be defined in this function, among other places.
    #
    # Defined elements:
    # 'FHR': forecast hour or equivalent
    # 'XN': max/min or min/max
    # 'P12': PoP12
    # 'WSP': wind speed

    dictWxElements = {'FHR': ['FHR', 'HR'],
                      'XN': ['X/N', 'N/X'],
                      'P12': ['P12'],
                      'WSP': ['WSP', 'WND']
                      }
    #dictWxElements['FHR'] = ['FHR', 'HR']
    #dictWxElements['XN'] = ['X/N', 'N/X']
    #dictWxElements['P12'] = ['P12']
    #dictWxElements['WSP'] = ['WSP', 'WND']

    # Check that wxelement has been defined before proceeding.
    # if wxelement not in dictWxElements.keys(), then fail gracefully
    # Still need to write this part. use try/except KeyError

    # some sites don't have the requested wxelement (e.g., NSTU has no
    # X/N, only temps. Don't worry about that here, it is handled in
    # makeDisplayArrays.
    elementLine = ''
    
    for x in range(0, len(data)):
        choices = dictWxElements[wxelement]
        for option in choices:
            if option in data[x]:
                elementLine = data[x]

    # toss pipes (can't replace with '' b/c of 144|156 hrs, for example)
    elementLine = elementLine.replace('|', ' ')

    # split on spaces in preparation for turning into a numpy array
    elementLine = elementLine.split(' ')

    # turn into numpy array
    arr_element = np.array(elementLine)

    # delete empty entries ('')
    delmeElement = [index for index in range(0, len(elementLine)) if elementLine[index] == '']
    arr_element = np.delete(arr_element, delmeElement)

    # For some stations, there is no climo entry (esp precip) and the last valid entry runs up
    # against the climo 999999 (e.g., 7999999 or 12999999 for a pop12 of 7 or 12).
    fixmeElement = [index for index in range(0, len(arr_element)) if len(arr_element[index]) > 3]
    for item in fixmeElement:
        arr_element[item] = arr_element[item][:-7] #-7 to account for the newline char

    # 999 means missing data, not 999 degrees. This happens often with TJMZ's minT. Turn
    # 999 into our representation of missing data, which is np.nan.
    arr_element = np.where(arr_element == '999', np.nan, arr_element)
    
    # Note: keep the leading entry ('P12', 'X/N', etc.) for future troubleshooting.
    # Note: if np.array(arr_element).size == 0, then the wxelement was not found in the MOS
    return np.array(arr_element)


def makeDisplayArrays(filename):
    # Given a filename of the expected form, figure out which previous
    # files are needed to construct complete arrays of all data needed
    # for the display of each configured fcst element. Load those files,
    # if they exist, and build the complete arrays. Then, construct display
    # arrays for each fcst element by selecting array elements from the complete
    # arrays based on mostype and model run date/time.
    # Returns the following:
    #   dispArr, a dictionary of display arrays with keys 'X', 'N', 'P12'
    #   dtXaxis, a dictionary with datetime objects to be used for creating x-axis labels
    #   infoDict, a dictionary returned by find_info (needed to construct the title and axes annotations)
    #   prevruns, a list of datetime objects (including the current run)
    #
    # 'filename' is a complete filename, including the extension, suitable for passing to load_file.
    # 'filename' should not include the file path b/c that is added during this function.

    dictDirNames = mosHelper.getDirNames()
    fullname = os.path.join(dictDirNames['proc'], filename)
    d = load_file(fullname)
    infoDict = find_info(d)
    prevruns, prevfiles = calc_dates(filename, infoDict)
    #allf = []
    allxn = []
    allp12 = []
    allwsp = []
    for fn in prevfiles:
        try:
            fullname2 = os.path.join(dictDirNames['proc'], fn)
            dd = load_file(fullname2)
            #fhr = yoinkFromMOS(dd, 'FHR')
            xn = yoinkFromMOS(dd, 'XN')
            p12 = yoinkFromMOS(dd, 'P12')
            wsp = yoinkFromMOS(dd, 'WSP')
            # As a side note, fhr, xn, p12 will have length 0 if the
            # wxelement was not found in MOS. This matters later.
            #allf.append(fhr)
            allxn.append(xn)
            allp12.append(p12)
            allwsp.append(wsp)
        except:
            # If the file does not exist, use empty np arrays as placeholders
            # On reflection, this may not be an entirely kosher use of try/except. Read up on this.
            #allf.append(np.array([]))
            allxn.append(np.array([]))
            allp12.append(np.array([]))
            allwsp.append(np.array([]))

    # At this point, if the wxelement was not found in that MOS type (e.g., NSTU has no
    # X/N line in the MAV), then allElem will be an array whose elements each have size 0.
    # This matters because we don't want to try constructing a display array with no data.
    # Handle this case by checking to see which elements are present and only constructing
    # display arrays for those ones. Note that a different situation is a site where
    # all entries for a given element are 999 (missing), such as TJMZ's minT, and this is not
    # handled here (the plot will be created and it will be empty).

    # These variables are used below to construct display arrays for the given wxelements and data
    wxelements = []
    alldata = {}

    # find a way to consolidate these loops to avoid repetition
    count = 0
    for item in allxn:
        if len(item) == 0:
            count = count + 1
    if count < len(allxn):
        wxelements.append('X')
        alldata['X'] = allxn
        wxelements.append('N')
        alldata['N'] = allxn
        
    count = 0
    for item in allp12:
        if len(item) == 0:
            count = count + 1
    if count < len(allp12):
        wxelements.append('P12')
        alldata['P12'] = allp12

    count = 0
    for item in allwsp:
        if len(item) == 0:
            count = count + 1
    if count < len(allwsp):
        wxelements.append('WSP')
        alldata['WSP'] = allwsp

    # Make life easy by using keys that are constructed from information returned by find_info.
    modelKey = infoDict['MOSTYPE'] + ' ' + infoDict['RUNTIME']

    # display array size: [row, col]
    # start, stop, step, and jump are indices:
    # start = index for the first element of the first row
    # stop = index for the last element of the first row (may be +/-1 because of Python slicing)
    # step = count by this many to go from start to stop (e.g, 0 to 14 by 2 means step = 2)
    # jump = count by this many to go from start to the first index of the next row (e.g., ECE X: first row begins with 0, next row begins with 2, therefore jump = 2)
    # These indices assume no leading 'X/N', which is OK because the leading label is dropped in the loops below.
    # firsthr = the first fcst of this element in the array is fcst at this many hours from the model cycle (e.g., ECE 00z X is 24, ECE 00z N is 36, MEX 12z X is 12 (even though the entry is blank), etc.)
    # xstep = number of hours to increment to generate x-axis labels
    #
    # For the MAV, jump has 2 values: what's needed to get to first index of the next line and
    # what's needed to get to the first index of the line after that. MAV is special because
    # successive lines sometimes need the same index.
    #
    # MET, MEX 00z -> first fcst is X of that date
    #   off-cycle (00z) N plot is the same as the previous (12z) cycle's N plus a special first line
    # MET, MEX 12z -> first fcst is N of that night (next date in Z)
    #   off-cycle (12z) X plot is the same as the previous (00z) cycle's X plus a special first line
    # MAV 00z, 06z -> first fcst is X of that date
    # MAV 12z, 18z -> first fcst is N of that date (next date in Z)
    #
    # Handle off-cycle X/N plots as follows:
    # display array size is [1,#] where # is the correct number of columns.
    # start = index of the first non-nan entry of that first special line
    # stop = index of the last element of that first special line (+/-1 for Python slicing)
    # step = count by this many to go from start to stop for that first special line
    # jump = nan
    
    dictSize = { # ~ahem~
        'ECMX MOS GUIDANCE 0000 UTC':{ #ECE 00z
            'X':{'size':[8,8], 'start':0, 'stop':15, 'step':2, 'jump':2, 'firsthr':24, 'xstep': 24},
            'N':{'size':[7,7], 'start':1, 'stop':14, 'step':2, 'jump':2, 'firsthr':36, 'xstep': 24},
            'P12':{'size':[8,15], 'start':0, 'stop':15, 'step':1, 'jump':2, 'firsthr':24, 'xstep': 12}
            }, 
        'ECM MOS GUIDANCE 0000 UTC':{ #ECS 00z
            'X':{'size':[3,3], 'start':0, 'stop':5, 'step':2, 'jump':2, 'firsthr':24, 'xstep': 24},
            'N':{'size':[1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'P12':{'size':[3,5], 'start':0, 'stop':5, 'step':1, 'jump':2, 'firsthr':24, 'xstep': 12}
            },
        'GFS MOS GUIDANCE 0000 UTC':{ #MAV 00z
            'X':{'size':[9,3], 'start':0, 'stop':5, 'step':2, 'jump':[1,0], 'firsthr':24, 'xstep': 24},
            'N':{'size':[1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'P12':{'size':[9,5], 'start':0, 'stop':5, 'step':1, 'jump':[1,0], 'firsthr':24, 'xstep': 12},
            'WSP':{'size':[10,19], 'start':0, 'stop':19, 'step':1, 'jump':2, 'firsthr':6, 'xstep': 3}
            },
        'GFS MOS GUIDANCE 0600 UTC':{ #MAV 06z
            'X':{'size':[10,3], 'start':0, 'stop':5, 'step':2, 'jump':[0,1], 'firsthr':18, 'xstep': 24},
            'N':{'size': [1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':6, 'xstep': 24},
            'P12':{'size':[10,5], 'start':0, 'stop':5, 'step':1, 'jump':[0,1], 'firsthr':18, 'xstep': 12},
            'WSP':{'size':[10,19], 'start':0, 'stop':19, 'step':1, 'jump':2, 'firsthr':6, 'xstep': 3}
            },
        'GFS MOS GUIDANCE 1200 UTC':{ #MAV 12z
            'X':{'size':[1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'N':{'size':[9,3], 'start':0, 'stop':5, 'step':2, 'jump':[1,0], 'firsthr':24, 'xstep': 24},
            'P12':{'size':[9,5], 'start':0, 'stop':5, 'step':1, 'jump':[1,0], 'firsthr':24, 'xstep': 12},
            'WSP':{'size':[10,19], 'start':0, 'stop':19, 'step':1, 'jump':2, 'firsthr':6, 'xstep': 3}
            },
        'GFS MOS GUIDANCE 1800 UTC':{ #MAV 18z
            'X':{'size':[1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':6, 'xstep': 24},
            'N':{'size':[10,3], 'start':0, 'stop':5, 'step':2, 'jump':[0,1], 'firsthr':18, 'xstep': 24},
            'P12':{'size':[10,5], 'start':0, 'stop':5, 'step':1, 'jump':[0,1], 'firsthr':18, 'xstep': 12},
            'WSP':{'size':[10,19], 'start':0, 'stop':19, 'step':1, 'jump':2, 'firsthr':6, 'xstep': 3}
            },
        'NAM MOS GUIDANCE 0000 UTC':{ #MET 00z
            'X':{'size':[5,3], 'start':0, 'stop':5, 'step':2, 'jump':1, 'firsthr':24, 'xstep': 24},
            'N':{'size':[1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'P12':{'size':[5,5], 'start':0, 'stop':5, 'step':1, 'jump':1, 'firsthr':24, 'xstep': 12},
            'WSP':{'size':[5,19], 'start':0, 'stop':19, 'step':1, 'jump':4, 'firsthr':6, 'xstep': 3}
            },
        'NAM MOS GUIDANCE 1200 UTC':{ #MET 12z
            'X':{'size':[1,3], 'start':1, 'stop':4, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'N':{'size':[5,3], 'start':0, 'stop':5, 'step':2, 'jump':1, 'firsthr':24, 'xstep': 24},
            'P12':{'size':[5,5], 'start':0, 'stop':5, 'step':1, 'jump':1, 'firsthr':24, 'xstep': 12},
            'WSP':{'size':[5,19], 'start':0, 'stop':19, 'step':1, 'jump':4, 'firsthr':6, 'xstep': 3}
            },
        'GFSX MOS GUIDANCE 0000 UTC':{ #MEX 00z
            'X':{'size':[15,8], 'start':0, 'stop':15, 'step':2, 'jump':1, 'firsthr':24, 'xstep': 24},
            'N':{'size':[1,8], 'start':1, 'stop':14, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'P12':{'size':[15,15], 'start':0, 'stop':15, 'step':1, 'jump':1, 'firsthr':24, 'xstep': 12},
            'WSP':{'size':[15,15], 'start':0, 'stop':15, 'step':1, 'jump':1, 'firsthr':24, 'xstep': 12}
            },
        'GFSX MOS GUIDANCE 1200 UTC':{ #MEX 12z
            'X':{'size':[1,8], 'start':1, 'stop':14, 'step':2, 'jump':np.nan, 'firsthr':12, 'xstep': 24},
            'N':{'size':[15,8], 'start':0, 'stop':15, 'step':2, 'jump':1, 'firsthr':24, 'xstep': 24},
            'P12':{'size':[15,15], 'start':0, 'stop':15, 'step':1, 'jump':1, 'firsthr':24, 'xstep': 12},
            'WSP':{'size':[15,15], 'start':0, 'stop':15, 'step':1, 'jump':1, 'firsthr':24, 'xstep': 12}
            }
        }

    dispArr = {} #init it here, add to it later in the loop below
    dtXaxis = {} #ditto
    
    # Recall that wxelements and alldata were defined above to handle missing cases.
    
    for wx in wxelements:
        if dictSize[modelKey][wx]['size'][0] == 1:
            # Handle the special case of an off-cycle X or N.
            #
            # As usual, it turns out that this is more complicated than it looks at first.
            # PITA cases: ECS 00z N, MAV 06z N, MAV 18z X. Here's what happens:
            # 00z ECS N -> look back at the previous run (00z prev day) to get the size of
            # the array. Since the 00z prev day has the same dictSize entry as 00z current run,
            # it also has size [1,#]. The array is too short.
            # 06z MAV N -> look back 6 hrs to the 00z run's N. The size of that array is also [1,#]. The
            # array is too short.
            # 18z MAV X -> look back 6 hours to the 12z run's X. Same thing happens.
            # The solution is to first check dictSize[modelKey][wx]['size'][0] == 1. If so,
            # enter a bounded loop (a while loop will cause an infinite loop for the ECS) limited
            # to the number of columns given by dictSize[modelKey][wx]['size'][1] since there can't be more
            # special leading lines than cols. Within that loop, calculate prevKey and append it to a
            # storage list. Break the loop once dictSize[modelKey][wx]['size'][0] != 1. Now we have a list,
            # possibly of length 1, containing a list of prevKeys for which to calculate special lines. In
            # fact, go ahead and calculate the speciallines within the loop and append to another storage
            # list. Once the loop ends, the value of prevKey is the key to use to construct the bulk of
            # the array. At least, that's the hope.
            thisrun = thisrun_as_dt(infoDict)
            storePrevKeys = []
            storeSpecialLines = []
            origKey = modelKey #save for later to restore, otherwise can't do more than 1 graph at a time
            for c in range(dictSize[origKey][wx]['size'][1]):
                if dictSize[modelKey][wx]['size'][0] == 1:
                    if 'ECM' in infoDict['MOSTYPE']:
                        backtrack = 24 #ECS
                    elif ('GFS' in infoDict['MOSTYPE'] and 'GFSX' not in infoDict['MOSTYPE']):
                        backtrack = 6 #MAV
                    else:
                        backtrack = 12 #MEX, MET
                    prevrun = thisrun - dt.timedelta(hours = backtrack)
                    prevRUNTIME = prevrun.strftime('%H%M UTC')
                    prevKey = '%s %s' % (infoDict['MOSTYPE'], prevRUNTIME)
                    storePrevKeys.append(prevKey)
                    firstline = alldata[wx][c][1:] #toss leading 'X/N', 'P12', etc.
                    inds = np.arange(1, dictSize[modelKey][wx]['stop'], dictSize[modelKey][wx]['step'])
                    specialline = np.insert(firstline[inds], [0], np.nan)
                    storeSpecialLines.append(specialline)
                    thisrun = prevrun #on the next iteration, go back farther
                    modelKey = prevKey #on the next iteration, go back farther
                else:
                    break
            # 'varResult' is X, N, P12, etc. to return. 'varData' is the working array (allxn, allp12, etc.)
            varResult = np.empty(dictSize[modelKey][wx]['size']) * np.nan
            # toss the first line(s) from allxn since it's associated with origKey, not prevKey
            varData = alldata[wx][c:][:]
            
        else:
            origKey = modelKey
            varResult = np.empty(dictSize[modelKey][wx]['size']) * np.nan
            varData = alldata[wx]
            
        # Secure in the knowledge that an off-cycle case has been handled (if it exists),
        # proceed with creating the display array. Note that if it is an off-cycle case,
        # the array created below is for the previous cycle, and the special line(s) will be added
        # back in afterwards.
        flag = 0
        jumpindex = dictSize[modelKey][wx]['start']
        for row in range(0, len(varResult)):
            validline = varData[row][1:] #toss leading 'X/N' or 'N/X'
            inds = np.arange(jumpindex, dictSize[modelKey][wx]['stop'], dictSize[modelKey][wx]['step'])
            if validline != []:
                varResult[row, 0:len(inds)] = validline[inds]
            # dictSize[modelKey][wx]['jump'] is a single number unless MOSTYPE is the MAV.
            # For the MAV, need to alternate between the two jump indices.
            if (np.size(dictSize[modelKey][wx]['jump']) > 1) and (flag == 0):
                jumpindex = jumpindex + dictSize[modelKey][wx]['jump'][0]
                flag = 1
            elif flag == 1:
                jumpindex = jumpindex + dictSize[modelKey][wx]['jump'][1]
                flag = 0
            else:
                jumpindex = jumpindex + dictSize[modelKey][wx]['jump']

        # Create the fcst valid date/time entries for the x-axis labels.
        # The x-axis labels increase differently depending on the wx element
        # and the MOS type. 
        thisrun = thisrun_as_dt(infoDict)
        tempdt = []
        #if wx in ['P12', 'WSP']:
        #    fcsthrs = range(dictSize[origKey][wx]['firsthr'], 216, 12)
        #else:
        #    fcsthrs = range(dictSize[origKey][wx]['firsthr'], 216, 24)
        fcsthrs = range(dictSize[origKey][wx]['firsthr'], 216, dictSize[origKey][wx]['xstep'])
        for hr in fcsthrs:
            future = dt.timedelta(hours = hr)
            tempdt.append(thisrun + future)
        dtXaxis[wx] = tempdt

        # For off-cycle plots, add the special line back in.
        if dictSize[origKey][wx]['size'][0] == 1:
            # insert the special line(s) defined above
            storeSpecialLines.reverse()
            for c in range(0, len(storeSpecialLines)):
                varResult = np.insert(varResult, [0], storeSpecialLines[c], axis = 0)
            # Guess what. ECS N plot fails miserably because of the chosen data structure (size
            # [1,#] and the off-cycle run is itself). Out of 10 test cases x 3 plots each =
            # 30 plots, only 1 doesn't work. Sigh. Get around this by explicitly defining
            # each element of varResult for ECS N, which is a 3x3 array.
            if 'ECM' in origKey:
                varResult = np.array([
                    [np.nan, alldata[wx][0][2], alldata[wx][0][4]],
                    [alldata[wx][1][2], alldata[wx][1][4], np.nan],
                    [alldata[wx][2][5], np.nan, np.nan]
                    ], dtype = 'f')
            # ...and all is as it was, for the next value of wx in the loop
            varData = alldata[wx]
            modelKey = origKey
        
        dispArr[wx] = varResult
            
    return dispArr, dtXaxis, infoDict, prevruns


def makePlots(displayArrays, dtXaxis, info, prevRuns):
    # Step 3: Profit. Make the plots and save them as files.
    # Returns nothing (except profit).
    #
    # 'displayArrays' is a dictionary of arrays returned by makeDisplayArrays
    # 'dtXaxis' is a dictionary of datetime objects, returned by makeDisplayArrays, from which to create x-axis labels
    # 'info' is a dictionary of information returned by find_info
    # 'prevRuns' is a list of datetime objects (including the current run)

    # Grab a reference to the existing logger.
    # This only works if the script calling this function has
    # already called mosHelper.setUpTheLogger().
    module_logger = logging.getLogger('mosgraphics.makePlots')

    for wx in displayArrays.keys():
        if wx == 'P12':
            # Pop12 spans from 0 to 100. No matter what values are actually present,
            # always use the same color curve for displaying those values.
            
            # Define a special color curve for PoP12. RGB values:
            BrBu = np.array([
                [191, 129, 45],
                [223, 194, 125],
                [246, 232, 195],
                [255, 255, 217],
                [237, 248, 177],
                [199, 233, 180],
                [127, 205, 187],
                [65, 182, 196],
                [29, 145, 192],
                [34, 94, 168],
                [37, 52, 148],
                [129, 15, 124]
                ])
            # the color tuples must be normalized from 0 to 1
            BrBu = BrBu.astype(float) / 255
            tempR = [] #will be a list of tuples
            tempG = [] #ditto
            tempB = [] #ditto
            for a in np.arange(0, len(BrBu)):
                #breakpoint values must range from 0 to 1, inclusive
                breakpoint = a.astype(float)/(len(BrBu)-1)
                tempR.append((breakpoint, BrBu[a][0], BrBu[a][0]))
                tempG.append((breakpoint, BrBu[a][1], BrBu[a][1]))
                tempB.append((breakpoint, BrBu[a][2], BrBu[a][2]))
            cdict = {
                'red': tuple(tempR),
                'green': tuple(tempG),
                'blue': tuple(tempB)
                }
            p12map = mcolors.LinearSegmentedColormap('some_map', cdict, 256)
            cmap = p12map
            vmin = 0
            vmax = 100
            figsize = (14,10)
            cbarticks = np.arange(0, 110, 10)
        elif ((wx == 'X') or (wx == 'N')):
            # For MaxT and MinT, let matplotlib autoscale based on the values in the data.
            # That way, it's easy to see hot/cold trends at a glance.
            cmap = plt.cm.RdYlBu_r
            vmin = np.nanmin(displayArrays[wx])
            vmax = np.nanmax(displayArrays[wx])
            figsize = (7,10)
            # For large temp ranges, the color bar scale can get pretty crowded. For small
            # temp ranges, the default algorithm creates decimal degrees which aren't
            # meaningful. To address this, declare that if the range is big (20 degrees),
            # only show ticks every 5 degrees and be clever about picking the upper
            # and lower bounds. Otherwise, show ticks every 2 degrees, and massage vmax/vmin
            # to prevent the upper and lower bounds from being left off.
            #if (abs(vmax - vmin) >= 20):
            #    cbarstep = 5
            #else:
            #    cbarstep = 2
            #vmin = vmin - (vmin % cbarstep)
            #vmax = vmax + cbarstep - (vmax % cbarstep)
            #cbarticks = np.arange(vmin, vmax + cbarstep, cbarstep)
            
            # On second thought, let's just do it every 5 degrees no matter what. This will
            # help address the problem of large color differences between numerically similar
            # values, especially when abs(vmax - vmin) is small.
            cbarstep = 5
            vmin = vmin - (vmin % cbarstep)
            vmax = vmax + cbarstep - (vmax % cbarstep)
            cbarticks = np.arange(vmin, vmax + cbarstep, cbarstep)
                
            #if vmin % 2 == 1:
            #    vmin = vmin + 1
            #if vmax % 2 == 1:
            #    vmax = vmax - 1   
            #cbarticks = np.arange(vmin, vmax+1, cbarstep)
            
        elif wx == 'WSP':

            cbarstep = 10
            vmin = 0
            vmax = 30
            
            # Create a new colormap based on a subset of an existing colormap. Thanks,
            # StackOverflow!
            cmap = plt.get_cmap('YlOrBr')
            minval = 0.0
            maxval = 0.8
            n = 100
            new_cmap = mcolors.LinearSegmentedColormap.from_list('trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a = minval, b = maxval), cmap(np.linspace(minval, maxval, n)))

            # Set the "over" color so it stands out like a beacon
            new_cmap.set_over('blueviolet')
            
            cmap = new_cmap

            figsize = (14,10)
            cbarticks = np.arange(vmin, vmax + cbarstep, cbarstep)
            
        else:
            # good luck
            cmap = plt.cm.Blues
            vmin = np.nanmin(displayArrays[wx])
            vmax = np.nanmax(displayArrays[wx])
            figsize = (7,10)
            cbarticks = np.arange(vmin, vmax, 5)
        
        plotthis = displayArrays[wx]
        fig = plt.figure(figsize = figsize)
        ax = fig.add_subplot(1,1,1)
        im = ax.imshow(plotthis, origin = 'upper', interpolation = 'nearest', cmap = cmap, vmin = vmin, vmax = vmax)

        # Getting the figures to look right is a balance between figsize,
        # rcParams font size, and the font size of the text labels in the boxes.
        # If the figure size is too small, the x-axis labels overlap severely. If
        # the font size of the x-axis labels is too small, the figure is hard to read.

        # Plot the numbers centered in the boxes
        for r in np.arange(0, len(plotthis)):
            for c in np.arange(0, len(plotthis[0])):
                if not(np.isnan(plotthis[r,c])):
                    plt.text(c, r, int(plotthis[r,c]), fontsize = 20, horizontalalignment = 'center', verticalalignment = 'center')

        # Add a descriptive title
        wxnames = {'X':'MaxT', 'N':'MinT', 'P12':'PoP12', 'WSP': 'WindSpd'}
        strTitle = info['STANAME'] + ' ' + info['MOSTYPE'] + '\n' + info['RUNDATE'] + ' ' + info['RUNTIME'] + ' ' + wxnames[wx]
        plt.title(strTitle)

        # y-axis settings: previous model runs date/time
        yticks = np.arange(0, len(plotthis))
        ylabels = []
        for item in prevRuns:
            ylabels.append(item.strftime('%m/%d %HZ'))
        ax.set_yticks(yticks)
        ax.set_yticklabels(ylabels)
        ax.set_ylabel('Model cycle')

        # x-axis settings: fcst valid date/time
        xticks = np.arange(0, len(plotthis[0]))
        ax.set_xticks(xticks)
        xlabels = []
        for item in dtXaxis[wx]:
            xlabels.append(item.strftime('%a\n%m/%d\n%HZ'))
        ax.set_xticklabels(xlabels)
        ax.set_xlabel('Fcst valid date/time')

        # use AxesGrid1 toolkit to explicitly create an axes for the colorbar so tight_layout will work
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(plt.gca())
        #cax = divider.append_axes('right', '5%', pad = '3%')
        # use a constant size and padding (units are inches) for a uniform look among plots
        cax = divider.append_axes('right', size = 0.25, pad = 0.2)
        cbar = plt.colorbar(im, cax = cax, ticks = cbarticks)

        plt.rcParams['font.size'] = 12
        plt.tight_layout()

        # A good file name for daily use (overwriting) should include station, MOS type, and weather element.
        mosname = info['MOSTYPE'].split(' ')[0] # GFSX -> MEX, NAM -> MET, GFS -> MAV
        imgfilename = '%s_%s_%s.png' % (info['STANAME'], mosname, wxnames[wx])
        imgpath = os.path.join('images', imgfilename)
        plt.savefig(imgpath)
        module_logger.info('Saved %s', imgfilename)

        # Clean up the memory to avoid crashing during large loops
        plt.close(fig)
        
        
    #plt.show()

#################################
# test cases that pass with flying colors
#testfn = 'ECESTL20121207_00'
#testfn = 'METSTL20121211_00'
#testfn = 'METSTL20121204_12'
#testfn = 'MEXSTL20121208_00'
#testfn = 'MEXSTL20121212_12'
#testfn = 'MAVSTL20121210_06'
#testfn = 'MAVSTL20121210_00'
#testfn = 'MAVSTL20121203_12'
#testfn = 'MAVSTL20121203_18'
#testfn = 'ECSSTL20121204_00'

# this one has issues, don't know why yet
#testfn = 'MEXUIN20121227_12'

#fn = 'METCOU20130916_00'
#plotme, xdt, info, prev = makeDisplayArrays(fn)
#makePlots(plotme, xdt, info, prev)


    

