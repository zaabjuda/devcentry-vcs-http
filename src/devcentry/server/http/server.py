# coding=utf-8
__author__ = "Dmitry Zhiltsov"
__copyright__ = "Copyright 2015, Dmitry Zhiltsov"
__year__ = 2015

import asyncio
import logging

from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.web import Application

from .banner import print_banner
from .handlers import InfoRefsHandler, BaseHandler, FileHandler


logger = logging.getLogger("tornado.general")


def make_app(io_loop):
    app = Application([
        ('/.*/git-.*', BaseHandler),
        ('/(?P<name_space>[\w-]+)/(?P<project>[\w-]+)\.git/info/refs', InfoRefsHandler),
        ('/(?P<name_space>[\w-]+)/(?P<project>[\w-]+)\.git/HEAD', FileHandler),
        ('/.*/objects/.*', BaseHandler),
    ])
    return app


def run_server():
    define('port', default=9090, type=int, help="Port to listen on")
    define('config', default='devcentry_config.yml', help="Path to config file")
    parse_command_line()
    print_banner()
    # Use asyncio loop
    AsyncIOMainLoop().install()
    io_loop = asyncio.get_event_loop()
    # Run server on corresponding port
    logging.info("Starting endpoint")
    app = make_app(io_loop)
    app.git_dir = '/home/dzhiltsov/tmp/'
    app.listen(options['port'])
    # Spin forever
    IOLoop.current().start()
