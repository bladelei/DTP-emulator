#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : utils
# @Function : 
# @Author : azson
# @Time : 2020/1/8 15:59
'''

import time, json
from matplotlib import pyplot as plt

def get_ms_time(rate=1000):

    return time.time()*rate


class Block(object):

    def __init__(self,
                 priority=0,
                 block_id=-1,
                 bytes_size=200000,
                 deadline=200,
                 timestamp=None):

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


    def get_cost_time(self):

        return self.queue_ms + self.transmition_ms + self.propagation_ms


    def __str__(self):

        return str(self.__dict__)


class Package(object):

    def __init__(self,
                 create_time,
                 next_hop,
                 block_id,
                 package_id,
                 deadline=0.2,
                 package_type="S",
                 drop = False,
                 send_delay=.0,
                 queue_delay=.0
                 ):
        self.package_type = package_type
        self.create_time = create_time
        self.next_hop = next_hop
        self.block_id = block_id
        self.package_id = package_id
        self.deadline = deadline
        self.drop = drop

        self.send_delay = send_delay
        self.queue_delay = queue_delay
        self.propagation_delay = 0.0002


    def parse(self):

        return [self.package_type,
                self.next_hop,
                self.queue_delay,
                self.drop,
                self.queue_delay,
                self.package_id]


    def __lt__(self, other):
        return self.create_time < other.create_time


    def __str__(self):
        print_data = {
            "Time": self.create_time,
            "Type": self.package_type,
            "Position": self.next_hop,
            "Send_delay" : self.send_delay,
            "Queue_delay": self.queue_delay,
            "Propagation_delay" : self.propagation_delay,
            "Drop": 1 if self.drop else 0,
            "Package_id": self.package_id,
            "Block_id": self.block_id,
            "Create_time" : self.create_time,
            "Deadline" : self.deadline
        }
        return str(print_data)


def analyze_pcc_emulator(log_file, trace_file=None, rows=20):

    plt_data = []

    with open(log_file, "r") as f:
        for line in f.readlines():
            plt_data.append(json.loads(line.replace("'", '"')))

    # priority by package id
    plt_data = sorted(plt_data, key=lambda x:x["Package_id"])

    plt.figure(figsize=(20, 10))
    plt.title("Block's Changing Process", fontsize=30)
    plt.xlabel("Time / ms", fontsize=20)
    plt.ylabel("Block Id", fontsize=20)

    labels = ["Queue time", "Transmission time", "Propagation time",
              "Not created", "Miss deadline"]
    max_time = plt_data[-1]["Time"]
    fir_drop = True
    linewidth = 5
    last_y = -1

    for idx in range(min(rows, len(plt_data))):
        # print(plt_data[idx])
        used_label = labels if not idx else [None] * 5
        y = plt_data[idx]["Package_id"]
        last_x = 0 if y != last_y else x
        x = plt_data[idx]["Time"]
        last_y = y

        # print(last_x, x, plt_data[idx]["Life"])
        plt.plot([last_x, x], [y] * 2, c='black',
                 label=used_label[3], linewidth=linewidth)

        plt.plot([last_x, plt_data[idx]["Life"] ], [y] * 2, c='r',
                 label=used_label[1], linewidth=linewidth)
        plt.plot([last_x, plt_data[idx]["Latency"]], [y] * 2, c='g',
                 label=used_label[2], linewidth=linewidth)

        if plt_data[idx]["Drop"] == 1:
            if fir_drop:
                fir_drop = False
                used_label[4] = "Miss deadline"
            plt.scatter([-1], [idx + 1], c='r', marker='x', label=used_label[4])

    # plot bandwith
    if trace_file:
        trace_list = []
        with open(trace_file, "r") as f:
            for line in f.readlines():
                trace_list.append(list(
                    map(lambda x: float(x), line.split(","))
                ))

        st = 0
        for idx in range(len(trace_list)):
            if trace_list[idx][0] > max_time:
                break
            plt.plot([st, trace_list[idx][0]], [len(plt_data) + 1] * 2, '--',
                     linewidth=5)
            st = trace_list[idx][0]

        if trace_list[-1][0] < max_time:
            plt.plot([st, max_time], [len(plt_data) + 1] * 2, '--',
                 label="Different Bandwith", linewidth=5)

        plt.legend(fontsize=20)
        plt.savefig("output/pcc_emulator-analysis.jpg")


if __name__ == '__main__':

    obj = Block()
    print(obj)