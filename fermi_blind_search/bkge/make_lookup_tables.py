import matplotlib

matplotlib.use('Agg')

from fermi_blind_search.bkge import ROIBackgroundEstimator

import glob

simulations = glob.glob("/dev/shm/swap/reference_rois/ra*ref.fits")


import os

for i,sim in enumerate(simulations):      
    
    print("\n\n%s of %s" %(i+1, len(simulations)))
    
    ft1 = ROIBackgroundEstimator.myFT1File(sim)
    
    if os.path.exists(ROIBackgroundEstimator.get_theta_lookup_file(ft1.ra, ft1.dec)):
        
        continue
    
    else:
    
       dbkge = ROIBackgroundEstimator.ROIBackgroundEstimatorDataMaker(sim, '3fgl_36_months_ft2.fits')
       dbkge.makeThetaHistogram()
       
