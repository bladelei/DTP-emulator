#《大象席地而坐》《路边野餐》《过春天》《地久天长》《山河故人》《白日焰火》《树先生》《百鸟朝凤》《八月》

from emulator import Emulator
import random
import numpy as np
import matplotlib.pyplot as plt
def creat_network(row, max_bw):
    trace_list = []
    for i in range(row):
        tmp = []
        tmp.append(i * 10)
        tmp.append(random.uniform(0, max_bw))
        tmp.append(random.random())
        trace_list.append(tmp)

    with open("config/traces.txt", "w+") as f:
        for i in range(len(trace_list)):
            for j in range(2):
                f.write(str(trace_list[i][j]))
                f.write(',')
            f.write(str(trace_list[i][2]))
            f.write('\n')


def main(times):
    first_qoe = []
    second_qoe = []
    for _ in range(times):
        creat_network(row=10, max_bw=100)
        block_file = "config/block.txt"
        trace_file = "config/traces.txt"

        emulator0 = Emulator(block_file=block_file,
                            trace_file=trace_file,
                            det=1,
                            tag=0)
        emulator0.run(times=1)
        qoe0 = emulator0.cal_QOE()
        first_qoe.append(qoe0)

        emulator1 = Emulator(block_file=block_file,
                            trace_file=trace_file,
                            det=1,
                            tag=1)
        emulator1.run(times=1)
        qoe1 = emulator1.cal_QOE()
        second_qoe.append(qoe1)

    data = np.array([first_qoe, second_qoe])
    data = data.T
    np.savetxt("scripts/network.log", data,fmt="%d", delimiter=',')
    return first_qoe,second_qoe


def drawing(times, first_qoe, second_qoe):
    X = np.linspace(1, times, times)
    Y1 = np.array(first_qoe)
    Y2 = np.array(second_qoe)
    fig, ax = plt.subplots()
    ax.plot(X, Y1, color='blue', label="base_priority")
    ax.plot(X, Y2, color='red',label="base_ddl")
    ax.set_xlabel("times")
    ax.set_ylabel("qoe")
    ax.legend()
    plt.savefig("scripts/network-drawing.png")


if __name__ == '__main__':
    times = 100
    first_qoe, second_qoe = main(times)
    drawing(times, first_qoe, second_qoe)



