default_config = '''

[Analysis]
# Zenith cut for gtmktime
zenith_cut = 100
# Theta cut for gtmktime
theta_cut = 65
# Emin and emax in MeV
emin = 100
emax = 100000
# Maximum duration, above which any excess is excluded (in seconds)
Max_duration = 21600
# Minimum number of counts in excess
Min_counts = 3

[Hardware]
ncpus = 10

[ROIBackgroundEstimator]
datapath: /home/giacomov/develop/blindTransientSearch/ROIBackgroundEstimator_data

'''