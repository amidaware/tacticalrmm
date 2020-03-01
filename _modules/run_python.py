import os


def run_python_script(filename, timeout):
    python_bin = os.path.join("c:\\salt\\bin", "python.exe")
    file_path = os.path.join("c:\\windows\\temp", filename)
    __salt__["cp.get_file"](
        "salt://scripts/userdefined/{0}".format(filename), file_path
    )
    return __salt__["cmd.run_all"](
        "{0} {1}".format(python_bin, file_path), timeout=timeout
    )
