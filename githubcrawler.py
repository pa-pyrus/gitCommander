#!/usr/bin/env python2
# vim:fenc=utf-8:ts=8:et:sw=4:sts=4:tw=79:ft=python

"""
githubcrawler.py

Defines the GithubCrawler class.

Copyright (c) 2014 Pyrus <pyrus@coffee-break.at>
See the file LICENSE for copying permission.
"""

from datetime import datetime
from json import loads
from urllib import urlencode

from twisted.internet.defer import DeferredList, succeed
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.web.client import getPage

from configuration import config_dict

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
GH_API_URL = "https://api.github.com"
GH_WEB_URL = "https://github.com"
GIT_IO_URL = "http://git.io"


class GithubCrawler(object):
    """
    The Github API crawler.

    Periodically queries a set of users, repositories and organizations and
    announces events to whoever is interested.
    """

    def __init__(self):
        """Read configuration or store defaults."""
        log.msg("Initializing Github crawler.")

        if "git" not in config_dict:
            log.err("No Github configuration found. Using default values.")

        git_cfg = config_dict.get("git", dict())

        # we don't use an auth token by default
        self.token = git_cfg.get("token", None)

        # times are in seconds
        self.timeout = git_cfg.get("timeout", 60)
        self.recency = git_cfg.get("recency", 3600)

        self.users = tuple(git_cfg.get("users", tuple()))
        self.repos = tuple(git_cfg.get("repos", tuple()))
        self.orgs = tuple(git_cfg.get("orgs", tuple()))

        self.loop = LoopingCall(self.update)

        # we remember the events we've seen so far
        self.events = set()

        # we cache git.io URLs mapped to their repository
        self.gitio_cache = dict()

        # whom do we need to notify?
        self.callbacks = list()

    def register(self, callback):
        """Register a callback that's called for each event."""
        self.callbacks.append(callback)

    def start(self):
        """Start the LoopingCall."""
        log.msg("Starting Github crawler LoopingCall.")
        self.loop.start(self.timeout, True)

    def update(self):
        """Start an update for all configured resources."""
        log.msg("Starting Github API update.")

        deferred_list = []

        def get_events(url):
            """Add an optional auth token retrieve events for the given URL."""
            if self.token:
                url = "{0}?{1}".format(url,
                                       urlencode({"access_token": self.token}))

            events_deferred = getPage(url)
            events_deferred.addCallback(self.on_update)
            deferred_list.append(events_deferred)

        for user in self.users:
            user_url = "{0}/users/{1}/events".format(GH_API_URL, user)
            get_events(user_url)

        for repo in self.repos:
            repo_url = "{0}/repos/{1}/{2}/events".format(GH_API_URL,
                                                         repo["user"],
                                                         repo["repo"])
            get_events(repo_url)

        for org in self.orgs:
            org_url = "{0}/orgs/{1}/events".format(GH_API_URL, org)
            get_events(org_url)

        # don't start a new update until all others have finished
        return DeferredList(deferred_list, consumeErrors=True)

    def on_update(self, content):
        """
        For each answer
          * check whether the event is recent enough,
          * check whether we have already seen that event,
          * add a shortened weburl, and
          * notify everyone interested
        """
        events = loads(content, encoding="utf-8")
        events.reverse()
        now = datetime.utcnow()
        for event in events:
            # skip events too old for us
            timestamp = datetime.strptime(event["created_at"], ISO_FORMAT)
            if (now - timestamp).total_seconds() > self.recency:
                continue

            # do we already know that event?
            event_id = int(event["id"])
            if event_id in self.events:
                continue

            # remember for next time
            self.events.add(event_id)

            weburl_deferred = self.add_weburl(event)
            for callback in self.callbacks:
                weburl_deferred.addCallback(callback)

    def add_weburl(self, event):
        """
        Add a shortened weburl to the event.
        In case we don't already know a short URL, we create one using git.io.
        If this doesn't work out, we add the full URL to the event.
        """
        repo_name = event["repo"]["name"]
        if repo_name in self.gitio_cache:
            event["repo"]["weburl"] = self.gitio_cache[repo_name]
            return succeed(event)

        full_url = "{0}/{1}".format(GH_WEB_URL, repo_name)
        log.msg("Shortening Github URL {0}.".format(full_url))

        def gitio_success(content):
            web_url = "{0}/{1}".format(GIT_IO_URL, content)
            log.msg("Shortened URL {0} to {1}.".format(full_url, web_url))
            # add shortened URL
            event["repo"]["weburl"] = web_url

            # cache for next time
            self.gitio_cache[repo_name] = web_url

            return event

        def gitio_error(error):
            log.err("Shortening URL {0} failed.".format(full_url))
            # add full URL instead
            event["repo"]["weburl"] = full_url

            return event

        gitio_deferred = getPage("{0}/create".format(GIT_IO_URL),
                                 method="POST",
                                 postdata=urlencode({"url": full_url}))
        gitio_deferred.addCallbacks(gitio_success, gitio_error)
        return gitio_deferred
