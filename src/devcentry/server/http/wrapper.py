# coding=utf-8
__author__ = 'dzhiltsov'
__year__ = 2015


from asyncio import subprocess


class GitProcessWrapper(object):
    def __init__(self, command):
        self.procees = subprocess.create_subprocess_exec(command)
