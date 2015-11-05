# coding=utf-8
__author__ = "Dmitry Zhiltsov"
__copyright__ = "Copyright 2015, Dmitry Zhiltsov"
__year__ = 2015

from asyncio import subprocess, coroutine, get_event_loop
import calendar
import datetime
import email.utils
import logging
import os
import re
from urllib import parse

from tornado.web import RequestHandler, HTTPError, gen


logger = logging.getLogger('tornado.handlers')


def get_date_header(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    t = calendar.timegm(dt.utctimetuple())
    return email.utils.formatdate(t, localtime=False, usegmt=True)


cache_forever = lambda: [('Expires', get_date_header(datetime.datetime.now() + datetime.timedelta(days=365))),
                         ('Pragma', 'no-cache'),
                         ('Cache-Control', 'public, max-age=31556926')]

dont_cache = lambda: [('Expires', 'Fri, 01 Jan 1980 00:00:00 GMT'),
                      ('Pragma', 'no-cache'),
                      ('Cache-Control', 'no-cache, max-age=0, must-revalidate')]


class BaseHandler(RequestHandler):
    def initialize(self, **kwargs):
        self.gitcommand = 'git'

    def git_lookup(self):
        real_path = os.path.join(self.application.git_dir, self.path_kwargs['name_space'],
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
    @gen.coroutine
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
            raise NotImplemented
            return
        rpc = rpc[4:]
        start_off = '# service=git-' + rpc
        start_off = str(hex(len(start_off) + 4)[2:].rjust(4, '0')) + start_off
        start_off += '0000'  # flush packet
        com = [self.gitcommand, rpc, '--stateless-rpc', '--advertise-refs', gitdir]
        self.set_header("Content-Type", 'application/x-git-%s-advertisement' % rpc)
        self.set_header("Expires", 'Fri, 01 Jan 1980 00:00:00 GMT')
        self.set_header("Pragma", 'no-cache')
        self.set_header("Cache-Control", 'no-cache, max-age=0, must-revalidate')
        yield from self.git_com(com, self)
        self.request.finish()

    @coroutine
    def git_com(self, cmd, request):
        procees = subprocess.create_subprocess_shell(' '.join(cmd), stdout=subprocess.PIPE)
        proc = yield from procees
        data = yield from proc.stdout.readline()
        line = data.decode('ascii').rstrip().encode()
        request.write(line)
        yield from proc.wait()


file_headers = {
    re.compile('.*(/HEAD)$'): lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*(/objects/info/alternates)$'): lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*(/objects/info/http-alternates)$'): lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*(/objects/info/packs)$'): lambda: dict(
        dont_cache() + [('Content-Type', 'text/plain; charset=utf-8')]),
    re.compile('.*(/objects/info/[^/]+)$'): lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*(/objects/[0-9a-f]{2}/[0-9a-f]{38})$'): lambda: dict(
        cache_forever() + [('Content-Type', 'application/x-git-loose-object')]),
    re.compile('.*(/objects/pack/pack-[0-9a-f]{40}\\.pack)$'): lambda: dict(
        cache_forever() + [('Content-Type', 'application/x-git-packed-objects')]),
    re.compile('.*(/objects/pack/pack-[0-9a-f]{40}\\.idx)$'): lambda: dict(
        cache_forever() + [('Content-Type', 'application/x-git-packed-objects-toc')]),
}


class FileHandler(BaseHandler):
    @gen.coroutine
    def get(self, project, name_space, *args):
        gitdir = self.get_gitdir()
        read, write = self.check_auth()
        if not read:
            if self.auth_failed:
                self.auth_failed()
                self.request.finish()
                return
            else:
                raise HTTPError(403, 'You are not allowed to perform this action')
        filename, headers = None, None
        for matcher, get_headers in file_headers.items():
            m = matcher.match(self.request.path)
            if m:
                filename = m.group(1)
                headers = get_headers()
                break
        logger.debug("Found %r with headers %r", filename, headers)
        if not filename:
            raise HTTPError(404, 'File not Found')

        filename = os.path.abspath(os.path.join(gitdir, filename.lstrip('/')))
        if not filename.startswith(os.path.abspath(gitdir)):
            raise HTTPError(404, 'Trying to access file outside of git repository')
        file_obj = open(filename, 'rb')
        logger.debug('Serving file %s', file_obj)
        yield from self.read_file(file_obj)
        self.finish()

    @coroutine
    def read_file(self, file_obj):
        loop = get_event_loop()
        line = yield from loop.run_in_executor(None, file_obj.readline)
        if len(line) == 0:
            return None
        self.write(line.decode("utf-8").rstrip("\n").encode())
