import os

def make_dir_if_not_exist(path):

    # check if the directory already exists
    if not os.path.exists(path):
        # it doesn't! so we try to make it
        try:
            os.makedirs(path)
        except:
            print("Could not make the directory %s" % path)
            raise
        else:
            print("successfully created dir %s" % path)