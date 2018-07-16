#!/usr/bin/env python

import argparse
import os
import subprocess

from fermi_blind_search.which import which

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Generate LTF jobs (one job per day) for dates listed in a .txt file and submit them to the farm')
	parser.add_argument('--date_file', help='Path to file of dates to analyse', type=str, required=True)
	parser.add_argument('--config', help='Path to configuration file', type=str, required=True)
	parser.add_argument('--outdir', help='Directory for results (must be NFS/AFS)', type=str, required=True)
	parser.add_argument('--logdir', help='Directory for logs (must be NFS/AFS)', type=str, required=True) 
	# consider adding a --simulate argument
	
	args = parser.parse_args()
	ltf_submit_day_jobs_path = which("ltf_submit_day_jobs.py")	
	dates = open(args.date_file).read().splitlines()
	for i in range(len(dates)):
		print('Submitting day job for %s' % dates[i])
		cmd_line = ("%s --start_date %s --end_date %s --config %s --outdir %s --logdir %s" % (ltf_submit_day_jobs_path, dates[i], dates[i], args.config, args.outdir, args.logdir))
		#ltf_submit_day_jobs.py requires that you hit "Enter" partway through the script. So we use subprocess.Popen() and communicate() to send "\n" to stdin		
		ps = subprocess.Popen(cmd_line, shell=True, stdin=subprocess.PIPE)
		_ = ps.communicate("\n")[0] 
