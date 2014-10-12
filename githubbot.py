#!/usr/bin/env python2
# vim:fenc=utf-8:ts=8:et:sw=4:sts=4:tw=79:ft=python

"""
githubbot.py

Defines the GitCommander IRC bot and its protocol factory.
"""

from twisted.internet import protocol, reactor
from twisted.python import log
from twisted.words.protocols import irc

from configuration import config_dict
from githubcrawler import GithubCrawler


class GithubBot(irc.IRCClient):
    """
    The GitCommander IRC bot.

    It authenticates with NickServ, joins channels and announces Github events.
    """

    crawler = GithubCrawler()

    def sendLine(self, line):
        """Encode all unicode lines."""
        if isinstance(line, unicode):
            line = line.encode("utf-8")
        irc.IRCClient.sendLine(self, line)

    def connectionMade(self):
        """
        Upon successful connection establishment, we set up our nickname, real
        name and message rate.
        """
        self.nickname = self.factory.nickname
        self.username = self.factory.username
        self.realname = self.factory.realname
        self.lineRate = self.factory.linerate
        irc.IRCClient.connectionMade(self)

    def signedOn(self):
        """
        Authenticate with NickServ and join the configured channels as soon as
        the welcome message is received.
        """
        log.msg("Connection established successfully.")

        if self.factory.nickserv:
            log.msg("Authenticating with NickServ.")
            self.msg("NickServ", "IDENTIFY {0}".format(self.factory.nickserv))

        log.msg("Joining channels {0}.".format(self.factory.channels))
        for channel in self.factory.channels:
            self.join(channel)

        # register our callback method
        self.crawler.register(self.tellEvent)

        # now we can start the crawler
        self.crawler.start()

    def tellEvent(self, event):
        """
        Check if we're interested in an event and send it to all our channels.
        """
        event_teller_name = "tell{0}".format(event["type"])
        event_teller = getattr(self, event_teller_name, None)
        if event_teller and callable(event_teller):
            log.msg("Got {0} for {1}.".format(event["type"],
                                              event["repo"]["name"]))

            for channel in self.factory.channels:
                event_teller(event, channel)

    def tellPushEvent(self, event, channel):
        """Write a PushEvent to the specified channel."""
        numerus = "commits" if event["payload"]["size"] else "commit"
        self.say(channel,
                 "[{0}] \x02{1}\x02 pushed {2} {3} "
                 "to \x02{4}\x02 ({5})".format(
                     event["created_at"], event["actor"]["login"],
                     event["payload"]["size"], numerus,
                     event["repo"]["name"], event["repo"]["weburl"]))

    def tellReleaseEvent(self, event, channel):
        """Write a ReleaseEvent to the specified channel."""
        self.say(channel,
                 "[{0}] \x02{1}\x02 published a new release {2} "
                 "to \x02{3}\x02 ({4})".format(
                     event["created_at"], event["actor"]["login"],
                     event["payload"]["release"]["tag_name"],
                     event["repo"]["name"], event["repo"]["weburl"]))


class BotFactory(protocol.ClientFactory):
    """
    Factory for GitCommander IRC connections.

    Reads the passed configuration, stores it and passes it to the protocol
    object created in buildProtocol.
    """

    # there's no instance until buildProtocol is called
    instance = None

    def __init__(self):
        """Read configuration or store defaults."""
        log.msg("Initializing Github API bot.")

        if "irc" not in config_dict:
            log.err("No IRC configuration found. Using default values.")

        irc_cfg = config_dict.get("irc", dict())

        self.nickname = irc_cfg.get("nickname", "GitCommander")
        # we don't auth with NickServ by default
        self.nickserv = irc_cfg.get("nickserv", None)
        self.username = irc_cfg.get("username", "gitcommander")
        self.realname = irc_cfg.get("realname", "Git Commander")
        self.channels = irc_cfg.get("channels", "#pamodding")
        self.linerate = irc_cfg.get("linerate", 1)

    def buildProtocol(self, address):
        """Build a new GithubBot instance and remember it."""
        log.msg("Creating a new GithubBot instance.")

        newBot = GithubBot()
        newBot.factory = self
        self.instance = newBot
        return newBot

    def getInstance(self):
        """Return the current GithubBot instance."""
        return self.instance

    def clientConnectionLost(self, connector, reason):
        """Reconnect to the server if we got disconnected."""
        log.msg("Disconnected from server: {0}".format(
            reason.getErrorMessage()))
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        """Stop the reactor if the connection fails."""
        log.msg("Connection to server failed: {0}".format(
            reason.getErrorMessage()))
        reactor.stop()
