#!/usr/bin/env python
import argparse
import datetime
import time

from fermi_blind_search.date2met_converter import convert_date
from fermi_blind_search.data_files import get_data_file_path
from fermi_blind_search.configuration import get_config
from GtBurst import IRFS
import GtApp


def computeSpread(points):
    from GtBurst.angularDistance import getAngularDistance
    minD = []
    for r, d in points:
        distances = getAngularDistance(r, d, points[:, 0], points[:, 1])
        minD.append(distances[distances > 0].min())
    return max(minD) - min(minD), numpy.median(minD)


if __name__ == '__main__':

    clockstart = time.time()

    parser = argparse.ArgumentParser(description='Run the LAT Transient Factory.')

    parser.add_argument('--date', help='''Start date in ISO format. Ex: "2010-12-31 23:53:25.2", or
                        "2010-12-31T23:53:25.2"''', type=str, required=True)
    parser.add_argument('--duration', help='Time window duration (in seconds)', type=float, required=True)
    # parser.add_argument('--irfs', help='Instrument Response Function to use', type=str,
    #                     required=False, default='P7REP_SOURCE_V15')
    # parser.add_argument('--probability',
    #                     help='Null hyp. probability for the excesses. Default: 6.33e-05 (i.e., 5 sigma)',
    #                     default=6.33e-05, required=False, type=float)
    parser.add_argument('--loglevel', help='''Logging level: DEBUG (very verbose) or INFO (normal).
                                           Note that this will not change the verbosity of the logfile,
                                           which is controlled by the logging.yaml configuration file.''',
                        required=False, choices=['DEBUG', 'INFO', 'debug', 'info'], default='INFO')
    parser.add_argument('--logfile', help='Filename for the log', required=False, default='ltfsearch.log')
    parser.add_argument('--workdir', help='Move to workdir before doing anything', default='.',
                        required=False)
    parser.add_argument('--outfile', help='Filename for the output. Use this if you do not want to use the database',
                        required=False, default=None)
    parser.add_argument('--ft1', help='User-provided ft1 file (default: download from data catalog at Stanford)',
                        required=False, default=None)
    parser.add_argument('--ft2', help='User-provided ft2 file (default: download from data catalog at Stanford)',
                        required=False, default=None)
    parser.add_argument('--config', help="Path to configuration file", type=get_config, required=True)

    args = parser.parse_args()

    import os
    import dateutil
    from fermi_blind_search import myLogging, ltf
    from fermi_blind_search.ltfException import ltfException
    import numpy
    import yaml
    import sys

    from fermi_blind_search.fits_handling.fits_interface import pyfits
    from fermi_blind_search import ltf

    if (args.workdir != '.'):
        os.chdir(args.workdir)

    # Set up the logger
    path = get_data_file_path('logging.yaml')

    if os.path.exists(path):

        with open(path, 'rt') as f:

            config = yaml.load(f.read())

        pass

        # Now overwrite the loglevel for the console
        config['handlers']['console']['level'] = args.loglevel.upper()

        # Overwrite the filename for the log file
        config['handlers']['mplog']['name'] = args.logfile

        myLogging.logconfig.dictConfig(config)
    else:
        raise RuntimeError("Could not find the logging configuration file %s" % (path))

    logger = myLogging.log.getLogger("ltfsearch")

    # Now overwrite stdout and stderr so they will go to the logger
    sl = myLogging.StreamToLogger(logger, myLogging.log.DEBUG)
    sys.stdout = sl

    sl = myLogging.StreamToLogger(logger, myLogging.log.ERROR)
    sys.stderr = sl

    logger.debug("Arguments: %s" % (args.__dict__))

    if args.ft1 is None:

        # This is available on galprop-cluster

        from myDataCatalog import mdcget

        # Download files

        met_start = convert_date(args.date)
        met_stop = met_start + args.duration

        logger.info("Running search starting at %s (MET: %s) for %s seconds" % (args.date, met_start, args.duration))

        # Get the data
        logger.info("######################")
        logger.info("Getting data")
        logger.info("######################")


        class Container(object):
            pass


        mdargs = Container()
        mdargs.met_start = met_start - 10000.0
        mdargs.met_stop = met_stop + 10000.0
        mdargs.type = None
        mdargs.outroot = 'data'
        mdargs.gtselect_pars = None

        logger.info("Obtaining data...")
        ft1file, ft2file = mdcget.getData(mdargs)
        logger.info("done")

    else:

        # Using provided data

        # with pyfits.open(args.ft1) as f:
        #
        #     met_start = f['EVENTS'].header.get("TSTART")
        #     met_stop = f['EVENTS'].header.get("TSTOP")

        try:
            met_start = float(args.date)

        except:

            met_start = convert_date(args.date)

        met_stop = met_start + args.duration

        ft1file = os.path.abspath(os.path.expandvars(os.path.expanduser(args.ft1)))
        ft2file = os.path.abspath(os.path.expandvars(os.path.expanduser(args.ft2)))

    #  #Strip version name
    configuration = args.config

    irf = configuration.get("Analysis", "irf")

    gtburstIrf = "_".join(irf.split("_")[:-1]).replace("P8R2", "P8")

    # Make a gtselect selecting the requested IRF
    cleaned_ft1 = "__cleaned_ft1.fits"

    gtselect_args = {'infile': ft1file,
                     'outfile': cleaned_ft1,
                     'ra': 0.0,
                     'dec': 0.0,
                     'rad': 180.0,
                     'tmin': met_start,
                     'tmax': met_stop,
                     'emin': configuration.get("Analysis", "emin"),
                     'emax': configuration.get("Analysis", "emax"),
                     'zmin': 0.0,
                     'zmax': 180.0,
                     'evclass': IRFS.IRFS[gtburstIrf].evclass,
                     'evtype': 'INDEF',
                     'clobber': 'yes'}
    logger.info("Preselecting events belonging to IRF %s..." % gtburstIrf)
    GtApp.GtApp('gtselect').run(**gtselect_args)

    # Get number of cpus to use

    ncpus = int(configuration.get("Hardware", "ncpus"))

    logger.info("######################")
    logger.info("Bayesian Blocks stage")
    logger.info("######################")

    logger.info("Loading grid...")

    gridFile = get_data_file_path('grid.fits')

    try:
        data = pyfits.getdata(gridFile, 1)
    except:
        raise ltfException("Could not read the file with the grid definition (%s)" % (gridFile))

    ras = data.field("RA")
    decs = data.field("DEC")

    spread, medianDistance = computeSpread(numpy.vstack([ras, decs]).T)

    # idx = (numpy.abs(ras - 174.450) < 1) & (numpy.abs(decs-73.5) < 1)
    # ras = ras[idx]
    # decs = decs[idx]
    # ras = numpy.array([275.072875977])
    # decs = numpy.array([-23.3751621246])

    logger.info("Found a grid of %s points, with median angular distance of %s deg and a spread of %s deg" % (
        ras.shape[0], medianDistance, spread))

    analysisDefinition = ltf.AnalysisDefinition(gtburstIrf.lower(),
                                                configuration.get('Analysis', 'zenith_cut'),
                                                configuration.get('Analysis', 'theta_cut'),
                                                configuration.get('Analysis', 'emin'),
                                                configuration.get('Analysis', 'emax'))

    timeInterval = ltf.TimeInterval(met_start,
                                    met_start + args.duration,
                                    cleaned_ft1,
                                    ft2file,
                                    simft1=None)

    # Null-hyp probability for Bayesian Blocks
    nullp = float(configuration.get("Analysis","nullp"))

    ltf = ltf.AllSkySearch(ras,
                           decs,
                           medianDistance + spread,
                           timeInterval,
                           analysisDefinition,
                           nullp,
                           cpus=ncpus)

    logger.info("Searching for excesses in %s regions with %s CPUs..." % (ras.shape[0], ncpus))

    interestingIntervals, figs = ltf.go(prepare_figures=True)

    for i in range(len(figs)):
        figs[i].savefig("img_%s" % i)

    logger.info("done")
    logger.info("Excluded %s single intervals because their duration is longer than the maximum one (%s s)" % (
        ltf.getExcludedBecauseOfDuration(),
        configuration.get('Analysis', "Max_duration")))

    logger.info("Saving %s interesting intervals..." % (len(interestingIntervals)))

    if args.outfile is None:

        # Save in database

        ltf.save()

    else:

        ltf.save_to_file(args.outfile)

    logger.info("done")

    logger.info("Finished")
    clockstop = time.time()
    delta = clockstop - clockstart

    logger.info("Execution time: %s (h:m:s)" % (str(datetime.timedelta(seconds=delta))))
