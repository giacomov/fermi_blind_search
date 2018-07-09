# LAT Transient Factory

import matplotlib

from fermi_blind_search.fits_handling.fits_interface import pyfits

matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy
import os
import sys
import shutil
import errno
import subprocess
import uuid
import StringIO

import GtApp
import pil

from GtBurst import dataHandling
from GtBurst.angularDistance import getAngularDistance
from GtBurst import aplpy
from GtBurst.GtBurstException import GtBurstException

import scipy.stats.distributions

from fermi_blind_search import BayesianBlocks
from fermi_blind_search.Configuration import configuration
from fermi_blind_search.ltfException import ltfException
from fermi_blind_search.SkyDir import SkyDir
from fermi_blind_search.bkge import ROIBackgroundEstimator
from fermi_blind_search.fits_handling.fits import FitsFile, make_GTI_from_FT2, update_GTIs
from fermi_blind_search.fits_handling.fits_interface import pyfits


try:
    import sklearn.cluster
except:
    pass

from fermi_blind_search import myLogging

import multiprocessing
import warnings

import time

try:

    from pymongo import MongoClient as Connection

except ImportError:

    has_database = False

    warnings.warn("\n\n***** DATABASE not available (pymongo is not properly installed) *****\n\n")

else:

    has_database = True

from astropy.coordinates import SkyCoord
import astropy.units as u
import re


def get_IAU_name(ra,dec):

    direction = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')

    # This is something like HHMMSS.ss-DDMMSS.ss

    iau = re.sub('([^0-9\-\.])', "", direction.to_string('hmsdms', precision=2))

    return "LTF %s" % iau


def getConnectionToResultsStorage():
    # Get host and port of the DB

    port = int(configuration.get('Database', 'port'))
    host = configuration.get('Database', 'host')

    # Connect directly with the host

    conn = Connection(host, port)

    db = conn[configuration.get('Database', 'name')]
    db.authenticate(configuration.get('Database', 'username'),
                    configuration.get('Database', 'password'))

    collection = db[configuration.get('Database', 'collection_name')]
    return collection


def setup_process():
    # Setup the logging

    thisLogger = myLogging.log.getLogger(multiprocessing.current_process().name)
    sl = myLogging.StreamToLogger(thisLogger, myLogging.log.DEBUG)
    sys.stdout = sl
    sl = myLogging.StreamToLogger(thisLogger, myLogging.log.ERROR)
    sys.stderr = sl

    # Set up PFILES so that they will be written in the current directory
    # of the running job
    user_pfiles, sys_pfiles = os.environ['PFILES'].split(";")
    os.environ['PFILES'] = ".:" + user_pfiles + ";" + sys_pfiles
    print("\nPFILES env. variable is now:")
    print(os.environ['PFILES'])

    # Setup configuration directory for gtburst
    os.environ['GTBURSTCONFDIR'] = os.getcwd()


def figureToString(figure):
    imgdata = StringIO.StringIO()
    figure.savefig(imgdata, format='png', bbox_inches='tight')
    imgdata.seek(0)
    data_uri = imgdata.read().encode('base64').replace('\n', '')
    return data_uri


class AllSkySearch(object):
    def __init__(self, ras, decs, rad, timeInterval, analysisDefinition, nullHypProb=6.33e-05, cpus=8, mute=False):
        self.ras = ras
        self.decs = decs
        self.rad = rad
        self.nullHypProb = float(nullHypProb)
        self.npoints = ras.shape[0]
        self.timeInterval = timeInterval
        self.analysisDefinition = analysisDefinition
        self.cpus = min(int(cpus), ras.shape[0])
        self.mute = bool(mute)

    def go(self, prepare_figures=True):

        thisLogger = myLogging.log.getLogger("AllSkySearch.go")

        intervals = [self.timeInterval] * self.npoints
        anDefs = [self.analysisDefinition] * self.npoints
        rads = [self.rad] * self.npoints
        probs = [self.nullHypProb] * self.npoints

        start = time.time()

        results = []

        if self.cpus > 1:

            pool = multiprocessing.Pool(self.cpus, setup_process)

            for i, res in enumerate(pool.imap(worker, zip(self.ras, self.decs, rads, anDefs, intervals, probs))):

                if ((i + 1) % 100) == 0:
                    thisLogger.info("%s out of %s completed" % (i + 1, self.npoints))

                results.append(res)

            pool.close()
            pool.join()

        else:

            for i, res in enumerate(map(worker, zip(self.ras, self.decs, rads, anDefs, intervals, probs))):

                if ((i + 1) % 100) == 0:
                    thisLogger.info("%s out of %s completed" % (i + 1, self.npoints))

                results.append(res)

        thisLogger.info("completed search in %s regions" % self.npoints)

        stop = time.time()
        thisLogger.info("Elapsed time: %s" % (stop - start))

        interestingIntervals = []
        self.excludedBecauseOfDuration = 0
        for k in results:
            try:
                # Get all the time intervals from the excesses for this RA,Dec point
                intervals = map(lambda x: (x.timeInterval.tstart, x.timeInterval.tstop), k)
            except:
                continue
            if (len(intervals) > 1):
                interestingIntervals.append(k)
            elif (len(intervals) == 0):
                continue
            else:
                thisInterval = k[0]

                print("Observed: %s, expected: %s (p = %s)" % (
                thisInterval.nobs, thisInterval.npred, thisInterval.probability))

                if (thisInterval.probability <= self.nullHypProb):

                    if (thisInterval.timeInterval.tstop - thisInterval.timeInterval.tstart >= float(
                            configuration.get("Analysis", "Max_duration"))):
                        print(
                        "Interval excluded because the duration is larger than the Max_duration value in configuration")
                        self.excludedBecauseOfDuration += 1
                        continue
                    pass

                    # Save it nevertheless
                    interestingIntervals.append(k)
                pass

            pass
        pass

        thisLogger.info("Found %s interesting intervals" % (len(interestingIntervals)))

        # Re-activate the interesting intervals
        for inte in interestingIntervals:
            for intee in inte:
                intee.restore()

                thisLogger.info("(R.A., Dec.) = (%.2f,%.2f), %s - %s, Nobs = %i, Npred = %.3g, prob = %g"
                                % (intee.ra, intee.dec, intee.timeInterval.tstart, intee.timeInterval.tstop,
                                   intee.nobs, intee.npred, intee.probability))
        
        # Get the figures
        figs = []
        
        if prepare_figures:
        
            thisLogger.info("Preparing figures...")
            
            for j, inte in enumerate(interestingIntervals):
                for i, intee in enumerate(inte):
                    img, clusters = intee.getImage()
                    img.save("_%s.png" % i)
                    plt.close()
    
                if (len(inte) > 1):
                    thisFig, subs = plt.subplots(1, len(inte), figsize=[1.33 * 8, 8])
                else:
                    thisFig, subs = plt.subplots(1, len(inte), figsize=[1.33 * 8, 8])
                    subs = [subs]
                pass
    
                for i, sub in enumerate(subs):
                    img = plt.imread("_%s.png" % i)
                    im = sub.imshow(img)
                    sub.set_title("%.2f - %.2f s" % (inte[i].timeInterval.tstart, inte[i].timeInterval.tstop),
                                  fontsize='x-small')
                    sub.axis('off')
                figs.append(thisFig)
                plt.close()
            pass
            thisLogger.info("done")
        
        else:
            
            thisLogger.info("Figures are not requested. Skipping...")

        self.figs = figs
        self.interestingIntervals = interestingIntervals

        return interestingIntervals, figs

    pass

    def getExcludedBecauseOfDuration(self):
        return self.excludedBecauseOfDuration

    def save_to_file(self, filename):

        # Each candidate transient corresponds to a row in the output file

        candidate_transients = []

        for interesting_region in self.interestingIntervals:

            this_ra = interesting_region[0].ra
            this_dec = interesting_region[0].dec

            tstarts = []
            tstops = []
            counts = []
            probs = []

            for interval in interesting_region:

                tstarts.append(str(interval.timeInterval.tstart))
                tstops.append(str(interval.timeInterval.tstop))
                counts.append(str(interval.nobs))
                probs.append(str(interval.probability))

            # Now create a name according to the IAU Specifications for Nomenclature
            name = get_IAU_name(this_ra, this_dec)

            this_row = [name.replace(" ","_"),
                        str(this_ra),
                        str(this_dec),
                        ",".join(tstarts),
                        ",".join(tstops),
                        ",".join(counts),
                        ",".join(probs)]

            candidate_transients.append(" ".join(this_row))

        with open(filename, "w+") as f:

            f.write("# name ra dec tstarts tstops counts probability\n")

            f.write("\n".join(candidate_transients))

            f.write("\n")

    def save(self):
        '''Save in the database
        '''

        if not has_database:

            raise RuntimeError("Cannot save to database, you don't have pymongo installed!")

        # Prepare dictionaries and insert them in the database
        for inte, fig in zip(self.interestingIntervals, self.figs):
            # Store the position as a GeoJSON pair of longitude,latitude points
            # so that queries for positions are super fast
            # (Note: while RA goes from 0 to 360, longitude goes from -180 to 180,
            # so we have to correct that)
            rra = inte[0].ra
            rra = rra if rra <= 180 else rra - 360
            geoJson = {'type':
                           "Point",

                       'coordinates':
                           [rra,
                            inte[0].dec]
                       }

            skdir = SkyDir(inte[0].ra, inte[0].dec, 'equatorial')
            ll, b = skdir.l, skdir.b
            ll = ll if ll <= 180 else ll - 360
            geoJsonGal = {'type':
                              "Point",

                          'coordinates':
                              [ll,
                               b]
                          }

            intervals = []
            for intee in inte:
                thisInterval = {
                    'met_start': intee.timeInterval.tstart,
                    'met_stop': intee.timeInterval.tstop,
                    'probability': intee.probability
                }
                intervals.append(thisInterval)
            pass

            thisResult = {
                'center_j2000': geoJson,
                'center_gal': geoJsonGal,
                'radius': inte[0].rad,
                'analysis_met_start': self.timeInterval.tstart,
                'analysis_met_stop': self.timeInterval.tstop,
                'intervals': intervals,
                'instrument_response_function': inte[0].analysisDef.irf,
                'zenith_max': inte[0].analysisDef.zmax,
                'energy_min': inte[0].analysisDef.emin,
                'energy_max': inte[0].analysisDef.emax,
                'figure': figureToString(fig)
            }

            collection = getConnectionToResultsStorage()
            collection.insert(thisResult)
        pass

    pass


pass


def getID():
    # Return a shortened version of the uuid4 unique id
    return uuid.uuid4().hex  # .bytes.encode('base64').rstrip('=\n').replace('/', '_')


def worker(args):
    # sys.stderr.write("Worker start")
    r, d, rr, a, t, p = args
    grbRoi = SearchRegion(r, d, rr, a, t)
    try:
        counts = grbRoi.applySelection()
    except ltfException as e:
        sys.stderr.write(e.message)
        # sys.stderr.write("Worker end")
        return [[]]
    except:
        raise

    if (counts == 0):
        res = [[]]
    else:
        res = grbRoi.searchForExcesses(p)
    pass

    grbRoi.done()
    # sys.stderr.write("Worker end")
    return res


class AnalysisDefinition(object):
    def __init__(self, irf, zmax, thetamax, emin, emax):
        self.irf = irf
        self.zmax = float(zmax)
        self.thetamax = float(thetamax)
        self.emin = float(emin)
        self.emax = float(emax)

    pass


pass


class TimeInterval(object):
    def __init__(self, tstart, tstop, ft1, ft2, simft1=None):
        self.tstart = float(tstart)
        self.tstop = float(tstop)

        if ((self.tstop - self.tstart) < 1e-15):
            raise ltfException("Time interval cannot have tstart=tstop")

        self.ft1 = os.path.abspath(ft1)
        self.ft2 = os.path.abspath(ft2)

        if simft1 is not None:

            self.simft1 = os.path.abspath(simft1)

            # Open the simulated FT1 and get the renormalization factor
            header = pyfits.getheader(self.simft1)
            self.symBoost = float(header['SYMBOOST'])

        else:

            self.simft1 = None
            self.symBoost = 1.0

    pass


pass


# This is a decorator which makes a method of a class run into the self.working directory
def in_workdir(method):
    def wrapper(*args):
        origdir = os.getcwd()

        workdir = args[0].workdir

        if (os.path.abspath(origdir) == os.path.abspath(workdir)):
            # we are already there, nothing to do
            print("Decorator: we are already in %s" % (workdir))
            return method(*args)

        else:
            print("Decorator: moving to directory %s" % (args[0].workdir))

            os.chdir(workdir)

            try:
                res = method(*args)

            finally:
                print("Decorator: moving back to %s" % (origdir))
                os.chdir(origdir)
            pass
        pass

        return res

    return wrapper


# This will create a directory only if does not exists, otherwise
# it will throw an exception
def createIfNotExists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
        else:
            raise ltfException("The directory %s already exists!" % path)


def copyPfiles(path):

    pfiles = ['gtselect.par', 'gtmktime.par', 'gtobssim.par',
              'fdelhdu.par', 'fappend.par']

    for pfile in pfiles:

        try:

            thisPil = pil.Pil(pfile)
            newName = os.path.join(os.path.abspath(path), pfile)
            thisPil.write(newName)

        except:

            if pfile.find("gt")==0:

                # A Fermi pfile, raise an error
                raise

            else:

                # A heasoft pfile, issue a warning (they are only needed for simulations)
                warnings.warn("Could not find pfile %s. You might encounter problems ")


# A class featuring a select method
class Selector(object):
    def __init__(self, ra, dec, rad, analysisDef, timeInterval):
        self.ra = float(ra)
        self.dec = float(dec)
        self.rad = float(rad)
        self.analysisDef = analysisDef
        self.timeInterval = timeInterval
        self.uid = "%s" % getID()
        self.workdir = os.path.join(os.path.abspath(os.getcwd()), "_%s" % self.uid)

        # Create unique workdir. All commands with the @in_workdir decorator
        # will run in that workdir
        createIfNotExists(self.workdir)

        # Copy pfiles in workdir
        copyPfiles(self.workdir)

        self.cleaned = False

    pass

    def done(self):
        # Remove workdirectory
        print("Cleaning up %s..." % (self.workdir))
        shutil.rmtree(self.workdir, ignore_errors=True)
        self.cleaned = True

    def __del__(self):
        # Remove workdirectory, if the user didn't call the done()
        # method
        try:

            print("Cleaning up %s in destructor..." % (self.workdir))
            shutil.rmtree(self.workdir, ignore_errors=True)

        except:

            pass

    @in_workdir
    def _select(self, tstart, tstop):

        # Make GTI file first
        filter_expression = '(DATA_QUAL>0 || DATA_QUAL==-1) && LAT_CONFIG==1 && IN_SAA!=T && LIVETIME>0 && ' \
                            '(ANGSEP(RA_ZENITH,DEC_ZENITH,%(ra)s,%(dec)s)<=(%(zmax)s-%(rad)s)) ' \
                            '&& (ANGSEP(RA_SCZ,DEC_SCZ,' \
                            '%(ra)s,%(dec)s)<=(%(thetamax)s-%(rad)s))' % {'ra': self.ra,
                                                                          'dec': self.dec,
                                                                          'zmax': self.analysisDef.zmax,
                                                                          'rad': self.rad,
                                                                          'thetamax': self.analysisDef.thetamax}

        gti_file = "__GTI.fit"

        gti_starts, gti_stops = make_GTI_from_FT2(self.timeInterval.ft2, filter_expression, gti_file, overwrite=True,
                                                  force_start=tstart, force_stop=tstop)

        gti_filter = "gtifilter('%s')" % gti_file
        energy_filter = "(ENERGY >= %s) && (ENERGY <= %s)" % (self.analysisDef.emin, self.analysisDef.emax)
        flt = '(%s) && (%s)' % (energy_filter, gti_filter)

        # Apply filter
        thisEventFile = 'filt_ft1_%s.fit' % self.uid

        fits = FitsFile(self.timeInterval.ft1,
                        'EVENTS',
                        flt,
                        cone=(self.ra, self.dec, self.rad))

        nEvents = len(fits['EVENTS'].data)

        fits.write_to(thisEventFile, overwrite=True)

        update_GTIs(thisEventFile, gti_starts, gti_stops)

        # latData = dataHandling.LATData(self.timeInterval.ft1,
        #                                self.timeInterval.ft1,
        #                                self.timeInterval.ft2,
        #                                self.uid)
        #
        # try:
        #     thisEventFile2, nEvents2 = latData.performStandardCut(self.ra,
        #                                                         self.dec,
        #                                                         self.rad,
        #                                                         self.analysisDef.irf,
        #                                                         tstart,
        #                                                         tstop,
        #                                                         self.analysisDef.emin,
        #                                                         self.analysisDef.emax,
        #                                                         self.analysisDef.zmax,
        #                                                         self.analysisDef.thetamax,
        #                                                         gtmktime=True)
        #
        # except GtBurstException as gtburstError:
        #
        #     if (gtburstError.code in [14, 2, 21, 22, 23]):
        #         # gtmktime or gtselect returned 0 events or 0 rows,
        #         # i.e., this is an empty ROI
        #         return None, 0
        #     else:
        #         print("\n\nGTSELECT FAILED\n\n")
        #         return None, 0
        # pass
        #
        # assert nEvents == nEvents2

        # Open the file just produced, fix it and get some info
        with pyfits.open(thisEventFile, mode='update') as f:

            # Get the total elapsed time (i.e., the sum of all GTIs)
            gti = f['GTI'].data
            self.onsource = numpy.sum(gti.STOP - gti.START)

            # Add a DS keyword describing the ROI (we will use it later)
            f['EVENTS'].header['DSTYP9'] = 'POS(RA,DEC)'
            f['EVENTS'].header['DSUNI9'] = 'deg'
            f['EVENTS'].header['DSVAL9'] = 'circle(%s,%s,%s)' % (self.ra, self.dec, self.rad)

        return thisEventFile, nEvents

class Excess(Selector):
    def setNpred(self, npred):
        '''Set the number of predicted counts within the interval'''
        self.npred = float(npred)

    def computeProbability(self):
        if hasattr(self, 'npred') and hasattr(self, 'nobs'):
            self.probability = self._poissonProbability()
        else:
            raise ltfExcess("Cannot compute probability without npred and nobs")
        pass

        return self.probability

    def _poissonProbability(self):
        # The probability of obtaining nobs *or more* when npred is expected
        return (scipy.stats.distributions.poisson.sf(self.nobs, self.npred) +
                scipy.stats.distributions.poisson.pmf(self.nobs, self.npred))

    def setNobs(self, nobs):
        '''Set the number of observed counts'''
        self.nobs = int(nobs)

    def restore(self):
        '''Restore the class if it comes from a parallel job and its directory
           has been removed
        '''
        if (os.path.exists(self.workdir)):
            # Do nothing
            return
        else:
            self.workdir = os.path.join(os.path.abspath(os.getcwd()), self.uid)

            # Create unique workdir. All commands with the @in_workdir decorator
            # will run in that workdir
            createIfNotExists(self.workdir)

            # Copy pfiles in workdir
            copyPfiles(self.workdir)

            self.cleaned = False
        pass

    pass

    @in_workdir
    def getImage(self, clustering=None):  # clustering="dbscan"
        # Select
        thisEventFile, _ = self._select(self.timeInterval.tstart, self.timeInterval.tstop)

        latData = dataHandling.LATData(thisEventFile,
                                       thisEventFile,
                                       self.timeInterval.ft2,
                                       self.uid)

        outfile = "__%s_skymap.fits" % (self.uid)
        latData.doSkyMap(outfile, binsz=0.2, fullsky=False)

        if (clustering != None):
            data = pyfits.getdata(thisEventFile)
            alg = getClusteringAlgorithm(clustering)
            clusters = alg.getClusters(data.field("RA"), data.field("DEC"), data.field("ENERGY"))
        else:
            clusters = []
        pass

        # Generate the figure
        image = plotFitsCountsmap(outfile, "%.2f - %.2f" % (self.timeInterval.tstart, self.timeInterval.tstop))
        os.remove(outfile)

        return image, clusters

    pass


pass


class SearchRegion(Selector):
    @in_workdir
    def applySelection(self):

        # Select
        self.selectedEventFile, self.nEvents = self._select(self.timeInterval.tstart, self.timeInterval.tstop)

        # How many counts?

        if (self.nEvents == 0):

            print("\nNo events in ROI!\n")
            return 0

        elif (self.nEvents < 2):

            print("\nToo few events in ROI (%s)!" % (self.nEvents))
            return 0

        else:

            # self._applySelectionToSim()

            return self.nEvents

    @in_workdir
    def _applySelectionToSim(self):

        # Pre-select so that gtselect is faster
        region_filter = "circle(%.3f,%.3f,%s,RA,DEC)" % (self.ra, self.dec, self.rad)

        # Make this in one line so the instance is not kept in memory
        FitsFile(self.timeInterval.ft1,
                 'EVENTS',
                 '(%s)' % region_filter).write_to("__preFilt.fit", overwrite=True)

        gtselect = GtApp.GtApp('gtselect')
        gtselect['infile'] = '__preFilt.fit'
        gtselect['outfile'] = '__sel.fits'
        gtselect['ra'] = self.ra
        gtselect['dec'] = self.dec
        gtselect['rad'] = self.rad
        gtselect['tmin'] = self.timeInterval.tstart
        gtselect['tmax'] = self.timeInterval.tstop
        gtselect['emin'] = self.analysisDef.emin
        gtselect['emax'] = self.analysisDef.emax
        gtselect['zmax'] = self.analysisDef.zmax
        gtselect['evclsmin'] = 0
        gtselect['evclsmax'] = 1000
        gtselect['evclass'] = 'INDEF'  # IRFS[self.analysisDef.irf].evclass
        gtselect['evtype'] = 'INDEF'
        gtselect['convtype'] = -1
        gtselect['phasemin'] = 0.0
        gtselect['phasemax'] = 1.0
        gtselect['evtable'] = 'EVENTS'
        gtselect['chatter'] = 2
        gtselect['clobber'] = 'yes'
        gtselect['debug'] = 'no'
        gtselect['gui'] = 'no'
        gtselect['mode'] = 'ql'

        gtselect.run()

        # Remove GTI extension
        cmdLine = "fdelhdu %s[GTI] 'no' 'yes'" % "__sel.fits"
        print("\n%s\n" % cmdLine)
        subprocess.check_output(cmdLine, shell=True)

        # Append new GTI extension, taken from self.selectedEventFile
        cmdLine = "fappend %s[GTI] __sel.fits" % self.selectedEventFile
        print("\n%s\n" % cmdLine)
        subprocess.check_output(cmdLine, shell=True)

        self.selectedEventFileSim = "sim_%s" % (self.selectedEventFile)

        # Apply the GTI
        gti_filter = "gtifilter('__sel.fits[GTI]')"

        # Make this in one line so the instance is not kept in memory
        FitsFile(self.timeInterval.ft1,
                 'EVENTS',
                 '%s' % gti_filter).write_to(self.selectedEventFileSim, overwrite=True)

        gti = pyfits.getdata(self.selectedEventFileSim, 'GTI')
        print("Exposure is %s" % (numpy.sum(gti.STOP - gti.START)))
        if (abs(self.onsource - numpy.sum(gti.STOP - gti.START)) > 1.0):
            raise ltfException("The on-source time differs between data and simulation!")

        events = pyfits.getdata(self.selectedEventFileSim, "EVENTS")
        print("Events in simulation: %s" % (events.shape[0]))
        if (events.shape[0] < 2):
            raise ltfException("Only %s events in simulation for this interval (minimum is 2). Was %s in real data." % (
            events.shape[0], self.nEvents))

    @in_workdir
    def getLightCurve(self, outfile, binsize):
        gtbin = GtApp.GtApp('gtbin')
        gtbin['algorithm'] = 'LC'
        gtbin['evfile'] = self.selectedEventFile
        gtbin['outfile'] = outfile
        gtbin['scfile'] = self.timeInterval.ft2
        gtbin['tbinalg'] = 'LIN'
        gtbin['tstart'] = self.timeInterval.tstart
        gtbin['tstop'] = self.timeInterval.tstop
        gtbin['dtime'] = binsize
        gtbin['lcemin'] = self.analysisDef.emin
        gtbin['lcemax'] = self.analysisDef.emax

        gtbin.run()

    def setSimEventFile(self, simEventFile):
        self.simEventFile = simEventFile

    @in_workdir
    def getSimLC(self, outfile, binsize):
        # Finally make the LC
        gtbin = GtApp.GtApp('gtbin')
        gtbin['evfile'] = self.selectedEventFileSim
        gtbin['scfile'] = self.timeInterval.ft2
        gtbin['outfile'] = outfile
        gtbin['algorithm'] = 'LC'
        gtbin['tbinalg'] = 'LIN'
        gtbin['tstart'] = self.timeInterval.tstart
        gtbin['tstop'] = self.timeInterval.tstop
        gtbin['dtime'] = binsize
        gtbin['lcemin'] = self.analysisDef.emin
        gtbin['lcemax'] = self.analysisDef.emax
        gtbin['chatter'] = 2
        gtbin['clobber'] = 'yes'
        gtbin['debug'] = 'no'
        gtbin['gui'] = 'no'
        gtbin['mode'] = 'ql'

        gtbin.run()

    @in_workdir
    def _createNpredIntegralDistribution(self):
        '''
        Make the integral distribution of the counts in the simulation, and then
        interpolate it with a spline, which will make the computation of the 
        expected counts between 0 and t very fast
        '''

        bkge = ROIBackgroundEstimator.ROIBackgroundEstimator(self.selectedEventFile, self.timeInterval.ft2)

        self.NpredIntegralDistribution = bkge.getIntegralDistribution(self.timeInterval.tstart)

    pass

    @in_workdir
    def searchForExcesses(self, nullHypProb=1e-05):

        self._createNpredIntegralDistribution()

        import fitsio

        #data = pyfits.getdata(self.selectedEventFile)

        #t = data.field("TIME")

        t = fitsio.read(self.selectedEventFile, columns=['TIME'], ext='EVENTS')['TIME']

        t.sort()

        tt = t - self.timeInterval.tstart

        if (tt.shape[0] == 0):
            print("No events in this ROI!")
            return [self.timeInterval.tstart, self.timeInterval.tstop]

        try:

            # res = myBB.bayesian_blocks(tt,nullHypProb,self.NpredIntegralDistribution)
            res = BayesianBlocks.bayesian_blocks(tt, 0.0,
                                                 self.timeInterval.tstop - self.timeInterval.tstart,
                                                 nullHypProb, self.NpredIntegralDistribution)

        except:

            sys.stderr.write("BB failed for region centered at (RA, Dec.) = %s,%s" % (self.ra, self.dec))

            raise

        self.excesses = []

        for t1, t2 in zip(res[0:], res[1:]):

            print("%s - %s" % (t1, t2))

            tt1 = t1 + self.timeInterval.tstart
            tt2 = t2 + self.timeInterval.tstart

            in_interval_idx = (t > tt1 - 1e-5) & (t < tt2 + 1e-5)

            nobs = numpy.sum(in_interval_idx)

            # Set the time interval to start just before the first event and just after the
            # last one. Otherwise, due to the Voronoi cells strategy, we might end up with a
            # tt1 and a tt2 in the middle of a BTI or a SAA passage

            if nobs >= 2:
                tt1 = t[in_interval_idx].min() - 1e-5
                tt2 = t[in_interval_idx].max() + 1e-5

            npred = (self.NpredIntegralDistribution(tt2 - self.timeInterval.tstart)
                     - self.NpredIntegralDistribution(tt1 - self.timeInterval.tstart))

            print("Nobs: %s, Npred: %s" % (nobs, npred))
            if (npred <= 0):
                if (nobs == 1):
                    sys.stderr.write("WARNING: simulation got npred 0 when nobs=1, setting it to 1e-5")
                    npred = 1e-5
                elif (nobs > 1):
                    raise ltfException(
                        "Zero or negative npred (%s) while observed are %s for region centered in %s,%s in time interval %s - %s" % (
                        npred, nobs, self.ra, self.dec, t1, t2))

            if (nobs < int(configuration.get("Analysis", "Min_counts"))):
                sys.stderr.write(
                    "WARNING: too few counts (%s) in interval %.3f-%.3f (npred = %s)" % (nobs, t1, t2, npred))

                continue

            if (tt2 - tt1 < 1e-6):
                sys.stderr.write("Interval too short in region %s,%s" % (self.ra, self.dec))
                sys.stderr.write("Results from BB were: %s" % (res))
            pass

            thisTimeInterval = TimeInterval(tt1,
                                            tt2,
                                            self.timeInterval.ft1,
                                            self.timeInterval.ft2,
                                            self.timeInterval.simft1)
            self.excesses.append(Excess(self.ra, self.dec, self.rad, self.analysisDef, thisTimeInterval))

            # Now set nobs and npred, and compute the probability
            self.excesses[-1].setNpred(npred)
            self.excesses[-1].setNobs(nobs)
            self.excesses[-1].computeProbability()

        print("Found %s intervals" % (len(self.excesses)))
        return self.excesses


def plotFitsCountsmap(fitsfile, title=''):
    image = aplpy.FITSFigure(fitsfile,
                             convention='calabretta',
                             figsize=(3, 3))
    image.set_theme('publication')
    image.tick_labels.set_xformat('ddd.d')
    image.tick_labels.set_yformat('ddd.d')
    image.add_grid()
    image.set_grid_xspacing(5.0)
    image.set_tick_xspacing(5.0)
    image.set_grid_yspacing(5.0)
    image.set_tick_yspacing(5.0)
    image.axis_labels.set_xtext('Right Ascension (J2000)')
    image.axis_labels.set_ytext('Declination (J2000)')
    image.axis_labels.show()
    image.show_colorscale(cmap='gist_heat', vmin=0.1, vmax=2, stretch='log')
    image._figure.suptitle(title)
    return image


pass


def haversine(x1, x2):
    d = getAngularDistance(x1[0], x1[1], x2[0], x2[1])
    return d


def getClusteringAlgorithm(algorithm):
    if (algorithm == "dbscan"):
        return Dbscan()
    else:
        raise NotImplemented("Clustering algorithm %s is not implemented" % (algorithm))
    pass


pass


class ClusteringAlgorithm(object):
    def _go(self):
        raise NotImplemented("You have to override this")

    def getClusters(self, ras, decs, energies):
        self._go(ras, decs, energies)
        return self.clusters

    def plot(self):
        pass


pass


class Dbscan(ClusteringAlgorithm):
    def __init__(self):
        self.dbscan = sklearn.cluster.DBSCAN(metric=haversine)

    def _go(self, ras, decs, energies):

        # Prepare data
        X = numpy.zeros([ras.shape[0], 2])
        X[:, 0] = ras
        X[:, 1] = decs

        # Run dbscan
        res = self.dbscan.fit_predict(X)

        # Now create the clusters
        self.clusters = []

        unique = set(res)

        for un in unique:

            idx = res == un

            if (un >= 0):
                n = numpy.sum(idx)
                thisCluster = numpy.zeros(n, dtype=[('RA', float), ('DEC', float), ('Energy', float)])
                thisCluster['RA'] = X[idx, 0]
                thisCluster['DEC'] = X[idx, 1]
                thisCluster['Energy'] = energies[idx]
                self.clusters.append(thisCluster)
            pass
        pass

    pass


pass


def getBoundingCoordinates(lon, lat, radius):
    '''
    Finds the smallest "rectangle" which contains the given Region Of Interest.
    It returns lat_min, lat_max, dec_min, dec_max. If a point has latitude
    within lat_min and lat_max, and longitude within dec_min and dec_max,
    it is possibly contained in the ROI. Otherwise, it is certainly NOT
    within the ROI.
    '''
    radLat = numpy.deg2rad(lat)
    radLon = numpy.deg2rad(lon)

    radDist = numpy.deg2rad(radius)

    minLat = radLat - radDist
    maxLat = radLat + radDist

    MIN_LAT = numpy.deg2rad(-90.0)
    MAX_LAT = numpy.deg2rad(90.0)
    MIN_LON = numpy.deg2rad(-180.0)
    MAX_LON = numpy.deg2rad(180.0)

    if (minLat > MIN_LAT and maxLat < MAX_LAT):
        deltaLon = numpy.arcsin(numpy.sin(radDist) / numpy.cos(radLat))

        minLon = radLon - deltaLon
        maxLon = radLon + deltaLon

        if (minLon < MIN_LON):
            minLon += 2.0 * numpy.pi
        if (maxLon > MAX_LON):
            maxLon -= 2.0 * numpy.pi

        # In FITS files the convention is to have longitude from 0 to 360, instead of
        # -180,180. Correct this
        if (minLon < 0):
            minLon += 2.0 * numpy.pi
        if (maxLon < 0):
            maxLon += 2.0 * numpy.pi
    else:
        # A pole is within the ROI
        minLat = max(minLat, MIN_LAT)
        maxLat = min(maxLat, MAX_LAT)
        minLon = 0
        maxLon = 360.0
    pass

    # Inversion can happen due to boundaries, so make sure min and max are right
    minLatf, maxLatf = min(minLat, maxLat), max(minLat, maxLat)
    minLonf, maxLonf = min(minLon, maxLon), max(minLon, maxLon)

    return numpy.rad2deg(minLonf), numpy.rad2deg(maxLonf), numpy.rad2deg(minLatf), numpy.rad2deg(maxLatf)


pass
