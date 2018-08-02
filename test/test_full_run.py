import subprocess
import os
import shutil
import time

from fermi_blind_search.which import which
from fermi_blind_search.database import Database


def test_setup(configuration):

    # make sure we start with an empty database
    db = Database(configuration)
    db.create_tables()
    db.delete_results_table()
    db.delete_analysis_table()


def test_most_recent_not_run_before(configuration):
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000

    db = Database(configuration)
    db.create_tables()

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, configuration.config_file, most_recent_event))
    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    time.sleep(60)
    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results

    # read in results file and check that the second line matches what it should be
    write_path = os.path.join(configuration.get("Real time", "base_path"),
                              str(most_recent_event - 43200.0) + "_43200.0", "out.txt")

    results = []
    with open(write_path) as f:
        results = f.read().split("\n")

    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(configuration.get("Real time", "base_path"))

    assert results[1] == \
           "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"




def test_most_recent_has_been_run_should_rerun(configuration):
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000

    db = Database(configuration)
    db.create_tables()

    base_path = os.path.abspath(os.path.expandvars(
        os.path.expanduser(configuration.get("Real time", "base_path"))))
    directory = os.path.join(base_path, "410184003.0_43200.0")

    analysis_to_add = {"met_start": 410184003.0, "duration": 43200.0, "counts": 30, "directory": directory}
    db.add_analysis(analysis_to_add)

    results = db.get_analysis_between_times(410227203.000 - 86400.0, 410227203.000 - 43200.0 - 1)
    for row in results:
        print(row)

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, configuration.config_file, most_recent_event))

    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)

    time.sleep(60)
    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results

    write_path = os.path.join(directory, "out.txt")
    results = []
    with open(write_path) as f:
        results = f.read().split("\n")
    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(base_path)

    assert results[1] == \
           "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"


def test_most_recent_has_been_run_should_not_rerun(configuration):
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000

    db = Database(configuration)
    db.create_tables()

    base_path = os.path.abspath(os.path.expandvars(
        os.path.expanduser(configuration.get("Real time", "base_path"))))
    directory = os.path.join(base_path, "410184003.0_43200.0")

    analysis_to_add = {"met_start": 410184003.0, "duration": 43200.0, "counts": 3639487, "directory": directory}
    db.add_analysis(analysis_to_add)

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, configuration.config_file, most_recent_event))

    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    time.sleep(60)
    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results
    ls = os.listdir(directory)

    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(base_path)

    assert len(ls) == 1


def test_rerun_past_analyses(configuration):
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000

    db = Database(configuration)
    db.create_tables()

    # analyses to rerun
    base_path = os.path.abspath(os.path.expandvars(
        os.path.expanduser(configuration.get("Real time", "base_path"))))

    # end time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410097703.0, "duration": 43200.0, "counts": 25,
                       "directory": os.path.join(base_path, "410097703.0_43200.0")}
    db.add_analysis(analysis_to_add)

    # start and end times of analysis fall in analysis interval
    analysis_to_add = {"met_start": 410141803.0, "duration": 40200.0, "counts": 25,
                       "directory": os.path.join(base_path, "410141803.0_40200.0")}
    db.add_analysis(analysis_to_add)

    # start time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410183003.0, "duration": 40000.0, "counts": 25,
                       "directory": os.path.join(base_path, "410183003.0_40000.0")}
    db.add_analysis(analysis_to_add)

    # analyses not to rerun

    # # end time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410139803.0, "duration": 40000.0, "counts": 3576544,
                       "directory": os.path.join(base_path, "410139803.0_40000.0")}
    db.add_analysis(analysis_to_add)

    # start and end times of analysis fall in analysis interval
    analysis_to_add = {"met_start": 410141803.0, "duration": 40000.0, "counts": 3539609,
                       "directory": os.path.join(base_path, "410141803.0_40000.0")}
    db.add_analysis(analysis_to_add)

    # start time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410183003.0, "duration": 40200.0, "counts": 3204272,
                       "directory": os.path.join(base_path, "410183003.0_40200.0")}
    db.add_analysis(analysis_to_add)

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, configuration.config_file, most_recent_event))

    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)

    time.sleep(60)
    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results
    len1 = len(os.listdir(os.path.join(base_path, "410139803.0_40000.0")))
    len2 = len(os.listdir(os.path.join(base_path, "410141803.0_40000.0")))
    len3 = len(os.listdir(os.path.join(base_path, "410183003.0_40200.0")))

    results1 = ''
    with open(os.path.join(base_path, "410097703.0_43200.0/out.txt")) as f:
        results1 = f.read()

    results2 = []
    with open(os.path.join(base_path, "410097703.0_43200.0/out.txt")) as f:
        results2 = f.read().split("\n")

    results3 = []
    with open(os.path.join(base_path, "410183003.0_40000.0/out.txt")) as f:
        results3 = f.read().split("\n")

    results4 = []
    with open(os.path.join(base_path, "410184003.0_43200.0/out.txt")) as f:
        results4 = f.read().split("\n")

    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(configuration.get("Real time", "base_path"))

    assert len1 == 1
    assert len2 == 1
    assert len3 == 1

    assert results1 == \
           "# name ra dec tstarts tstops counts probabilities"

    assert results2[1] == \
           "LTF003738.54-043812.88 9.41058921814 -4.63691186905 410146516.288,410157957.022,410158188.93 410157946.008,410158181.858,410181087.077 3,22,24 0.4415005372786246,6.762756319877049e-27,0.021202409309007006"

    assert results3[1] == \
           "LTF222917.20-570319.91 337.321655273 -57.0555305481 410214484.059 410214503.816 3 5.196131451719908e-06"

    assert results4[1] == \
           "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"
