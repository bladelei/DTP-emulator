#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : block
# @Function : 
# @Author : azson
# @Time : 2020/2/19 14:17
'''

from utils import (
    get_ms_time, get_free_App
)


class Block(object):

    def __init__(self,
                 priority=0,
                 block_id=-1,
                 bytes_size=200000,
                 deadline=200,
                 timestamp=None,
                 src=None,
                 dst=None,
                 **kwargs):

        self.priority = priority
        self.block_id = block_id
        self.size = bytes_size
        self.deadline = deadline
        self.timestamp = timestamp if not timestamp is None else get_ms_time()
        # emulator params
        self.queue_ms = -1
        self.propagation_ms = -1
        self.transmition_ms = -1

        # log params
        self.finish_timestamp = -1
        self.miss_ddl = 0

        # version 2.0
        self.src = get_free_App(src)
        self.dst = get_free_App(dst)
        self.log_list = kwargs["log_list"] if "log_list" in kwargs else []


    def append_log(self, info):
        self.log_list.append(info)


    def get_cost_time(self):

        return self.queue_ms + self.transmition_ms + self.propagation_ms


    def __str__(self):

        return str(self.__dict__)


if __name__ == '__main__':
    pass