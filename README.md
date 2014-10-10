# GitCommander IRC bot #
GitCommander is a *simple* IRC bot.
It crawls the GitHub API for events and announces them on configured channels.

## Setup ##
1. Install **Node.js** and **[npm](https://www.npmjs.org/)**.
2. Run `npm install [-g] git+https://github.org/pa-pyrus/GitCommander.git` to install GitCommander.
3. Adapt configuration in `$XDG_CONFIG_HOME/GitCommander/config.json`.
4. Run `npm start GitCommander`.

## Dependencies ##
* [Node.js](http://www.nodejs.org/)
    * All other dependencies will be installed using **[npm](https://www.npmjs.org/)**.
* [CoffeeScript](http://coffeescript.org/)
* [node-irc](https://github.com/martynsmith/node-irc)
* [nconf](https://github.com/flatiron/nconf)
* [node-github](https://github.com/mikedeboer/node-github)
* [node-gitio2](https://github.com/passcod/node-gitio)
