# coding=utf-8
__author__ = "Dmitry Zhiltsov"
__copyright__ = "Copyright 2015, Dmitry Zhiltsov"
__year__ = 2015

import os
import logging
from urllib import parse

from tornado.web import RequestHandler, HTTPError, asynchronous


logger = logging.getLogger('tornado.handlers')


class BaseHandler(RequestHandler):
    def initialize(self, **kwargs):
        self.gitcommand = 'git'

    def git_lookup(self):
        real_path =  os.path.join(self.application.git_dir, self.path_kwargs['name_space'],
                                  self.path_kwargs['project']) + '.git'
        if os.path.isdir(real_path):
            return real_path
        return False

    def auth_failed(self):
        msg = 'Authorization needed to access this repository'
        self.request.write('HTTP/1.1 401 Unauthorized\r\nContent-Type: text/plain\r\nContent-Length: %d\r\n'
                           'WWW-Authenticate: Basic realm="%s"\r\n\r\n%s' % (len(msg), "DevCentry", msg))

    def get_gitdir(self):
        gitdir = self.git_lookup()
        if gitdir is None:
            raise HTTPError(404, 'unable to find repository')
        logger.debug("Accessing git at: %s", gitdir)

        return gitdir

    def check_auth(self):
        return True, True

    def enforce_perms(self, rpc):
        read, write = self.check_auth()
        if rpc in ['git-receive-pack', 'receive-pack']:
            if not write:
                self.auth_failed()
                self.request.finish()
                return False
        elif rpc in ['git-upload-pack', 'upload-pack']:
            if not read:
                self.auth_failed()
                self.request.finish()
                return False
        else:
            raise HTTPError(400, 'Unknown RPC command')
        return True


class InfoRefsHandler(BaseHandler):
    @asynchronous
    def get(self, project, name_space, *args):
        gitdir = self.get_gitdir()
        logger.debug("Query string: %r", self.request.query)
        rpc = parse.parse_qs(self.request.query).get('service', [''])[0]
        read, write = self.check_auth()
        if not read:
            if self.auth_failed:
                self.auth_failed()
                self.request.finish()
                return
            else:
                raise HTTPError(403, 'You are not allowed to perform this action')
        if not rpc:
            logger.debug("Dumb client detected")
            raise  NotImplemented
            return
        rpc = rpc[4:]
        start_off = '# service=git-' + rpc
        start_off = str(hex(len(start_off) + 4)[2:].rjust(4, '0')) + start_off
        start_off += '0000' # flush packet
        raise NotImplemented
