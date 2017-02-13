#!/usr/bin/env python

#PBS -l walltime=01:00:00
#PBS -l nodes=1:ppn=20
#PBS -l vmem=30gb


import os, shutil, traceback,sys, subprocess
import socket

def are_we_at_slac():
    
    hostname = socket.getfqdn()
    
    if hostname.find('slac.stanford.edu') > 0:
        
        return True
    else:
        
        return False

# Add the path to the python modules

if are_we_at_slac():
    
    PACKAGE_PATH = '/nfs/farm/g/glast/u/giacomov/blindTransientSearch'

else:
    
    PACKAGE_PATH = '/home/giacomov/blindTransientSearch'

sys.path.append(PACKAGE_PATH)

def make_analysis(date, duration, irfs, probability, workdir):
    
    cmd_line = ("%s/ltfsearch.py --date %s --duration %s --irfs %s" 
                " --probability %s --loglevel info --workdir %s" 
                % (PACKAGE_PATH, date,duration,irfs,probability,workdir))
    
    print(cmd_line)
    
    subprocess.check_call(cmd_line, shell=True)
    

if __name__=="__main__":
  
  #date = os.environ['date']
  #duration = os.environ['duration']
  #irfs = os.environ['irfs']
  #probability = os.environ['probability']
  
  # Process command line
  
  date, duration, irfs, probability = sys.argv[1:]
  
  # Print options
  print("About to execute job with these parameters:\n")
  print("date : %s" % date)
  print("duration : %s" % duration)
  print("irfs : %s" % irfs)
  print("probability : %s" % probability)
  
  print("\n\n\nRunning on the computer farm")
  print("This is my environment:")
  for key, value in os.environ.iteritems():
    print("%s = %s" %(key, value))
  
  #Print 3 empty lines
  print("\n\n\n")  
 
  #This is what you need to do to create a directory
  #in the computer node

  #This is your unique job ID (a number like 546127)
  
  if are_we_at_slac():
      
      unique_id = os.environ.get("LSB_JOBID")
      
      workdir = os.path.join('/scratch',unique_id)
      
  else:
  
      unique_id = os.environ.get("PBS_JOBID").split(".")[0]
  
      #os.path.join joins two path in a system-independent way
      workdir = os.path.join('/dev/shm',unique_id)
  
  #Now create the workdir
  print("About to create %s..." %(workdir))
  
  try:
     os.makedirs(workdir)
  except:
     print("Could not create workdir %s !!!!" %(workdir))
     raise
  else:
     #This will be executed if no exception is raised
     print("Successfully created %s" %(workdir))
  
  #now you have to go there
  os.chdir(workdir)
  
  try:
    
    make_analysis(date, duration, irfs, probability, workdir)
  
  except:
    
    traceback.print_exc(sys.stdout)
  
  finally:

    #This is executed in any case, whether an exception have been raised or not
    #I use this so we are sure we are not leaving trash behind even
    #if this job fails
    
    #First move out of the workdir
    os.chdir(os.path.expanduser('~'))

    #Now remove the directory    
    try:
      
      shutil.rmtree(workdir)
    
    except:
      
      print("Could not remove workdir. Unfortunately I left behind some trash!!")
      raise
    
    else:
      
      print("Clean up completed.")
