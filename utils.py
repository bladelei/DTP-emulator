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



class Node(object):

    def __init__(self, transmission_rate=10**7,
                 propagation_rate=3*10**8,
                 link_list=None,
                 trace_list=None,
                 det=0,
                 type="Host",
                 block_queue=None):

        self.cal_queue = block_queue if block_queue else []
        # not used
        self.s_wnd=1500
        self.r_wnd=1500
        self.c_wnd=1500
        self.loss_rate = .0

        self.link_list = link_list
        self.trace_list = trace_list

        self.transmission_rate = transmission_rate
        self.propagation_rate = propagation_rate

        self.init_time = 0
        self.pass_time = .0

        self.fir_cal = True
        self.block_circle = -1
        self.det = det

        self.type = type

        if len(self.trace_list) > 0:
            self.transmission_rate = self.trace_list[0][1] * 10**6


    def update_queue(self, det=0):

        pass


    def update_trace(self):

        while len(self.trace_list) > 0 and \
                self.pass_time > self.trace_list[0][0]:
            self.trace_list.pop(0)


    def run_stop(self, stop_time=-1):

        while True:
            send_block = self.select_block()

            # todo : send_block type id error
            if not send_block:
                break

            # if the block create time > last block finished time(pass_time)
            self.pass_time = max(self.pass_time, send_block.timestamp)
            send_block = self.cal_block(send_block)

            # loss package?

            self.log_block(send_block)

        return self.init_time + self.pass_time


    def cal_block(self, block):

        # cal queue time, use get_ms_time which contain cal time
        block.queue_ms = self.init_time + self.pass_time - block.timestamp
        if self.fir_cal:
            self.fir_cal = False
            self.pass_time += block.queue_ms

        # cal transmition_ms
        block.transmition_ms = 0
        rest_block_size = block.size
        # different bw
        for i in range(len(self.trace_list)):
            if rest_block_size <= 0:
                break
            if self.pass_time + block.transmition_ms > self.trace_list[i][0]:
                continue

            used_time = rest_block_size / self.transmission_rate * 1000
            tmp = self.trace_list[i][0] - (self.pass_time + block.transmition_ms)
            if used_time > tmp:
                used_time = tmp
                rest_block_size -= used_time * self.transmission_rate / 1000
                self.transmission_rate = self.trace_list[i][1] * 10 ** 6
            else:
                rest_block_size = 0
            block.transmition_ms += used_time

        if rest_block_size > 0:
            block.transmition_ms += rest_block_size / self.transmission_rate * 1000
            self.update_trace()

        # queue in link
        block.propagation_ms = random.random() * 0.5
        block.propagation_ms += 2 if not self.link_list else self.link_list[0] / self.propagation_rate

        # update emulator
        self.pass_time += block.transmition_ms

        return block


    def select_block(self):

        def is_better(block):
            return (now_time - block.timestamp) * best_block.deadline > \
                    (now_time - best_block.timestamp) * block.deadline


        best_block=None
        now_time = self.init_time + self.pass_time
        ch=-1

        while not best_block:
            queue_size = sum(map(lambda x:len(x), self.cal_queue))
            if queue_size == 0:
                break

            for idx in range(3):
                if len(self.cal_queue[idx]) == 0:
                    continue

                # if miss ddl in queue, clean and log
                if self.init_time + self.pass_time > \
                        self.cal_queue[idx][0].timestamp + self.cal_queue[idx][0].deadline:
                    self.cal_queue[idx][0].miss_ddl = 1
                    self.log_block(self.cal_queue[idx][0])
                    self.cal_queue[idx].pop(0)
                    break

                if best_block == None or is_better(self.cal_queue[idx][0]) :
                    best_block = self.cal_queue[idx][0]
                    ch = idx

        if best_block:
            self.cal_queue[ch].pop(0)

        return best_block


    def get_trace(self):

        pass


    def log_block(self, block):

        pass




if __name__ == '__main__':

    obj = Block()
    print(obj)