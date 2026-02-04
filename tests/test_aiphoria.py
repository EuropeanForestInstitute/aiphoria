#!/usr/bin/env python3
"""
Script for testing package structure before building

Test function must be:
- prefixed with "test_"
- contain docstring (comment wrapped in 3 quotation marks)
- return two parameters: first is number of passed test and second is number of failed tests

"""
import sys
import logging
from typing import Tuple


class LogFormatter(logging.Formatter):
    """Custom formatting class with colorsfor logging-instance"""
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    WHITE = "\033[0;37m"
    RESET = "\033[0m"

    FORMATS = {
        logging.INFO: f"{GREEN}[%(levelname)s]{RESET} %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Global logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(LogFormatter())
logger.addHandler(ch)


def test_core_imports() -> Tuple[int, int]:
    """
    Verify core module imports
    """
    passed = 0
    failed = 0
    logger.info("Verify importing as package")


    # TODO: Test importing aiphoria as package inside venv and using it
    return passed, failed


if __name__ == "__main__":
    """
    Run all callable test functions inside this script
    that are prefixed by "test_"
    """
    name_to_entry = {}
    module = sys.modules[__name__]
    attribute_names = dir(module)
    for name in attribute_names:
        if name.startswith("_"):
            continue

        if not name.startswith("test_"):
            continue

        attr = getattr(module, name)
        if not callable(attr):
            continue

        desc = attr.__doc__ if hasattr(attr, "__doc__") else None
        if desc:
            desc = desc.strip()
        name_to_entry[name] = {"function": attr, "name": name, "description": desc, "is_success": False, "errors": []}

    num_test_functions = len(name_to_entry)
    num_total_tests_passed = 0
    num_total_tests_failed = 0
    logger.info("Running {} test functions".format(num_test_functions))
    logger.info("")

    # Function name to status
    name_to_errors = {}
    for index, (func_name, entry) in enumerate(name_to_entry.items()):
        func = entry["function"]
        func_desc = entry["description"]
        func_result = entry["is_success"]
        func_errors = entry["errors"]

        if not func_desc:
            # No docstring for test, treat this as error
            func_errors.append("No docstring for test function \"{}\"".format(func_name))
            entry["is_success"] = False
            num_total_tests_failed += 1
            continue

        test_passed = 0
        test_failed = 0
        try:
            logger.info("Test function {}/{}: {}".format(index + 1, num_test_functions, func_desc))
            test_passed, test_failed = func()
            is_success = (test_passed == 0 and test_failed == 0) or (test_passed > 0 and test_failed == 0)

            # Assume test function was successful test_passed == 0 and test_failed == 0
            # This happens if test function does not return two parameters
            if is_success:
                entry["is_success"] = is_success
                test_passed = test_passed if test_passed > 0 else 1
            else:
                entry["is_success"] = is_success
                test_failed = test_failed if test_failed > 0 else 1
                entry["errors"].append("Test function failed")

        except Exception as ex:
            func_errors.append("Function not returning tuple (passed, failed)")
            entry["is_success"] = False
            if not test_failed:
                test_failed = 1

        num_total_tests_passed += test_passed
        num_total_tests_failed += test_failed
        logger.info("")

    num_total_tests = num_total_tests_passed + num_total_tests_failed
    logger.info("RESULT: Passed: {}, failed: {}, total tests: {}".format(
        num_total_tests_passed,
        num_total_tests_failed,
        num_total_tests))

    if num_total_tests_failed == 0:
        logger.info("All test functions passed ({}/{})".format(num_test_functions, num_test_functions))
    else:
        failed_tests = [entry for name, entry in name_to_entry.items() if not entry["is_success"]]
        logger.info("{}/{} test functions failed {}:".format(
            len(failed_tests),
            num_test_functions,
            "test" if num_test_functions == 1 else "tests"))

        for entry in failed_tests:
            logger.info("Function: {} (Description: {}): {}".format(entry["name"], entry["description"], entry["errors"][0]))
