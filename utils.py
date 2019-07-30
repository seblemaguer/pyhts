#!/usr/bin/python3

import shlex
import subprocess

def run_shell_command(command_line, logger):
    command_line_args = shlex.split(command_line)

    logger.info('Subprocess: "' + command_line + '"')

    try:
        command_line_process = subprocess.Popen(
            command_line_args,
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
