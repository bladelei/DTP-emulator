#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : emulator
# @Function : 
# @Author : azson
# @Time : 2020/1/8 15:59
'''


from utils import (
        Block, Node
    )
import random, json, time


class Emulator(object):

    def __init__(self, transmission_rate=10**7,
                 propagation_rate=3*10**8,
                 link_list=None,
                 block_file=None,
                 trace_file=None,
                 det=0):

        self.block_file = block_file
        self.trace_file = trace_file
        self.link_list = link_list

        self.transmission_rate = transmission_rate
        self.propagation_rate = propagation_rate

        self.init_time = 0
        self.pass_time = .0

        self.trace_list = []

        self.fir_log = True
        self.fir_cal = True
        self.block_circle = -1
        self.det = det

        if self.trace_file:
            self.trace_list = self.get_trace()
        if len(self.trace_list) > 0:
            self.transmission_rate = self.trace_list[0][1] * 10**6

        # version 2.0
        self.fir_run = True
        self.network = self.create_network()
        self.topo_list = self.get_topo_list()


    def create_network(self):
        pass


    def get_topo_list(self):
        pass


    def update_queue(self, det=0):

        with open(self.block_file, "r") as f:
            self.block_circle = int(f.readline())

            pattern_cols = ["type", "size", "ddl"]
            pattern=[]
            for line in f.readlines():
                pattern.append(
                    { pattern_cols[idx]:item.strip() for idx, item in enumerate(line.split(',')) }
                )

            peroid = len(pattern)
            for idx in range(self.block_circle):
                ch = idx % peroid
                block = Block(bytes_size=float(pattern[ch]["size"]),
                              block_id=idx,
                              deadline=float(pattern[ch]["ddl"]),
                              timestamp=self.init_time+self.pass_time+idx*det,
                              priority=pattern[ch]["type"])

                self.cal_queue[int(pattern[ch]["type"]) ].append(block)


    def update_trace(self):

        while len(self.trace_list) > 0 and \
                self.pass_time > self.trace_list[0][0]:
            self.trace_list.pop(0)


    def run_stop(self, stop_time=-1):
        '''
        only run emulator for "stop_time" ms.
        It will run consistently if "stop_time" equal -1.
        :param stop_time: int
        :return:
        '''
        if self.fir_run and self.block_file:
            self.update_queue(det=self.det)
            self.fir_run = False

        while True:

            for node in self.topo_list:
                if isinstance(node, Node):
                    self.pass_time = node.run_stop(stop_time)

            if stop_time!= -1 and self.init_time+self.pass_time >= stop_time:
                break


    def get_trace(self):

        trace_list = []
        with open(self.trace_file, "r") as f:

            for line in f.readlines():
                trace_list.append(list(
                    map(lambda x : float(x), line.split(","))
                ))

        return trace_list


    def log_block(self, block):

        if self.fir_log:
            self.fir_log = False
            with open("output/emulator.log", "w") as f:
                pass

        block.finish_timestamp = self.init_time + self.pass_time
        if block.get_cost_time() > block.deadline:
            block.miss_ddl = 1

        with open("output/emulator.log", "a") as f:
            f.write(str(block)+'\n')


    def analysis(self, rows=20, file_path=None):

        import matplotlib.pyplot as plt

        if not file_path:
            file_path = "output/emulator.log"

        plt_data = []
        max_time = -1
        with open(file_path, "r") as f:
            for line in f.readlines():
                plt_data.append(json.loads(line.replace("'", '"')))

        plt.figure(figsize=(20, 10))
        plt.title("Block's Changing Process", fontsize=30)
        plt.xlabel("Time / ms", fontsize=20)
        plt.ylabel("Block Id", fontsize=20)

        labels= ["Queue time", "Transmission time", "Propagation time",
                 "Not created", "Miss deadline"]
        linewidth=5
        fir_ddl = True
        # fixed start point in plot

        for idx in range(min(rows, len(plt_data))):
            used_label = labels if not idx else [None] * 5
            st = 0

            if plt_data[idx]["queue_ms"] != -1:
                st = plt_data[idx]["timestamp"] - self.init_time
                plt.plot([0, st], [idx + 1] * 2, c='black',
                         label=used_label[3], linewidth=linewidth)

                plt.plot([st, st+plt_data[idx]["queue_ms"] ], [idx+1]*2, c='r',
                         label=used_label[0], linewidth=linewidth)

            if plt_data[idx]["transmition_ms"] != -1:
                st += plt_data[idx]["queue_ms"]
                plt.plot([st, st+plt_data[idx]["transmition_ms"] ], [idx+1] * 2, c='g',
                         label=used_label[1], linewidth=linewidth)

            if plt_data[idx]["propagation_ms"] != -1:
                st += plt_data[idx]["transmition_ms"]
                plt.plot([st, st+plt_data[idx]["propagation_ms"] ], [idx+1] * 2, c='b',
                         label=used_label[2], linewidth=linewidth)
                st += plt_data[idx]["propagation_ms"]

            max_time = max(max_time, st)

            if plt_data[idx]["miss_ddl"] == 1:
                if fir_ddl:
                    fir_ddl = False
                    used_label[4] = "Miss deadline"
                plt.scatter([-5], [idx+1], c='r', marker='x', label=used_label[4])

        # plot bandwith
        trace_list = self.get_trace()
        st = 0
        for idx in range(len(trace_list)):
            plt.plot([st, trace_list[idx][0] ], [len(plt_data)+1] * 2, '--',
                     linewidth=5)
            st = trace_list[idx][0]

        plt.plot([st, max_time], [len(plt_data) + 1] * 2, '--',
                 label="Different Bandwith", linewidth=5)

        plt.legend(fontsize=20)
        plt.savefig("output/emulator-analysis.jpg")


if __name__ == '__main__':

    block_file = "config/block.txt"
    trace_file = "config/trace.txt"

    emulator = Emulator(block_file=block_file,
                        trace_file=trace_file,
                        det=1)

    emulator.run_stop()
    emulator.analysis(rows=1000)