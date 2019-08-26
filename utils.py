#!/usr/bin/python3

import shlex
import subprocess

def run_shell_command(command_line, logger):
    command_line_args = " ".join(shlex.split(command_line))

    logger.info('Subprocess: "' + str(command_line_args) + '"')

    try:
        command_line_process = subprocess.Popen(
            ["sh", "-c", command_line_args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        process_output, _ =  command_line_process.communicate()
        logger.info(process_output.decode())
    except (OSError, subprocess.CalledProcessError) as exception:
        logger.error('Exception occured: ' + str(exception))
        logger.error('Subprocess failed')
        return False
    else:
        # no exception was raised
        logger.info('Subprocess finished')

    return True
