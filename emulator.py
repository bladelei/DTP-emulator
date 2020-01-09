#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : emulator
# @Function : 
# @Author : azson
# @Time : 2020/1/8 15:59
'''


from utils import (
        Block, get_ms_time, lower_bound
    )
import random, json, time


class Emulator(object):

    def __init__(self, transmission_rate=10**7,
                 propagation_rate=3*10**8,
                 link_list=None,
                 block_file=None,
                 trace_file=None):

        self.a_queue, self.b_queue, self.c_queue = [], [], []
        # use shallow copy
        self.cal_queue = [self.a_queue, self.b_queue, self.c_queue]
        # not used
        self.s_wnd=1500
        self.r_wnd=1500
        self.c_wnd=1500
        self.loss_rate = .0

        self.block_file = block_file
        self.trace_file = trace_file
        self.link_list = link_list

        self.transmission_rate = transmission_rate
        self.propagation_rate = propagation_rate

        self.init_time = get_ms_time()
        self.pass_time = .0
        self.last_past_time = .0

        self.trace_list = []

        self.fir_log = True
        self.block_circle = -1

        if self.trace_file:
            self.trace_list = self.get_trace()
        if len(self.trace_list) > 0:
            self.transmission_rate = self.trace_list[0][1] * 10**6


    def update_queue(self):

        with open(self.block_file, "r") as f:
            self.block_circle = int(f.readline())

            pattern_cols = ["type", "size", "ddl"]
            pattern=[]
            for line in f.readlines():
                pattern.append(
                    {pattern_cols[idx]:item.strip() for idx, item in enumerate(line.split(','))}
                )

            peroid = len(pattern)
            for idx in range(self.block_circle):
                ch = idx % peroid
                block = Block(bytes_size=float(pattern[ch]["size"]),
                              deadline=float(pattern[ch]["ddl"]),
                              timestamp=self.init_time+self.pass_time)

                self.cal_queue[int(pattern[ch]["type"]) ].append(block)


    def update_trace(self):

        while len(self.trace_list) > 0 and \
                self.pass_time > self.trace_list[0][0]:
            self.trace_list.pop(0)


    def run(self, times=1):

        for _ in range(times):

            if self.block_file:
                self.update_queue()
            self.last_past_time = self.pass_time

            while True:
                send_block = self.select_block()

                if not send_block:
                    break

                send_block = self.cal_block(send_block)

                # loss package?

                self.log_block(send_block)


    def cal_block(self, block):

        # cal queue time, use get_ms_time which contain cal time
        block.queue_ms = self.init_time + self.pass_time - block.timestamp
        if self.pass_time <= 0.0000001:
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
        block.propagation_ms = random.random() * 10
        block.propagation_ms += 100 if not self.link_list else self.link_list[0] / self.propagation_rate

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


    def get_trace(self, det=0):

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
                        trace_file=trace_file)

    emulator.run(times=3)
    emulator.analysis(rows=1000)