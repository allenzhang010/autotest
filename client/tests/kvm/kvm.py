import sys, os, time, shelve, random, resource, logging
from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error


class test_routine:
    def __init__(self, module_name, routine_name):
        self.module_name = module_name
        self.routine_name = routine_name
        self.routine = None


class kvm(test.test):
    """
    Suite of KVM virtualization functional tests.
    Contains tests for testing both KVM kernel code and userspace code.

    @copyright: Red Hat 2008-2009
    @author: Uri Lublin (uril@redhat.com)
    @author: Michael Goldish (mgoldish@redhat.com)
    @author: David Huff (dhuff@redhat.com)
    @author: Alexey Eromenko (aeromenk@redhat.com)
    @author: Mike Burns (mburns@redhat.com)
    """
    version = 1
    def initialize(self):
        # Define the test routines corresponding to different values
        # of the 'type' field
        self.test_routines = {
                # type                       module name            routine
                "steps":        test_routine("kvm_guest_wizard", "run_steps"),
                "stepmaker":    test_routine("stepmaker", "run_stepmaker"),
                "boot":         test_routine("kvm_tests", "run_boot"),
                "migration":    test_routine("kvm_tests", "run_migration"),
                "yum_update":   test_routine("kvm_tests", "run_yum_update"),
                "autotest":     test_routine("kvm_tests", "run_autotest"),
                "kvm_install":  test_routine("kvm_install", "run_kvm_install"),
                "linux_s3":     test_routine("kvm_tests", "run_linux_s3"),
                }

        # Make it possible to import modules from the test's bindir
        sys.path.append(self.bindir)


    def run_once(self, params):
        import logging
        import kvm_utils
        import kvm_preprocessing

        # Seed the random number generator
        random.seed()

        # Enable core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (-1, -1))

        # Set the logging prefix
        #kvm_log.set_prefix(params.get("shortname"))

        # Report the parameters we've received and write them as keyvals
        logging.debug("Test parameters:")
        keys = params.keys()
        keys.sort()
        for key in keys:
            logging.debug("    %s = %s" % (key, params[key]))
            self.write_test_keyval({key: params[key]})

        # Open the environment file
        env_filename = os.path.join(self.bindir, "env")
        env = shelve.open(env_filename, writeback=True)
        logging.debug("Contents of environment: %s" % str(env))

        try:
            try:
                # Get the test routine corresponding to the specified test type
                type = params.get("type")
                routine_obj = self.test_routines.get(type)
                # If type could not be found in self.test_routines...
                if not routine_obj:
                    message = "Unsupported test type: %s" % type
                    logging.error(message)
                    raise error.TestError(message)
                # If we don't have the test routine yet...
                if not routine_obj.routine:
                    # Dynamically import the module
                    module = __import__(routine_obj.module_name)
                    # Get the needed routine
                    routine_name = "module." + routine_obj.routine_name
                    routine_obj.routine = eval(routine_name)

                # Preprocess
                kvm_preprocessing.preprocess(self, params, env)
                env.sync()
                # Run the test function
                routine_obj.routine(self, params, env)
                env.sync()

            except Exception, e:
                logging.error("Test failed: %s" % e)
                logging.debug("Postprocessing on error...")
                kvm_preprocessing.postprocess_on_error(self, params, env)
                env.sync()
                raise

        finally:
            # Postprocess
            kvm_preprocessing.postprocess(self, params, env)
            logging.debug("Contents of environment: %s" % str(env))
            env.sync()
            env.close()
