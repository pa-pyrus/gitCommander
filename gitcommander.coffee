# read configuration
path = require "path"
nconf = require "nconf"

if "XDG_CONFIG_HOME" of process.env
  CONFIG_HOME = process.env.XDG_CONFIG_HOME
else
  CONFIG_HOME = path.join process.env.HOME, ".config"

CONFIG_FILE = path.join CONFIG_HOME, "GitCommander", "config.json"
console.log "* Reading config file #{CONFIG_FILE}."
nconf.file CONFIG_FILE

IRC_OPTS = nconf.get "irc"
CHANNELS = IRC_OPTS.options.channels
GIT_OPTS = nconf.get "git"
RECENCY = nconf.get "recency"
TIMEOUT = nconf.get "timeout"

# write pidfile
PIDFILE = nconf.get "pidfile"
console.log "* Writing PID file #{PIDFILE}."
fs = require "fs"
fs.writeFileSync PIDFILE, process.pid

# delete pidfile on exit
process.on "exit", (code) ->
  console.log "* Deleting PID file #{PIDFILE}."
  fs.unlinkSync PIDFILE

# call exit on SIGINT and SIGTERM
exitHandler = (signal) ->
  console.log "* Received #{signal}. Exiting..."
  process.exit(0)
process.on "SIGINT", -> exitHandler("SIGINT")
process.on "SIGTERM", -> exitHandler("SIGTERM")

# setup github api
GitHubApi = require "github"
github = new GitHubApi
  version: "3.0.0"

github.authenticate
  type: "oauth"
  token: GIT_OPTS.token

gitio = require "gitio2"

# connect to IRC
irc = require "irc"
console.log "* Connecting to IRC (#{IRC_OPTS.server})."
ircClient = new irc.Client IRC_OPTS.server, IRC_OPTS.nickname, IRC_OPTS.options

# we're connected and ready to do stuff on MOTD
ircClient.addListener "motd", (motd) ->
  console.log "* Connected to IRC."
  console.log "* Starting timer with timout #{TIMEOUT}."
  timer = setInterval timerCallback, TIMEOUT
  do timer.unref

events = []
handleEvents = (err, res) ->
  if err? or not res?
    console.log "! Error when handling events: #{err}."
    return

  nofEvents = 0
  do res.reverse
  now = do Date.now

  for event in res
    # ignore events we've already seen and those older than the configured limit
    eventDate = new Date event.created_at
    age = now - do eventDate.getTime
    if age >= RECENCY or event.id in events
      continue
    events.push event.id
    if event.type of eventTeller
      nofEvents++
      announceEvent event

  if nofEvents
    console.log "* Seen #{nofEvents} new events (#{events.length} total)."

announceEvent = (event) ->
  weburl = "https://github.com/#{event.repo.name}"
  gitio weburl, (err, res) ->
    if err? or not res?
      console.log "! Error when shortening URL #{weburl}."
      event.repo.weburl = weburl
    else
      event.repo.weburl = res

    for channel in CHANNELS
      eventTeller[event.type] channel, event

eventTeller =
  "PushEvent": (channel, event) ->
    numerus = if event.payload.size > 1 then "commits" else "commit"
    ircClient.say channel, "[#{event.created_at}] #{event.actor.login} pushed
      #{event.payload.size} #{numerus} to
      #{event.repo.name} (#{event.repo.weburl})"
  "ReleaseEvent": (channel, event) ->
    ircClient.say channel, "[#{event.created_at}] #{event.actor.login} published
      a new release (#{event.payload.release.tag_name}) of
      #{event.repo.name} (#{event.repo.weburl})"

timerCallback = ->
  for orgEntry in GIT_OPTS.orgs
    github.events.getFromOrg
      org: orgEntry
      handleEvents

  for repoEntry in GIT_OPTS.repos
    github.events.getFromRepo
      user: repoEntry.user
      repo: repoEntry.repo
      handleEvents

  for userEntry in GIT_OPTS.users
    github.events.getFromUser
      user: userEntry
      handleEvents
