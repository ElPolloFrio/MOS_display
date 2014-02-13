import string, urllib2, re, os, logging, mosHelper

# written Sep 2013
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

    # Look here for the MAV, MET, and MEX
    urls = ['ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.mav',
        'ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.met',
        'ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.mex']

    dictDirNames = mosHelper.getDirNames()

    # Use this to keep track of which files were written and still need
    # to be processed with mosHelper.parseStations
    rawfiles = []

    try:
        for url in urls:
            mosname = url[-3:]
            module_logger.info('Asking MDL for the %s', mosname)
            response = urllib2.urlopen(url)
            contents = response.read()
            response.close()

            # Each FTP directory contains at most 2 folders: RD.YYYYMMDD (RD.20130909),
            # although it used to contain a much longer archive.
            # Find the RD.######## section(s) of the string to get the folder names.
            RD = re.compile(r'RD\.[0-9]+')
            folders = RD.findall(contents)
            module_logger.info('Found these folders: %s', folders)

            for item in folders:
                folderurl = url + '/' + item + '/'
                response = urllib2.urlopen(folderurl)
                contents = response.read()
                response.close()
    
                # Each folder contains at most 4 files: cy.CC.txt (cy.00.txt, etc.)
                # Find the cy.##.txt section(s) of the string to get the filenames.
                CY = re.compile(r'cy\.[0-9]+\.txt')
                mosfiles = CY.findall(contents)
                module_logger.info('%s has these files: %s', item, mosfiles)

                for fname in mosfiles:
                    # Write to a local file with a meaningful name. ABCD is a placeholder b/c staname is
                    # undefined for raw files in mosHelper.makeFilenames.
                    #localfilename = mosname + '-' + item[3:7] + '-' + item[7:9] + '-' + item[9:11] + '-' + fname[3:5] + 'z.txt'
                    dictFn = mosHelper.makeFilenames(mosname, 'ABCD', item[3:7], item[7:9], item[9:11], fname[3:5])
                    localfilename = dictFn['raw']

                    # If there already exists a file with the intended localfilename,
                    # then don't bother downloading because the file probably already
                    # exists. This check fails if the file exists but is empty.
                    existingRawFiles = mosHelper.listRawFiles(mosname)
                    if localfilename in existingRawFiles:
                        module_logger.info('Skipping %s becaues it already exists on disk', localfilename)
                        pass
                    else:
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

