#!/usr/bin/env twistd
# vim:fenc=utf-8:ts=8:et:sw=4:sts=4:tw=79:ft=python

"""
gitcommander.tac

The GitCommander IRC bot Twisted service file.
Reads the configuration, sets up logging and starts the bot.

Copyright (c) 2014 Pyrus <pyrus@coffee-break.at>
See the file LICENSE for copying permission.
"""

from twisted.application import internet, service
from twisted.internet import ssl
from twisted.python import log
from twisted.python.logfile import LogFile

from configuration import config_dict
from githubbot import BotFactory

# set up the application and logfile
application = service.Application("GitCommander")
logfile = LogFile("GitCommander.log", "/tmp", maxRotatedFiles=1)
application.setComponent(log.ILogObserver, log.FileLogObserver(logfile).emit)

irc_cfg = config_dict.get("irc", {"server": "irc.esper.net", "port": 6697})

factory = BotFactory()
internet.SSLClient(irc_cfg["server"], irc_cfg["port"],
                   factory, ssl.CertificateOptions()).setServiceParent(
    service.IService(application))
