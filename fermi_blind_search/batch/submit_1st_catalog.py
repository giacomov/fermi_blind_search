#!/usr/bin/env python
import datetime
import subprocess
import socket
import numpy

def are_we_at_slac():
    
    hostname = socket.getfqdn()
    
    if hostname.find('slac.stanford.edu') > 0:
        
        return True
    else:
        
        return False

def name_to_date(name):
    yy,mm,dd = name[0:2],name[2:4],name[4:6]
    return '20%s-%s-%s' %(yy,mm,dd)

if __name__=="__main__":
    
    names = numpy.recfromtxt("1st_cat_detections.txt")
    
    dates = map(name_to_date, names)
    
    for date in dates:
        
        #2015-09-14T09:50:45 86400.0 P8R2_TRANSIENT010E_V6 1e-6
        
        if are_we_at_slac():
             
            cmd_line = ('''bsub -W 03:00 -n 4 -R "span[hosts=1] rusage[mem=1000]"'''
                        ''' analyze_one_day.py %sT00:00:00 86400.0 '''
                        '''P8R2_SOURCE_V6 1e-6''' % date)
        
        else:
        
            cmd_line = ("qsub -F '%sT00:00:00 86400.0 "
                        "P8R2_TRANSIENT010E_V6 1e-5' analyze_one_day.py" % date)
                
        print(cmd_line)
        
        subprocess.check_call(cmd_line,shell=True)
