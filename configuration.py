#!/usr/bin/env python2
# vim:fenc=utf-8:ts=8:et:sw=4:sts=4:tw=79:ft=python

"""
configuration.py

The GitCommander IRC bot configuration loader.
It reads the configuration from XDG_CONFIG_HOME/GitCommander/config.json and
provides access to it.
"""

from json import load
from os import getenv
from os.path import join, expanduser

from twisted.python import log

# set up paths according to XDG basedir spec
CONFIG_HOME = getenv("XDG_CONFIG_HOME", expanduser("~/.config"))
CONFIG_FILE = join(CONFIG_HOME, "GitCommander", "config.json")

log.msg("Reading configuration from {0}.".format(CONFIG_FILE))

# importing us will fail if there is no such file
with open(CONFIG_FILE) as config_fp:
    config_dict = load(config_fp)
