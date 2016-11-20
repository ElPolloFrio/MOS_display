import string, urllib2, re, os, logging, mosHelper

# written Sep 2013
# last updated: 23 Oct 2016
# Go get files from MDL and save them with meaningful filenames
# Meaningful filename convention: NNN-YYYY-MM-DD-CCz.txt
# NNN = 3 letter abbreviation (mex, met, mav)
# YYYY = year
# MM = month
# DD = day
# CC = cycle (00, 06, 12, 18)
# z is constant and refers to the UTC timezone
#
# Return a list of raw files that need to be processed.

def GrabEm():

    # Grab a reference to the existing logger.
    # This only works if the script calling this function has
    # already called mosHelper.setUpTheLogger().
    module_logger = logging.getLogger('mosgraphics.GrabEm')

    # MDL changed the folder structure for MET:
    # ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/nam/prod/nam_mos.YYYYMMDD/mdl_nammet.tXXz
    # YYYYMMDD = year/month/day in UTC
    # XX = cycle (00 or 12) in UTC
    # This folder also contains files named 'mdl_nammme.tXXz'.

    # MDL also changed the folder structure for MAV and MEX:
    # MAV:
    # ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfsmos.YYYYMMDD/mdl_gfsmav.tXXz
    # MEX:
    # ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfsmos.YYYYMMDD/mdl_gfsmex.tXXz
    # YYYYMMDD = year/month/day in UTC
    # XX = cycle (00, 06, 12, or 18 for the MAV, 00 or 12 for the MEX and MET) in UTC

    # There is also another source for MAV, MET, MEX, but the date and cycle are not present
    # in all filenames.
    # MAV:
    # http://www.nws.noaa.gov/mdl/forecast/text/avnmav.txt
    # MET:
    # http://www.nws.noaa.gov/mdl/forecast/text/nammet.txt
    # MEX:
    # http://www.nws.noaa.gov/mdl/forecast/text/mrfmex00.txt
    # http://www.nws.noaa.gov/mdl/forecast/text/mrfmex12.txt

    dictURLs = {'MAV': 'ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.mav',
                'MEX': 'ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.mex',
                'MET': 'ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/nam/prod/'
                }

    backupURLs = {'MAV': ['http://www.nws.noaa.gov/mdl/forecast/text/avnmav.txt'],
                  'MEX': ['http://www.nws.noaa.gov/mdl/forecast/text/mrfmex00.txt',
                          'http://www.nws.noaa.gov/mdl/forecast/text/mrfmex12.txt'
                          ],
                  'MET': ['http://www.nws.noaa.gov/mdl/forecast/text/nammet.txt']
                  }

    # File sizes in kb. Multiply by 1000 to get file size in bytes needed for os.path.getsize.
    dictFilesizeThresh = {'MAV': 250,
                          'MET': 1000,
                          'MEX': 1500
                          }

    dictDirNames = mosHelper.getDirNames()

    # Use this to keep track of which files were written and still need
    # to be processed with mosHelper.parseStations
    rawfiles = []

    try:
        for mosname in dictURLs:
            url = dictURLs[mosname]
            module_logger.info('Asking MDL for the %s', mosname)
            response = urllib2.urlopen(url)
            contents = response.read()
            response.close()

            # For MAV and MEX:
            # Each FTP directory contains at most 2 folders: RD.YYYYMMDD (RD.20130909),
            # although it used to contain a much longer archive.
            # Find the RD.######## section(s) of the string to get the folder names.
            #
            # For MET:
            # The FTP directory contains many folders, only two of which are of interest.
            # These folders are named 'nam_mos.YYYYMMDD', where YYYYMMDD is the UTC date
            # of the MOS run.
            if mosname is not 'MET':
                RD = re.compile(r'RD\.[0-9]+')
                folders = RD.findall(contents)
            else:
                RD = re.compile(r'nam_mos\.[0-9]+')
                folders = RD.findall(contents)
            module_logger.info('Found these folders: %s', folders)
            
            for item in folders:
                folderurl = '{}/{}/'.format(url, item)
                response = urllib2.urlopen(folderurl)
                contents = response.read()
                response.close()
                    
                # For MAV, MEX:
                # Each folder contains at most 4 files: cy.CC.txt (cy.00.txt, etc.)
                # Find the cy.##.txt section(s) of the string to get the filenames.
                #
                # For MET:
                # Each of those folders contains up to 4 files, only two of which are of
                # interest attm: 'mdl_nammet.tXXz', where XX is either '00' or '12'.
                if mosname is not 'MET':
                    CY = re.compile(r'cy\.[0-9]+\.txt')
                else:
                    CY = re.compile(r'mdl_nammet\.t[0-9][0-9]z')
                mosfiles = CY.findall(contents)
                module_logger.info('%s has these files: %s', item, mosfiles)

                for fname in mosfiles:
                    # Write to a local file with a meaningful name. ABCD is a placeholder b/c staname is
                    # undefined for raw files in mosHelper.makeFilenames.

                    if mosname is not 'MET':
                        yr = item[3:7]
                        mon = item[7:9]
                        dy = item[9:11]
                        cycle = fname[3:5]
                    else:
                        base = item.split('.')[1]
                        yr = base[0:4]
                        mon = base[4:6]
                        dy = base[6:8]
                        cycle = fname.split('.')[1][1:3]
                    dictFn = mosHelper.makeFilenames(mosname, 'ABCD', yr, mon, dy, cycle)
                    localfilename = dictFn['raw']

                    # If there already exists a file with the intended localfilename,
                    # then don't bother downloading because the file probably already
                    # exists. If the file is too small, try downloading it again.
                    existingRawFiles = mosHelper.listRawFiles(mosname)
                    if localfilename in existingRawFiles:
                        module_logger.info('{} already exists on disk.'.format(localfilename))
                        fpath = os.path.join(dictDirNames['raw'], localfilename)
                        # If the file size is too low (see thresholds above), then
                        # something went wrong last time the file was downloaded. Try
                        # to download it again now so it will be available the next time
                        # this script runs.
                        thresh = dictFilesizeThresh[mosname] * 1000
                        if os.path.getsize(fpath) > thresh:
                            module_logger.info('Skipping. It\'s probably OK.')
                            # 'continue': the current iteration of the loop terminates and
                            # execution continues with the next iteration of the loop.
                            continue
                        else:
                            module_logger.info('Downloading. The copy on disk seems too small.')
                    
                    fileurl = folderurl + '/' + fname
                    response = urllib2.urlopen(fileurl)
                    contents = response.read()
                    response.close()
                    
                    module_logger.info('Writing to %s', localfilename)
                    fullname = os.path.join(dictDirNames['raw'], localfilename)
                    output = open(fullname, 'w')
                    output.write(contents)
                    output.close()
                    rawfiles.append(localfilename)

    except urllib2.URLError:
        module_logger.warning('Lost the connection with MDL. Some files were not downloaded.')

    return(rawfiles)

