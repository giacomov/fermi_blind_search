import bisect
import glob
import sys

import numpy
import os
import re
import scipy.interpolate

try:

    import astropy.io.fits as pyfits

except:

    import pyfits

import matplotlib.pyplot as plt

from fermi_blind_search.bkge.angular_distance import getAngularDistance
from fermi_blind_search.Configuration import configuration
from fermi_blind_search.data_files import get_data_file_path


class myFT1File(object):
    def __init__(self, ft1):

        with pyfits.open(ft1) as f:
            self.time = f['EVENTS'].data.field("TIME")

            self.tstart = float(f['EVENTS'].header.get("TSTART"))
            self.tstop = float(f['EVENTS'].header.get("TSTOP"))

            # Read the GTIs
            nGTIs = f['GTI'].data.field("START").shape[0]

            self.gtis = numpy.zeros(nGTIs,
                                    dtype=[('start', float), ('stop', float)])

            self.gtis['start'] = f['GTI'].data.field("START")
            self.gtis['stop'] = f['GTI'].data.field("STOP")

            # Read the ROI
            header = f['EVENTS'].header
            dskeys = filter(lambda x: x.startswith("DSVAL"), header.keys())

            # Get the key for the CIRCLE(ra,dec,radius) instruction
            roikey = filter(lambda x: header[x].upper().startswith("CIRCLE"), dskeys)

            if (len(roikey) == 0):
                raise RuntimeError("Provided ft1 file does not contain a ROI definition")

            # This is a string like 'CIRCLE(-234.25,+4.7,7.2)'
            circleDef = header[roikey[0]]

            # Extract RA,Dec and radius
            self.ra, self.dec, self.rad = map(lambda x: float(x),
                                              re.findall(
                                                  'CIRCLE\(([-,+]?[0-9\.]+),([-,+]?[0-9\.]+),([0-9\.]+)\)',
                                                  circleDef, re.IGNORECASE)[0])

    def inGTIs(self, time):

        idx = (self.gtis['start'] <= time) & (self.gtis['stop'] > time)

        n = numpy.sum(idx)

        if (n == 1):

            # In one GTI
            return True

        elif (n == 0):

            # In no GTI
            return False

        else:

            raise RuntimeError("This is a bug. Provided time is in more than 1 GTI...")

    def iterateOverGTIs(self, start=None, stop=None):

        if start is not None and stop is not None:

            # Sub-select the GTIs

            idx = (self.gtis['stop'] >= start) & (self.gtis['start'] < stop)

            gtis = self.gtis[idx]

        else:

            gtis = self.gtis

        for t1, t2 in zip(gtis['start'], gtis['stop']):

            yield (t1, t2)

    def getNumberOfEvents(self, start=None, stop=None):

        if start is not None and stop is not None:

            # Sub-select the GTIs

            idx = (self.time >= start) & (self.time < stop)

            return numpy.sum(idx)

        else:

            return self.time.shape[0]


class myFT2File(object):
    def __init__(self, ft2file):

        # Open the FT2 file

        with pyfits.open(ft2file) as f:

            self.start = f['SC_DATA'].data.field("START")
            self.stop = f['SC_DATA'].data.field("STOP")

            ra_scz = f['SC_DATA'].data.field("RA_SCZ")
            dec_scz = f['SC_DATA'].data.field("DEC_SCZ")

        self.ra_interpolator = scipy.interpolate.InterpolatedUnivariateSpline(
            self.start, ra_scz, k=3)
        self.dec_interpolator = scipy.interpolate.InterpolatedUnivariateSpline(
            self.start, dec_scz, k=3)

    def getPointing(self, time):
        return (self.ra_interpolator(time), self.dec_interpolator(time))

    def getStartTimes(self):
        return self.start

    def getStopTimes(self):
        return self.stop


# class TimeDependentExposure(object):
#
#     def __init__(self, ft2file, ft1file, dcostheta=0.1):
#
#         self.ft1 = myFT1File(ft1file)
#
#         self.ft2 = myFT2File(ft2file)
#
#         # Now compute how many exposures I need to compute
#         _changePoints = []
#
#         # The first changePoints is the tstart of the ft1
#         _changePoints.append(self.ft1.tstart)
#         raz_prev, decz_prev = self.ft2.getPointing(_changePoints[0])
#         offaxis_prev = angularDistance.getAngularDistance(self.ft1.ra, self.ft1.dec,
#                                                           raz_prev, decz_prev)
#         cos_prev = math.cos(numpy.deg2rad(offaxis_prev))
#
#         ft2EntriesTimes = self.ft2.getStartTimes()
#         idx = (ft2EntriesTimes >= self.ft1.tstart)
#
#         for t in ft2EntriesTimes[idx]:
#
#             # Get the cos of the off-axis angle
#             raz, decz = self.ft2.getPointing(t)
#             offaxis = angularDistance.getAngularDistance(self.ft1.ra, self.ft1.dec,
#                                                          raz, decz)
#             if (offaxis >= 70.0):
#                 # Outside the FOV!
#                 continue
#
#             cos = math.cos(numpy.deg2rad(offaxis))
#
#             # Get the delta cos with respect to the previous change point
#             deltaCos = abs(cos - cos_prev)
#
#             if (deltaCos >= dcostheta):
#
#                 # Accept this as a change point
#                 _changePoints.append(t)
#                 cos_prev = cos
#
#             else:
#
#                 continue
#
#         # Filter out all changePoints not contained in GTIs
#         changePoints = []
#
#         for change in _changePoints:
#
#             # Find start time of closest GTI
#             idx = (self.ft1.gtis['start'] >= change)
#
#             if (numpy.sum(idx) == 0):
#                 # After last GTI
#                 continue
#
#             thisStart = self.ft1.gtis['start'][idx][0]
#
#             thisStop = self.ft1.gtis['stop'][idx][0]
#
#             if (thisStop >= change):
#                 # This change points is inside a GTI, keep it
#                 changePoints.append(change)
#
#         # Now add all the start and stop times of the GTIs, so that we
#         # always finish each GTI with an exposure computation (to avoid
#         # extrapolation madness)
#         changePoints.extend(self.ft1.gtis['start'])
#         changePoints.extend(self.ft1.gtis['stop'])
#
#         self.changePoints = numpy.unique(numpy.asarray(changePoints))
#         self.changePoints.sort()
#
#         print("Found %s change points" % (self.changePoints.shape[0]))


######################
######################
######################
######################

def countsInInterval(t, t1, t2):
    # Find leftmost item greater than or equal to start[i]

    firstElementInInterval = bisect.bisect_left(t, t1)

    # Find rightmost value less than or equal to tstop

    lastElementInInterval = bisect.bisect_right(t, t2) - 1

    return firstElementInInterval, lastElementInInterval, lastElementInInterval - firstElementInInterval + 1


def get_theta_lookup_file(ra, dec):

    root_for_interpolator = "ra%.3f-dec%.3f_rateForInterpolator" % (ra, dec)

    path = get_data_file_path('ROIBackgroundEstimator_data')

    return os.path.join(path, '%s.npz' % root_for_interpolator)


class ROIBackgroundEstimatorDataMaker(object):
    def __init__(self, ft1file, ft2file):

        self.ft1 = myFT1File(ft1file)

        with pyfits.open(ft2file) as f:

            ft2data = f['SC_DATA'].data

            start = ft2data.field("START")
            stop = ft2data.field("STOP")

            # Check that Ft2 covers ft1
            if (start[0] >= self.ft1.tstart):
                raise RuntimeError("Provided FT2 file does not cover FT1 interval")

            # Throw away all part of the Ft2 which are useless
            idx = (ft2data.field("START") >= self.ft1.tstart) & (ft2data.field("STOP") < self.ft1.tstop)
            # idx = (ft2data.field("START") >= self.ft1.tstart) & (ft2data.field("STOP") < (self.ft1.tstart + 100*86400.0))

            start = start[idx]
            stop = stop[idx]
            ra_scx = ft2data.field("RA_SCX")[idx]
            dec_scx = ft2data.field("DEC_SCX")[idx]
            ra_scz = ft2data.field("RA_SCZ")[idx]
            dec_scz = ft2data.field("DEC_SCZ")[idx]
            ft2livetime = ft2data.field("LIVETIME")[idx]

            # Now make sure that the FT2 file is time-ordered

            idx = numpy.argsort(start)

            start = start[idx]
            stop = stop[idx]
            ra_scx = ra_scx[idx]
            dec_scx = dec_scx[idx]
            ra_scz = ra_scz[idx]
            dec_scz = dec_scz[idx]
            ft2livetime = ft2livetime[idx]

        print("Covering time interval %s - %s" % (start.min(), start.max()))

        nEntries = start.shape[0]

        self.theta = numpy.zeros(nEntries, dtype=numpy.float16)
        # self.phi = numpy.zeros(nEntries)
        self.livetime = numpy.zeros(nEntries, dtype=numpy.float32)
        self.counts = numpy.zeros(nEntries, dtype=numpy.int16)

        t = numpy.array(self.ft1.time, copy=True)

        t.sort()

        idx = (t >= start[0]) & (t <= stop[-1])

        t = list(t[idx])

        nEvents = len(t)

        sys.stdout.write("\nFound %s events within the FT2 boundaries\n" % nEvents)

        root = ".".join(os.path.basename(ft1file).split(".")[:-1])

        lookup_table_file = '%s_lookup.npz' % root

        if os.path.exists(lookup_table_file):

            sys.stdout.write("Reading data space (theta,phi,counts) from %s...\n" % lookup_table_file)

            npzfile = numpy.load(lookup_table_file)

            self.theta = npzfile['theta']
            # self.phi = npzfile['phi']
            self.counts = npzfile['counts']
            self.livetime = npzfile['livetime']

            del npzfile

        else:
            sys.stdout.write("File %s does not exists\n" % lookup_table_file)
            sys.stdout.write("Filling data space (theta,phi,counts)...\n")

            sys.stdout.write("(processing %s entries)\n" % (nEntries))

            self.theta = getAngularDistance(ra_scz, dec_scz, self.ft1.ra, self.ft1.dec)

            # self.theta = getTheta(ra_scz, dec_scz, self.ft1.ra,self.ft1.dec)
            self.counts = numpy.array(map(lambda (t1, t2): countsInInterval(t, t1, t2)[-1], zip(start, stop)))

            self.livetime[:] = ft2livetime[:]

            # for i in range(nEntries):

            # thetaPhi = getThetaPhi(ra_scx[i],dec_scx[i],ra_scz[i],dec_scz[i],self.ft1.ra,self.ft1.dec)
            # self.theta[i] = thetaPhi[0]
            # self.phi[i] = thetaPhi[1]

            #    i1,i2,n = countsInInterval(t,start[i],stop[i])

            #    self.counts[i] = n
            #    self.livetime[i] = ft2livetime[i]

            #    if(i > 0 and i % 1000 == 0):
            #        sys.stdout.write("\r%.2f percent completed" % (float(i)/start.shape[0]*100.0)) 

            sys.stdout.write("\r100 percent completed    \n")

            if numpy.sum(self.counts) != nEvents:
                print("ARGH")
                import pdb;
                pdb.set_trace()

            numpy.savez(lookup_table_file, theta=self.theta,
                        # phi=self.phi,
                        counts=self.counts,
                        livetime=self.livetime)

    def makeThetaHistogram(self, **kwargs):

        # Freedman-Diaconis rule for the bin size (why not?)

        # iqr = numpy.diff(numpy.percentile(numpy.cos(numpy.deg2rad(self.theta)), [25, 75]))

        # binsize = 2 * iqr * pow(self.theta.shape[0], -1/3.0)

        # nTheta = int(numpy.ceil(1.0 / binsize))

        # print("Number of bins selected with the Freedman-Diaconis rule: %s" % (nTheta))

        binsize = 0.025
        nTheta = 40

        print("Using binsize = %s deg (number of theta bins: %s)" % (binsize, nTheta))

        k = 2
        s = nTheta / 1.5
        phimin = 0
        phimax = 360
        interpolate = True
        errors = True

        for key, val in kwargs.iteritems():

            if key.lower() == 'binsize':
                binsize = val

                nTheta = int(numpy.ceil(1.0 / binsize))

                print("User-defined binsize: %s (%s bins)" % (binsize, nTheta))

                s = nTheta / 1.5

            if (key.lower() == "phimin"):
                phimin = float(val)

            if (key.lower() == "phimax"):
                phimax = float(val)

            if (key.lower() == "k"):
                k = int(val)

            if (key.lower() == "s"):
                s = int(val)

            if (key.lower() == "interpolate"):
                interpolate = bool(val)

            if (key.lower() == "errors"):
                errors = bool(val)

        cosbins = numpy.linspace(numpy.cos(numpy.deg2rad(75)), 1, nTheta + 1)[::-1]
        thetaBins = numpy.rad2deg(numpy.arccos(cosbins))

        print(thetaBins)

        cc = numpy.zeros(nTheta)
        cce = numpy.zeros(nTheta)
        livetime = numpy.zeros(nTheta)

        for i, th1, th2 in zip(range(nTheta), thetaBins[:-1], thetaBins[1:]):
            idx = (
                ((self.theta >= th1) & (self.theta < th2))
                # & ( (self.phi >= phimin) & (self.phi < phimax)  )
            )
            totC = numpy.sum(self.counts[idx])

            livetime[i] = numpy.sum(self.livetime[idx])
            cc[i] = totC
            cce[i] = 1 + numpy.sqrt(totC + 0.75)

        rate = cc / livetime
        rateErr = cce / livetime

        idx = numpy.isnan(rate)
        rate[idx] = 0.0
        idx = numpy.isnan(rateErr)
        rateErr[idx] = 0.0

        width = thetaBins[1:] - thetaBins[:-1]
        center = (thetaBins[:-1] + thetaBins[1:]) / 2

        # rate = rate / width
        # rateErr = rateErr / width

        fig = plt.figure()
        sub = fig.add_subplot(111)

        sub.set_xlabel("Off-axis angle (deg)")
        sub.set_ylabel("Rate (photons/s)")

        if (errors):

            plt.bar(center, rate, align='center', width=width, yerr=rateErr, alpha=0.5, lw=0)

        else:

            plt.bar(center, rate, align='center', width=width, alpha=0.5, lw=0)

        if (interpolate):
            # Polynomial interpolation
            # Add one point at the beginning to avoid Runge phenomenon at
            # theta = 0
            xi = numpy.insert(center, 0, 0.0)
            yi = numpy.insert(rate, 0, rate[0])
            wi = numpy.insert(rateErr, 0, rateErr[0])

            # Add one point at the end for the same reason
            xi = numpy.append(xi, 80.0)
            yi = numpy.append(yi, 0.0)
            wi = numpy.append(wi, wi[0])

            # Save interpolator points

            rate_lookup_table_file = get_theta_lookup_file(self.ft1.ra, self.ft1.dec)

            numpy.savez(rate_lookup_table_file, rate=yi, theta=xi, weights=1.0 / wi, k=k, s=s)

            self.rateInterpolator = scipy.interpolate.UnivariateSpline(xi, yi, w=1.0 / wi, k=k, s=s, check_finite=True)

            xx = numpy.linspace(0, 80, 100)
            yy = self.rateInterpolator(xx)

            plt.plot(xx, yy)
            plt.ylim([0, max(yi) * 1.1])

            image_file = os.path.join(get_data_file_path('ROIBackgroundEstimator_data'),
                                      rate_lookup_table_file.replace("npz", "png"))

            fig.savefig(image_file)

        return thetaBins, rate, rateErr, fig, sub


# def makeThetaPhiHistogram(self, nTheta, nPhi,**kwargs):
#        
#        cosbins = numpy.linspace(numpy.cos(numpy.deg2rad(75)),1,nTheta+1)[::-1]
#        thetaBins = numpy.rad2deg(numpy.arccos(cosbins))
#        
#        phiBins = numpy.linspace(0,360,nPhi+1)
#        
#        cc = []
#        cce = []
#        
#        for ph1,ph2 in zip(phiBins[:-1],phiBins[1:]):
#            
#            thisRow = []
#            thisLivetime = []
#            
#            for th1,th2 in zip(thetaBins[:-1],thetaBins[1:]):
#                
#                idx = (self.theta >= th1) & (self.theta < th2) & (self.phi >= ph1) & (self.phi < ph2)
#                
#                totC = numpy.sum(self.counts[idx])
#                thisRow.append(totC )
#                thisLivetime.append(numpy.sum(self.livetime[idx]))
#                #print("%s <= theta < %s, %s <= phi < %s -> %s" %(th1,th2,ph1,ph2,totC))
#            
#            cc.append(numpy.array(thisRow) / numpy.array(thisLivetime))
#            cce.append(numpy.sqrt(numpy.array(thisRow)) / numpy.array(thisLivetime))
#        
#        cc = numpy.asarray(cc)
#        cce = numpy.asarray(cce)
#        
#        idx = numpy.isnan(cc)
#        cc[idx] = 0
#        cce[idx] = 0
#                
#        fig, sub = plt.subplots(nrows=1,ncols=1,subplot_kw=dict(polar=True))
#        sub.pcolormesh(phiBins *numpy.pi/180.0, thetaBins,cc.T,**kwargs)
#        PCM = sub.get_children()[2] #get the mappable, the 1st and the 2nd are the x and y axes
#        plt.colorbar(PCM, ax=sub)
#        
#        return fig,sub

class ROIBackgroundEstimator(object):

    def __init__(self, dataFt1, dataFt2):

        self.dataFt1 = myFT1File(dataFt1)

        with pyfits.open(dataFt2) as f:

            ft2data = f['SC_DATA'].data

            start = ft2data.field("START")
            stop = ft2data.field("STOP")

            # Check that Ft2 covers ft1
            if (start[0] > self.dataFt1.tstart):
                raise RuntimeError("Provided FT2 file does not cover FT1 interval")

            # Throw away all parts of the Ft2 which are useless
            idx = (ft2data.field("STOP") >= self.dataFt1.tstart- 100.0) & \
                  (ft2data.field("START") < self.dataFt1.tstop + 100.0)

            start = start[idx]
            stop = stop[idx]

            # ra_scx = ft2data.field("RA_SCX")[idx]
            # dec_scx = ft2data.field("DEC_SCX")[idx]

            ra_scz = ft2data.field("RA_SCZ")[idx]
            dec_scz = ft2data.field("DEC_SCZ")[idx]

            ft2livetime = ft2data.field("LIVETIME")[idx]

        # Now make sure that the FT2 file is time-ordered

        idx = numpy.argsort(start)

        start = start[idx]
        stop = stop[idx]

        # ra_scx = ra_scx[idx]
        # dec_scx = dec_scx[idx]

        ra_scz = ra_scz[idx]
        dec_scz = dec_scz[idx]

        ft2livetime = ft2livetime[idx]

        self.livetimeFraction = ft2livetime / (stop - start)

        self.ft2_start = start

        self.dataTheta = getAngularDistance(ra_scz, dec_scz, self.dataFt1.ra, self.dataFt1.dec)

        # Fix the pole and antipode for which the haversine formula is unstable

        idx = numpy.isnan(self.dataTheta)

        self.dataTheta[idx] = 180.0

        print("Covering time interval %s - %s" % (start.min(), start.max()))

        lookup_table_file = get_theta_lookup_file(self.dataFt1.ra, self.dataFt1.dec)

        # This is to cope with the fact that sometimes (I don't know why) the name of the
        # file is slightly different

        if not os.path.exists(lookup_table_file):
            # Try with a slightly different RA

            ra = float(os.path.basename(lookup_table_file).split("-")[0].replace("ra", "")[:-2])

            other_tokens = "-".join(os.path.basename(lookup_table_file).split("-")[1:])

            search_expr = os.path.join(get_data_file_path('ROIBackgroundEstimator_data'),
                                       'ra%s*%s' % (ra, other_tokens))

            files_ = glob.glob(search_expr)

            if len(files_)==0:

                raise RuntimeError("Could not find data files for background estimation (%s)" % (search_expr))

            else:

                lookup_table_file = files_[0]

        if os.path.exists(lookup_table_file):

            sys.stdout.write("Reading theta histogram from %s...\n" % lookup_table_file)

            npzfile = numpy.load(lookup_table_file)

            # Rate as function of theta

            self.sim_theta = npzfile['theta']
            self.sim_rate = npzfile['rate']
            self.sim_weights = npzfile['weights']
            self.k = npzfile['k']
            self.s = npzfile['s']

            del npzfile

            # Now make sure there are no infinite weight

            idx = numpy.isfinite(self.sim_weights)

            self.sim_theta = self.sim_theta[idx]
            self.sim_weights = self.sim_weights[idx]
            self.sim_rate = self.sim_rate[idx]

        else:

            raise IOError("Cannot find lookup table %s" % (lookup_table_file))

        # Now prepare the interpolators

        # Rate from the simulations

        self.rateInterpolator = scipy.interpolate.UnivariateSpline(self.sim_theta, self.sim_rate,
                                                                   w=self.sim_weights, k=self.k, s=self.s)

        # Theta from the data

        self.dataThetaInterpolator = scipy.interpolate.InterpolatedUnivariateSpline(
            start, self.dataTheta, k=3)

        # Livetime from the data

        self.dataLivetimeFractionInterpolator = scipy.interpolate.InterpolatedUnivariateSpline(
            start, self.livetimeFraction, k=1)

        # Check that all interpolations have gone fine

        if numpy.sum(numpy.isnan(self.rateInterpolator.get_coeffs())) > 0:
            raise RuntimeError("Rate interpolation failed using %s\n" % lookup_table_file)

        if numpy.sum(numpy.isnan(self.dataThetaInterpolator.get_coeffs())) > 0:
            raise RuntimeError("Theta interpolation for data for %s failed!\n" % dataFt1)

        if numpy.sum(numpy.isnan(self.dataLivetimeFractionInterpolator.get_coeffs())) > 0:
            raise RuntimeError("Livetime fraction interpolation for data for %s failed!\n" % dataFt2)

    def getExpectedRate(self, t1=None, t2=None, binsize=1.0):

        if (t1 == None or t2 == None):

            t1 = self.dataFt1.tstart
            t2 = self.dataFt1.tstop

        # Generate the grid iterating over the GTIs

        times = []
        lc = []

        for gti_t1, gti_t2 in self.dataFt1.iterateOverGTIs(t1, t2):

            # Generate grid for this GTI
            
            # Pad the end of the GTI so that it will never happen that we have
            # events between the last bin and the end of the GTI where the
            # predicted rate is 0 due to the SAA
            
            padded_gti_t2 = gti_t2 - 0.2
            
            # Modify the binsize so we end always exactly at the end of the padded GTI
            
            nbins = int(numpy.ceil((padded_gti_t2 - gti_t1) / binsize))

            this_times = numpy.linspace(gti_t1, padded_gti_t2, nbins)

            this_lc = numpy.zeros_like(this_times)

            for i, t in enumerate(this_times):

                theta = self.dataThetaInterpolator(t)

                if theta > 80:

                    raise RuntimeError("You have to cut your data with gtmktime and a theta cut of 65 at most!")

                else:

                    this_lc[i] = self.rateInterpolator(theta) * self.dataLivetimeFractionInterpolator(t)

            # Add a zero before the first bin of this GTI, so
            # between GTIs the interpolation will be zero

            times.append(gti_t1 - 1e-3)
            lc.append(0.0)

            # Add these bins

            times.extend(this_times)
            lc.extend(this_lc)

            # Add another zero after these bins, so
            # between GTIs the interpolation will be zero
                        
            times.append(gti_t2)
            lc.append(0.0)

        return numpy.array(times), numpy.array(lc)

    def getIntegralDistribution(self, t0, t1=None, t2=None):

        # Get the predicted light curve

        tt, lc = self.getExpectedRate(t1, t2)
        
        # Remove time offset

        tt = tt - t0

        # Make the integral distribution

        # n_obs = self.dataFt1.getNumberOfEvents(t1, t2)

        int_distr_points = numpy.cumsum(lc)  # / numpy.sum(lc) * n_obs

        # Build a linear spline interpolating the integral distribution,
        # which is very fast to evaluate on any given x

        # We use ext=3, which according to the scipy documentation means
        # that any backward extrapolation will return the first value (0),
        # and any forward extrapolation will return the last value (nobs)

        self.intDistr = scipy.interpolate.InterpolatedUnivariateSpline(tt, int_distr_points, k=1, ext=3)

        return self.intDistr


# def getTheta(ra_scz, dec_scz, ra, dec):
#    
#    v0 = getVector(ra,dec)
#    vzs = getVectors(ra_scz, dec_scz)
#        
#    theta = numpy.rad2deg(angle(v0, vzs))
#        
#    return theta
#
# def getVector(ra,dec):
#  
#  ra1                         = numpy.deg2rad(ra)
#  dec1                        = numpy.deg2rad(dec)
#  
#  cd                          = numpy.cos(dec1)
#  
#  xs = numpy.cos(ra1) * cd
#  ys = numpy.sin(ra1) * cd
#  zs = numpy.sin(dec1)
#  
#  return [xs,ys,zs]  
#
# def getVectors(ra,dec):
#  
#  ra1                         = numpy.deg2rad(ra)
#  dec1                        = numpy.deg2rad(dec)
#  
#  cd                          = numpy.cos(dec1)
#  
#  xs = numpy.cos(ra1) * cd
#  ys = numpy.sin(ra1) * cd
#  zs = numpy.sin(dec1)
#  
#  return numpy.vstack([xs,ys,zs]).T
#
# def angle(ref, b):
#    
#    def getNorm(v):
#        
#        return math.sqrt(pow(v[0],2) + pow(v[1],2) + pow(v[2],2))
#    
#    refNorm = getNorm(ref)
#    
#    return [numpy.arccos(numpy.dot(ref, v1) / (refNorm * getNorm(v1))) for v1 in b]

# def solidAngle(phi):
#     return 2 * numpy.pi * (1 - numpy.cos(numpy.deg2rad(phi)))
