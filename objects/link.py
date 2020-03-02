import random
from config.constant import BYTES_PER_PACKET

class Link():

    def __init__(self, trace_list, queue_size):
        '''
        :param trace_list: [[time, bandwith, loss_rate, delay] ...]
        :param queue_size:
        '''
        self.trace_list = trace_list
        if len(trace_list) == 0:
            # use 全名
            self.bw = 20
            self.lr = .0
            self.dl = .0
        else:
            self.bw = trace_list[0][1] * 10**6 / BYTES_PER_PACKET
            self.lr = trace_list[0][2]
            self.dl = trace_list[0][3]

        self.queue_delay = 0.0
        self.queue_delay_update_time = 0.0
        self.max_queue_delay = queue_size / self.bw

        self.extra_delay = 0
        self.queue_size = queue_size


    def get_cur_queue_delay(self, event_time):
        return max(0.0, self.queue_delay - (event_time - self.queue_delay_update_time))


    def get_cur_latency(self, event_time):
        return self.dl + self.get_cur_queue_delay(event_time)


    def packet_enters_link(self, event_time):
        if (random.random() < self.lr):
            return False
        self.queue_delay = self.get_cur_queue_delay(event_time)
        self.queue_delay_update_time = event_time
        self.extra_delay = self.send_delay(event_time) # 1.0 / self.bw
        # print("Extra delay: %f, Current delay: %f, Max delay: %f" % (extra_delay, self.queue_delay, self.max_queue_delay))
        if self.extra_delay + self.queue_delay > self.max_queue_delay:
            # print("\tDrop!")
            return False
        self.queue_delay += self.extra_delay
        # print("\tNew delay = %f" % self.queue_delay)
        return True

    # todo : change to start id
    def update_trace(self, event_time):

        while len(self.trace_list) > 0 and \
                event_time > self.trace_list[0][0]:
            self.trace_list.pop(0)


    def send_delay(self, event_time):

        rest_block_size = 1
        # todo ： change to seconds
        transmition_ms = 0
        # different bw
        for i in range(len(self.trace_list)):
            if rest_block_size <= 0:
                break
            if event_time + transmition_ms > self.trace_list[i][0]:
                continue

            used_time = rest_block_size / self.bw
            tmp = self.trace_list[i][0] - (event_time + transmition_ms)
            if used_time > tmp:
                used_time = tmp
                rest_block_size -= used_time * self.bw
                self.bw = self.trace_list[i][1] * 10 ** 6 / BYTES_PER_PACKET
            else:
                rest_block_size = 0
            transmition_ms += used_time

        if rest_block_size > 0:
            transmition_ms += rest_block_size / self.bw
            self.update_trace(event_time+transmition_ms)

        self.max_queue_delay = self.queue_size / self.bw

        return transmition_ms


    def print_debug(self):
        print("Link:")
        print("Bandwidth: %f" % self.bw)
        print("Delay: %f" % self.dl)
        print("Queue Delay: %f" % self.queue_delay)
        print("Max Queue Delay: %f" % self.max_queue_delay)
        print("One Packet Queue Delay: %f" % (1.0 / self.bw))


    def reset(self):
        self.queue_delay = 0.0
        self.queue_delay_update_time = 0.0