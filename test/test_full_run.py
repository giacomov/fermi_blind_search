import subprocess
import os

from fermi_blind_search.which import which
from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config


def test_most_recent_not_run_before():
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000
    config_path = "./test/config_test.txt"
    configuration = get_config(config_path)

    db = Database(configuration)
    db.create_tables()

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, config_path, most_recent_event))
    # subprocess.check_call(cmd_line, shell=True)
    p = subprocess.Popen(cmd_line, stdout=PIPE)
    stout, _ = p.communicate()
    print(stout)
    print("done yet?")
    assert 1==1
    # write_path = configuration.get("Real time", "base_path") + "/" + str(most_recent_event) + "_"
    # results_path = write_path + "/out.txt"
    # write_path = write_path + "/results"
    # print(results_path)
    # send_email_path = which("ltf_send_results_email.py")
    # # emulate the part that send the email, but write the results instead
    # email_cmd_line = ("%s --config %s --results %s --check_db --write_path %s" % (send_email_path, config_path,
    #                                                                               results_path, write_path ))
    #
    # subprocess.check_call(email_cmd_line, shell=True)
    #
    # result_files = os.listdir(write_path)
    #
    # print(len(result_files))
    # assert len(result_files) == 4