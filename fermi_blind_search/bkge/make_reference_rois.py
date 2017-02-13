import GtApp
import numpy
import os
import subprocess

from fermi_blind_search.Configuration import configuration
from scripts.ltfsearch import computeSpread

try:
    
    from astropy.io import fits as pyfits

except:

    import pyfits

class ReferenceROIsMaker(object):
    
    def __init__(self, sim_ft1_file, sim_ft2_file, grid_file, evclass=128):
        
        with pyfits.open(grid_file) as f:
            
            self.ras = f[1].data.field("RA")
            self.decs = f[1].data.field("DEC")
        
        spread,medianDistance = computeSpread(numpy.vstack([self.ras,
                                                            self.decs]).T)
        
        # Use a radius to cover all
        
        self.radius = medianDistance + spread
        
        # Save event class to use
        self.evclass = evclass
        
        # Check that the FT1 file exists
        
        if os.path.exists(sim_ft1_file):
            
            self.sim_ft1_file = os.path.abspath(sim_ft1_file)
        
        else:
            
            raise IOError("File %s does not exist!" % (sim_ft1_file))
        
        if os.path.exists(sim_ft2_file):
            
            self.sim_ft2_file = os.path.abspath(sim_ft2_file)
        
        else:
            
            raise IOError("File %s does not exist!" % (sim_ft2_file))
    
    def go(self):
        
        #####################################################################
        ## REMEMBER: since we are using simulations, there is no zenith cut 
        ## to be made!
        ####################################################################
        
        # Prepare args for gtselect
        
        args = {'rad' : self.radius,
                'tmin': 0,
                'tmax': 0,
                'emin': configuration.get('Analysis','emin'),
                'emax': configuration.get('Analysis','emax'),
                'zmax': 180,
                'evclass': self.evclass,
                'evtype': 3,
                'chatter': 4
               }
        
        # Prepare args for gtmktime
        
        mkargs = {'scfile': self.sim_ft2_file,
                  'roicut': 'no',
                  'apply_filter': 'yes',
                  'header_obstimes': 'yes',
                  'chatter': 4}
        
        for i, (ra, dec) in enumerate(zip(self.ras, self.decs)):
            
            print("\nProcessing ROI centered on (%.3f,%.3f)...\n" % (ra,dec))
            print("(%s out of %s)" % (i+1, len(self.ras)))            
            
            
            # Run first ftcopy which is way faster than gtselect, then use
            # gtmktime and finally gtselect to fix keywords and stuff
            
            # Create a region file
            
            reg_file = "__reg_filter.reg"
            
            filter_region = 'circle(%s,%s,%s)' %(ra,dec,self.radius+0.5)
            
            with open(reg_file,"w+") as f:
                
                # I use a slightly larger radius to make sure that we don't loose
                # events at this stage, gtselect will fix this
                
                f.write("#fk5\n%s\n" % filter_region)
            
            temp_file = '__pre_filtered_ft1.fits'
            
            print("\nAbout to filter with region: %s\n" % filter_region)
            
            
            cmd_line = """fcopy '%s[EVENTS][regfilter("%s",RA,DEC)]' %s clobber=yes""" % (self.sim_ft1_file,
                                                                         reg_file, temp_file)
            
            print("\n%s\n" %(cmd_line))
            
            subprocess.call(cmd_line,shell=True)
            
            # Run gtmktime
            
            #mkargs['evfile'] = temp_file
            #mkargs['filter'] = (#'(DATA_QUAL>0 || DATA_QUAL==-1) && '
                               #'LAT_CONFIG==1 && '
                               #'IN_SAA!=T && '
                               #'LIVETIME>0 && '
            #                   '(ANGSEP(RA_ZENITH,DEC_ZENITH,%s,%s)<=(%s-%s)) ' %(ra, dec, zenith_cut, self.radius))
            
            #temp_file2 = '__mktime_ft1.fits'
            
            #mkargs['outfile'] = temp_file2
            
            #gtmktime = GtApp.GtApp('gtmktime')
            
            #for k,v in mkargs.iteritems():
                
            #    gtmktime[k] = v
            
            #gtmktime.run()
            
            args['infile'] = temp_file
            args['outfile'] = 'reference_rois/ra%.3f-dec%.3f_ref.fits' %(ra,dec)
            args['ra'] = ra
            args['dec'] = dec
            
            gtselect = GtApp.GtApp('gtselect')
            
            for k,v in args.iteritems():
                
                gtselect[k] = v
        
            gtselect.run()
            print("\ndone\n")
            
    
