#!/usr/bin/env python
import datetime
import subprocess
import socket

def are_we_at_slac():
    
    hostname = socket.getfqdn()
    
    if hostname.find('slac.stanford.edu') > 0:
        
        return True
    else:
        
        return False


def daterange( start_date, end_date ):
    if start_date <= end_date:
        for n in range( ( end_date - start_date ).days + 1 ):
            yield start_date + datetime.timedelta( n )
    else:
        for n in range( ( start_date - end_date ).days + 1 ):
            yield start_date - datetime.timedelta( n )

if __name__=="__main__":
    
    start = datetime.date( year = 2008, month = 9, day = 16 )
    end = datetime.date( year = 2008, month = 9, day = 17)
    
    date_range = daterange(start, end)
    
    for date in date_range:
        
        #2015-09-14T09:50:45 86400.0 P8R2_TRANSIENT010E_V6 1e-6
        
        if are_we_at_slac():
             
            cmd_line = ('''bsub -W 03:00 -Rinet -n 4 -R "span[hosts=1] rusage[mem=1000]"'''
                        ''' submit_job.py %sT00:00:00 86400.0 '''
                        '''P8R2_SOURCE_V6 1e-6''' % date)
        
        else:
        
            cmd_line = ("qsub -F '%sT00:00:00 86400.0 "
                        "P8R2_SOURCE_V6 1e-6' submit_job.py" % date)
                
        print(cmd_line)
        
        subprocess.check_call(cmd_line,shell=True)
