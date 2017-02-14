import subprocess


def execute_command(cmd_line):

    print("\nExecuting command:")
    print(cmd_line)

    subprocess.check_call(cmd_line, shell=True)
