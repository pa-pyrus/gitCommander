# read configuration
path = require "path"
nconf = require "nconf"

if process.env.XDG_CONFIG_HOME?
  CONFIG_HOME = process.env.XDG_CONFIG_HOME
else
  CONFIG_HOME = path.join process.env.HOME, ".config"

CONFIG_FILE = path.join CONFIG_HOME, "GitCommander", "config.json"
console.log "* Reading config file #{CONFIG_FILE}."
nconf.file CONFIG_FILE

IRC_OPTS = nconf.get "irc"
GIT_OPTS = nconf.get "git"
RECENCY = nconf.get "recency"
TIMEOUT = nconf.get "timeout"

# setup github api
GitHubApi = require "github"
github = new GitHubApi
  version: "3.0.0"

github.authenticate
  type: "oauth"
  token: GIT_OPTS.token

# connect to IRC
irc = require "irc"
console.log "* Connecting to IRC (#{IRC_OPTS.server})."
ircClient = new irc.Client IRC_OPTS.server, IRC_OPTS.nickname, IRC_OPTS.options

# we're connected and ready to do stuff on MOTD
ircClient.addListener "motd", (motd) ->
  console.log "* Connected to IRC."
  console.log "* Starting timer with timout #{TIMEOUT}."
  timer = setInterval timerCallback, TIMEOUT
  timer.unref

events = []
eventTeller =
  "PushEvent": (channel, event) ->
    ircClient.say channel, "[#{event.created_at}] #{event.actor.login} pushed
      #{event.payload.size} commit(s) to #{event.repo.name}"

handleEvents = (err, res) ->
  if err? or not res?
    console.log "! Error when handling events: #{err}."
    return

  nofEvents = 0
  res.reverse
  now = Date.now()

  for event in res
    # ignore events we've already seen and those older than one hour
    eventDate = new Date event.created_at
    age = now - eventDate.getTime()
    if age >= RECENCY or event.id in events
      continue
    events.push event.id
    nofEvents++
    if event.type of eventTeller
      for channel in IRC_OPTS.options.channels
        eventTeller[event.type] channel, event

  console.log "* Seen #{nofEvents} new events (#{events.length} total)."

timerCallback = ->
  for orgEntry in GIT_OPTS.orgs
    github.events.getFromOrg org: orgEntry, handleEvents
  for userEntry in GIT_OPTS.users
    github.events.getFromUser user: userEntry, handleEvents
