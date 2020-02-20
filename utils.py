#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : utils
# @Function : 
# @Author : azson
# @Time : 2020/1/8 15:59
'''

import time, random
from collections import namedtuple


App = namedtuple("Application", ["ip", "port"])
Graph = namedtuple("Graph", ["nodes", "edges"])
used_app_poll = set()


def get_free_App(app=None):
    '''
    if app not used, return itself. Other, find a free App and return it.
    :param app: App
    :return: App
    '''
    if not isinstance(app, App):
        if not app:
            app = App("127.0.0.1", "5001")
        else:
            raise ValueError("app type should be App(ip, port)!")

    while app in used_app_poll:
        app = (app.ip, random.randint(5001, 65536))
    used_app_poll.add(app)

    return app


def get_ms_time(rate=1000):

    return time.time()*rate
