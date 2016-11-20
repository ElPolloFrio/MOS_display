import string, urllib2, re, os, logging, mosHelper

# written Sep 2013
# last updated: Nov 2016
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

class MOS(object):
    """ Class to represent and manipulate MOS files from MDL """

    def __init__(self, mostype):

        # (string) MEX, MAV, or MET
        self.mostype = mostype

        # (list of strings) URL(s) to access the MOS file(s)
        self.fileurls = None

        # (list of strings) Local filename(s) corresponding to the
        # MOS file(s) listed in self.fileurls.
        self.localfnames = None

        # (float, int, or long) Minimum file size in kb for a file
        # to be considered complete. Multiply by 1000 to get file size
        # in bytes for use with os.path.getsize.
        self.filethresh = None


    def set_filethresh(self):
        # File sizes in kb. Multiply by 1000 to get file size in bytes for
        # use with os.path.getsize.
        dictFilesizeThresh = {'MAV': 250,
                              'MET': 1000,
                              'MEX': 1500
                              }

        self.filethresh = dictFilesizeThresh[self.mostype]


    def check_primary(self):
        # MDL's FTP site is the primary source. Attempt to access it.

        # MDL changed the folder structure for MET:
        # ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/nam/prod/nam_mos.YYYYMMDD/mdl_nammet.tXXz
        # YYYYMMDD = year/month/day in UTC
        # XX = cycle (00 or 12) in UTC
        # This folder also contains files named 'mdl_nammme.tXXz'.

        # FutureDev:
        # MDL also changed the folder structure for MAV and MEX:
        # MAV:
        # ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfsmos.YYYYMMDD/mdl_gfsmav.tXXz
        # MEX:
        # ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfsmos.YYYYMMDD/mdl_gfsmex.tXXz
        # YYYYMMDD = year/month/day in UTC
        # XX = cycle (00, 06, 12, or 18 for the MAV, 00 or 12 for the MEX and MET) in UTC
        
        dictURLs = {'MAV': 'ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.mav',
                    'MEX': 'ftp://tgftp.nws.noaa.gov/SL.us008001/DF.anf/DC.mos/DS.mex',
                    'MET': 'ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/nam/prod/'
                    }

        fileurls = []
        localfnames = []

        mosname = self.mostype
        url = dictURLs[mosname]

        try:
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

            #print 'Found these folders: %s' % (folders)

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
                #print '%s has these files: %s' %(item, mosfiles)

                for fname in mosfiles:
                    # Construct the file URL
                    furl = '{}/{}'.format(folderurl, fname)
                    fileurls.append(furl)

                    # Construct the local filename. ABCD is a placeholder value
                    # because 'staname' is undefined for raw files in
                    # mosHelper.makeFilenames.
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

                    localfnames.append(localfilename)
                    
            # After all file URLs have been found, store them as an object property.
            # Ditto on the local filenames.
            self.fileurls = fileurls
            self.localfnames = localfnames

            # There's probably a better way to do this. Let '1' stand for success.
            return 1
                
        except urllib2.URLError:
            # There's probably a better way to do this. Let '0' stand for failure.
            return 0


    def check_backup(self):
        # MDL's other site is the secondary source. Attempt to access it.

        # There is also another source for MAV, MET, MEX, but the date and cycle are not present
        # in all filenames. Use mosHelper.getIssuance to determine these elements.
        # MAV:
        # http://www.nws.noaa.gov/mdl/forecast/text/avnmav.txt
        # MET:
        # http://www.nws.noaa.gov/mdl/forecast/text/nammet.txt
        # MEX:
        # http://www.nws.noaa.gov/mdl/forecast/text/mrfmex00.txt
        # http://www.nws.noaa.gov/mdl/forecast/text/mrfmex12.txt
        
        backupURLs = {'MAV': ['http://www.nws.noaa.gov/mdl/forecast/text/avnmav.txt'],
                      'MEX': ['http://www.nws.noaa.gov/mdl/forecast/text/mrfmex00.txt',
                              'http://www.nws.noaa.gov/mdl/forecast/text/mrfmex12.txt'
                              ],
                      'MET': ['http://www.nws.noaa.gov/mdl/forecast/text/nammet.txt']
                      }

        mosname = self.mostype        
        urls = backupURLs[mosname]

        bucket = []
        fileurls = []
        localfnames = []

        try:
            for u in urls:
                response = urllib2.urlopen(u)
                contents = response.readlines()
                response.close()
                bucket.append(contents)

                # This seems silly. We've already downloaded the file. Why mark it
                # for downloading again?
                # FutureDev: Surely there's a better way.
                fileurls.append(u)

            for item in bucket:
                info = mosHelper.getIssuance(item)
                yr = info['DATE'].split('/')[2]
                mon = info['DATE'].split('/')[0]
                dy = info['DATE'].split('/')[1]
                cycle = info['CYCLE']

                dictFn = mosHelper.makeFilenames(mosname, 'ABCD', yr, mon, dy, cycle)
                localfilename = dictFn['raw']

                localfnames.append(localfilename)
                    
            # After all file URLs have been found, store them as an object property.
            # Ditto on the local filenames.
            self.fileurls = fileurls
            self.localfnames = localfnames
            
            # There's probably a better way to do this. Let '1' stand for success.
            return 1
            
        except urllib2.URLError:
            # There's probably a better way to do this. Let '0' stand for failure.
            return 0


    def __str__(self):
        return '{} {}/{}/{} {} UTC'.format(self.mostype, self.mon, self.dy, self.yr, self.cycle)


def GrabEm():

    # Grab a reference to the existing logger.
    # This only works if the script calling this function has
    # already called mosHelper.setUpTheLogger().
    module_logger = logging.getLogger('mosgraphics.GrabEm')

    dictDirNames = mosHelper.getDirNames()

    moslist = ['MET', 'MEX', 'MAV']

    # Use this to keep track of which files were written and still need
    # to be processed with mosHelper.parseStations.
    rawfiles = []
    
    for mosname in moslist:
        tempObj = MOS(mosname)
        tempObj.set_filethresh()
        
        module_logger.info('Asking MDL for the {}'.format(mosname))
        status = tempObj.check_primary()

        if status is not 1:
            module_logger.warning('Lost the connection with MDL. File was not downloaded.')
            module_logger.info('Trying another server')
            status2 = tempObj.check_backup()
            
            if status2 is not 1:
                module_logger.warning('Bummer. Unable to download {}'.format(mosname))
            elif status2 is 1:
                module_logger.info('Success!')
            else:
                module_logger.info('? ? ? ? ? ?')

        if tempObj.fileurls is not None:
            for furl, localfilename in zip(tempObj.fileurls, tempObj.localfnames):
                # If there already exists a file with the intended localfilename,
                # check to see if it has an appropriate size. If the file seems
                # too small, then try downloading it again. Otherwise, don't bother
                # because it's probably OK.
                existingRawFiles = mosHelper.listRawFiles(mosname)
                if localfilename in existingRawFiles:
                    module_logger.info('{} already exists on disk.'.format(localfilename))
                    fpath = os.path.join(dictDirNames['raw'], localfilename)

                    # If the file size is too small, then something went wrong the
                    # last time the file was downloaded. Try to download it again
                    # now so that it will be available for the next script run.
                    thresh = tempObj.filethresh * 1000
                    if os.path.getsize(fpath) > thresh:
                        module_logger.info('Skipping. It\'s probably OK.')
                        # 'continue': the current iteration of the loop terminates
                        # and execution continues with the next iteration of the loop.
                        continue
                    else:
                        module_logger.info('Downloading. The copy on disk seems too small.')

                # Note that in order to reach this part of the script, the file
                # size must pass the above if-else.
                response = urllib2.urlopen(furl)
                contents = response.read()
                response.close()

                module_logger.info('Writing to %s', localfilename)
                fullname = os.path.join(dictDirNames['raw'], localfilename)
                output = open(fullname, 'w')
                output.write(contents)
                output.close()
                rawfiles.append(localfilename)
                    
        else:
            module_logger.info('A rolling stone gathers no {} MOS.'.format(mosname))

    return(rawfiles)

