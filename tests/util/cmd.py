# coding: utf-8

# Copyright 2017 Scality
#
# This file is part of Eve.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.
"""A simple command launcher."""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)


def cmd(command, ignore_exception=False, cwd=None, wait=True, env=None):
    """Execute a shell command and display output in a readable manner.

    Args:
        command (string): The command to execute.
        ignore_exception (bool): Do not raise a CalledProcessError if return
            code is not 0.
        cwd (string): The directory that the command will be run from.
        wait (bool): Wait for finish. default==True.
        env (dict): Environement variables to add to os.environ before running
            the command.

    """
    output = ''
    logger.info('COMMAND : %s', command)
    if env is not None:
        for key, val in env.iteritems():
            os.environ[key] = val
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd)

    if not wait:
        return None

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        if nextline:
            logger.info(' │ %s', nextline.rstrip())
            output += nextline
        elif process.poll() is not None:
            break

    logger.info(u' └────────')

    process.communicate()
    exit_code = process.returncode

    if exit_code == 0 or ignore_exception:
        return output
    raise subprocess.CalledProcessError(exit_code, command)
