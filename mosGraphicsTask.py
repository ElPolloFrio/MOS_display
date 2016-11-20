import datetime as dt
import os, logging, GoGetFiles, mosHelper, mosplots, purge

# Here's the deal:
# MET usually comes in at 00/12z + 3 hours
# MAV usually comes in at 00/06/12/18z + 4 hours
# MEX usually comes in at 00/12z + 5 hours
#
# In an ideal world, we could schedule the task to run at
# 03z, 04z, 05z, 10z, 15z, 16z, 17z, 22z. However, the Windows
# scheduler on the server only permits regular intervals of
# hours. 6 hours is too sparse, so let's schedule it to run every
# 3 hours and do some checking to figure out which hours to skip
# and which MOS to run at which hours. This only matters if the
# total runtime will exceed 3 hours (possible for a lot of sites,
# but unknown as of 1/28/2014), otherwise it might be a nice
# feature to run every MOS at every opportunity-- if one of the
# MOS products was delayed, it will still be processed on the
# next run.
#
# Here is one option:
# CDT  7p 10p 01a 04a 07a 10a  1p  4p
# CST  6p  9p 12a 03a 06a 09a 12p  3p
# UTC 00z 03z 06z 09z 12z 15z 18z 21z
#     MAV MET MAV  X  MAV MET MAV  X
#             MEX             MEX

# Trying to be clever and get around the DST/standard time issues. This part
# was written during standard time. Be sure to check after the switch to DST
# that it still works as intended.
rightnow = dt.datetime.utcnow()
# Define a dictionary whose keys correspond to str(rightnow.hour) and whose
# values are the MOS products to generate on that hour's run.
dictTimeControl = {}
dictTimeControl['0'] = ['MAV']
dictTimeControl['3'] = ['MET']
dictTimeControl['6'] = ['MAV', 'MEX']
dictTimeControl['12'] = ['MAV']
dictTimeControl['15'] = ['MET']
dictTimeControl['18'] = ['MAV', 'MEX']
# Use this to cheat to force all graphics on an off hour.
#dictTimeControl[str(rightnow.hour)] = ['MAV', 'MEX', 'MET']
#
# The Windows Scheduler is on standard time. DST cheap trick.
dictTimeControl['1'] = ['MAV']
dictTimeControl['4'] = ['MET']
dictTimeControl['7'] = ['MAV', 'MEX']
dictTimeControl['13'] = ['MAV']
dictTimeControl['16'] = ['MET']
dictTimeControl['19'] = ['MAV', 'MEX']

# Create the logger used by this script, GoGetFiles, and mosplots
logger = mosHelper.setUpTheLogger()

# Go get files from MDL
# Design decision: keep this outside of the try/except below, and don't
# specify which MOS to download (request all 3 types). Do this because
# occasionally the connection with MDL is lost and some files aren't
# downloaded, so it's better to have more opportunities to get the
# latest files. May need to revisit this design decision depending on
# performance.
newfiles = GoGetFiles.GrabEm()

# Set station lists for which to process raw files
CWAlist = mosHelper.setStations()
sites = [CWAlist['LSX'],
         CWAlist['SGF'],
         CWAlist['EAX_lite'],
         CWAlist['ILX_lite'],
         #CWAlist['LIX_lite'],
         CWAlist['PAH_lite'],
         CWAlist['DVN_lite'],
         CWAlist['TEST']
         ]

# Set mos types for which to process raw files based on the hour.
# If nothing is defined for this hour, then quit.
try:
    try:
        mostypes = dictTimeControl[str(rightnow.hour)]
        logger.info('It\'s %02dz, time for: %s', rightnow.hour, mostypes)
    except KeyError:
        logger.info('It\'s %02dz, nothing to process. Move along, move along, nothing to see here.', rightnow.hour)
        mostypes = [] # Define it to avoid NameError: name 'mostypes' is not defined
    for CWA in sites:
        for asos in CWA:
            for mos in mostypes:
                logger.info('Processing: %s %s', mos, asos)
                mosHelper.processFromSavedFiles(mos, asos)
                try:
                    logger.info('Attempting to plot: %s %s', mos, asos)
                    fn = mosHelper.getLatestFilename(mos, asos)
                    plotme, xdt, info, prev = mosplots.makeDisplayArrays(fn)
                    mosplots.makePlots(plotme, xdt, info, prev)
                except IndexError:
                    logger.warning('This error usually means that %s doesn\'t exist in %s', asos, mos)
                except:
                    logger.warning('Something, somewhere, went horribly wrong. Barfed on %s %s', asos, mos)
finally:
    # Get rid of old raw files
    purge.cleanHouse()
    # Clear all processed files in preparation for the next run
    purge.clearProcFiles()
    
    logger.info('--------------------------------Dun dun dun...done.')
    # Perform an orderly shutdown of the logger (flush and close all handlers)
    logging.shutdown()
