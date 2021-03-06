# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2020 Intel Corporation. All Rights Reserved.

"""
This module is for formatting and writing unit-tests in python. The general format is as follows
1. Use start to start a test and give it, as an argument, the name of the test
2. Use whatever check functions are relevant to test the run
3. Use finish to signal the end of the test
4. Repeat stages 1-3 as the number of tests you want to run in the file
5. Use print_results_and_exit to print the number of tests and assertions that passed/failed in the correct format
   before exiting with 0 if all tests passed or with 1 if there was a failed test

In addition you may want to use the 'info' functions in this module to add more detailed
messages in case of a failed check
"""

import os, sys, subprocess, traceback, platform
import pyrealsense2 as rs

n_assertions = 0
n_failed_assertions = 0
n_tests = 0
n_failed_tests = 0
test_failed = False
test_in_progress = False
test_info = {} # Dictionary for holding additional information to print in case of a failed check.

def set_env_vars(env_vars):
    """
    If this is the first time running this script we set the wanted environment, however it is impossible to change the
    current running environment so we rerun the script in a child process that inherits the environment we set
    :param env_vars: A dictionary where the keys are the name of the environment variable and the values are the
        wanted values in string form (environment variables must be strings)
    """
    if len(sys.argv) < 2:
        for env_var, val in env_vars.items():
            os.environ[env_var] = val
        sys.argv.append("rerun")
        if platform.system() == 'Linux' and "microsoft" not in platform.uname()[3].lower():
            cmd = ["python3"]
        else:
            cmd = ["py", "-3"]
        if sys.flags.verbose:
            cmd += ["-v"]
        cmd += sys.argv
        p = subprocess.run( cmd, stderr=subprocess.PIPE, universal_newlines=True )
        exit(p.returncode)

def find_first_device_or_exit():
    """
    :return: the first device that was found, if no device is found the test is skipped. That way we can still run
        the unit-tests when no device is connected and not fail the tests that check a connected device
    """
    c = rs.context()
    if not c.devices.size():  # if no device is connected we skip the test
        print("No device found, skipping test")
        exit(0)
    return c.devices[0]

def find_devices_by_product_line_or_exit(product_line):
    """
    :param product_line: The product line of the wanted devices
    :return: A list of devices of specific product line that was found, if no device is found the test is skipped.
        That way we can still run the unit-tests when no device is connected
        and not fail the tests that check a connected device
    """
    c = rs.context()
    devices_list = c.query_devices(product_line)
    if devices_list.size() == 0:
        print("No device of the" , product_line ,"product line was found; skipping test")
        exit(0)
    return devices_list

def print_stack():
    """
    Function for printing the current call stack. Used when an assertion fails
    """
    test_py_path = os.sep + "unit-tests" + os.sep + "py" + os.sep + "test.py"
    for line in traceback.format_stack():
        if test_py_path in line: # avoid printing the lines of calling to this function
            continue
        print(line)

"""
The following functions are for asserting test cases:
The check family of functions tests an expression and continues the test whether the assertion succeeded or failed.
The require family are equivalent but execution is aborted if the assertion fails. In this module, the require family
is used by sending abort=True to check functions
"""

def check_failed():
    """
    Function for when a check fails
    """
    global n_failed_assertions, test_failed
    n_failed_assertions += 1
    test_failed = True
    print_info()

def abort():
    print("Abort was specified in a failed check. Aborting test")
    exit(1)

def check(exp, abort_if_failed = False):
    """
    Basic function for asserting expressions.
    :param exp: An expression to be asserted, if false the assertion failed
    :param abort_if_failed: If True and assertion failed the test will be aborted
    :return: True if assertion passed, False otherwise
    """
    global n_assertions
    n_assertions += 1
    if not exp:
        print("Check failed, received", exp)
        check_failed()
        print_stack()
        if abort_if_failed:
            abort()
        return False
    reset_info()
    return True

def check_equal(result, expected, abort_if_failed = False):
    """
    Used for asserting a variable has the expected value
    :param result: The actual value of a variable
    :param expected: The expected value of the variable
    :param abort_if_failed:  If True and assertion failed the test will be aborted
    :return: True if assertion passed, False otherwise
    """
    if type(expected) == list:
        print("check_equal should not be used for lists. Use check_equal_lists instead")
        if abort_if_failed:
            abort()
        return False
    global n_assertions
    n_assertions += 1
    if result != expected:
        print("Result was:" + result + "\nBut we expected: " + expected)
        check_failed()
        print_stack()
        if abort_if_failed:
            abort()
        return False
    reset_info()
    return True

def unreachable( abort_if_failed = False ):
    """
    Used to assert that a certain section of code (exp: an if block) is not reached
    :param abort_if_failed: If True and this function is reached the test will be aborted
    """
    check(False, abort_if_failed)

def unexpected_exception():
    """
    Used to assert that an except block is not reached. It's different from unreachable because it expects
    to be in an except block and prints the stack of the error and not the call-stack for this function
    """
    global n_assertions
    n_assertions += 1
    traceback.print_exc( file = sys.stdout )
    check_failed()

def check_equal_lists(result, expected, abort_if_failed = False):
    """
    Used to assert that 2 lists are identical. python "equality" (using ==) requires same length & elements
    but not necessarily same ordering. Here we require exactly the same, including ordering.
    :param result: The actual list
    :param expected: The expected list
    :param abort_if_failed:  If True and assertion failed the test will be aborted
    :return: True if assertion passed, False otherwise
    """
    global n_assertions
    n_assertions += 1
    failed = False
    if len(result) != len(expected):
        failed = True
        print("Check equal lists failed due to lists of different sizes:")
        print("The resulted list has", len(result), "elements, but the expected list has", len(expected), "elements")
    i = 0
    for res, exp in zip(result, expected):
        if res != exp:
            failed = True
            print("Check equal lists failed due to unequal elements:")
            print("The element of index", i, "in both lists was not equal")
        i += 1
    if failed:
        print("Result list:", result)
        print("Expected list:", expected)
        check_failed()
        print_stack()
        if abort_if_failed:
            abort()
        return False
    reset_info()
    return True

def check_exception(exception, expected_type, expected_msg = None, abort_if_failed = False):
    """
    Used to assert a certain type of exception was raised, placed in the except block
    :param exception: The exception that was raised
    :param expected_type: The expected type of exception
    :param expected_msg: The expected message in the exception
    :param abort_if_failed:  If True and assertion failed the test will be aborted
    :return: True if assertion passed, False otherwise
    """
    failed = False
    if type(exception) != expected_type:
        print("Raised exception was of type", type(exception), "and not of type", expected_type, "as expected")
        failed = True
    if expected_msg and str(exception) != expected_msg:
        print("Exception had message:", str(exception), "\nBut we expected:", expected_msg)
        failed = True
    if failed:
        check_failed()
        print_stack()
        if abort_if_failed:
            abort()
        return False
    reset_info()
    return True

def check_frame_drops(frame, previous_frame_number, allowed_drops = 1):
    """
    Used for checking frame drops while streaming
    :param frame: Current frame being checked
    :param previous_frame_number: Number of the previous frame
    :param allowed_drops: Maximum number of frame drops we accept
    :return: False if dropped too many frames or frames were out of order, True otherwise
    """
    global test_in_progress
    if not test_in_progress: 
        return True
    frame_number = frame.get_frame_number()
    failed = False
    if previous_frame_number > 0:
        dropped_frames = frame_number - (previous_frame_number + 1)
        if dropped_frames > allowed_drops:
            print( dropped_frames, "frame(s) starting from frame", previous_frame_number + 1, "were dropped" )
            failed = True
        if dropped_frames < 0:
            print( "Frames repeated or out of order. Got frame", frame_number, "after frame",
                   previous_frame_number)
            failed = True
    if failed:
        check_failed()
        return False
    reset_info()
    return True

"""
The following functions are for adding additional information to the printed messages in case of a failed check.
"""

class Information:
    """
    Class representing the information stored in test_info dictionary
    """
    def __init__(self, value, persistent = False):
        self.value = value
        self.persistent = persistent

def info(name, value, persistent = False):
    """
    This function is used to store additional information to print in case of a failed test. This information is
    erased after the next check. The information is stored in the dictionary test_info, Keys are names (strings)
    and the items are of Information class
    If information with the given name is already stored it will be replaced
    :param name: The name of the variable
    :param value: The value this variable stores
    :param persistent: If this parameter is True, the information stored will be kept after the following check
        and will only be erased at the end of the test ( or when reset_info is called with True)
    """
    global test_info
    test_info[name] = Information(value, persistent)

def reset_info(persistent = False):
    """
    erases the stored information
    :param persistent: If this parameter is True, even the persistent information will be erased
    """
    global test_info
    if persistent:
        test_info.clear()
    else:
        for name, information in test_info.items():
            if not information.persistent:
                test_info.pop(name)

def print_info():
    global test_info
    if not test_info: # No information is stored
        return
    print("Printing information")
    for name, information in test_info.items():
        print("Name:", name, "        value:", information.value)
    reset_info()

"""
The following functions are for formatting tests in a file
"""

def fail():
    """
    Function for manually failing a test in case you want a specific test that does not fit any check function
    """
    global test_in_progress, n_failed_tests, test_failed
    if not test_in_progress:
        raise RuntimeError("Tried to fail a test with no test running")
    if not test_failed:
        n_failed_tests += 1
        test_failed = True

def start(*test_name):
    """
    Used at the beginning of each test to reset the global variables
    :param test_name: Any number of arguments that combined give the name of this test
    :return:
    """
    global n_tests, test_failed, test_in_progress
    if test_in_progress:
        raise RuntimeError("Tried to start test before previous test finished. Aborting test")
    n_tests += 1
    test_failed = False
    test_in_progress = True
    reset_info(persistent=True)
    print(*test_name)

def finish():
    """
    Used at the end of each test to check if it passed and print the answer
    """
    global test_failed, n_failed_tests, test_in_progress
    if not test_in_progress:
        raise RuntimeError("Tried to finish a test without starting one")
    if test_failed:
        n_failed_tests += 1
        print("Test failed")
    else:
        print("Test passed")
    print()
    test_in_progress = False

def print_results_and_exit():
    """
    Used to print the results of the tests in the file. The format has to agree with the expected format in check_log()
    in run-unit-tests and with the C++ format using Catch
    """
    global n_assertions, n_tests, n_failed_assertions, n_failed_tests
    if n_failed_tests:
        passed = n_assertions - n_failed_assertions
        print("test cases:", n_tests, "|" , n_failed_tests,  "failed")
        print("assertions:", n_assertions, "|", passed, "passed |", n_failed_assertions, "failed")
        exit(1)
    print("All tests passed (" + str(n_assertions) + " assertions in " + str(n_tests) + " test cases)")
    exit(0)
