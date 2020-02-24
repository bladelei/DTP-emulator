import heapq
import time
import random
import json
import os
import sys
import inspect
import numpy as np

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from common import sender_obs
from utils import analyze_pcc_emulator, Block, Package

DELTA_SCALE = 0.9

MAX_CWND = 5000
MIN_CWND = 4

MAX_RATE = 1000
MIN_RATE = 40

REWARD_SCALE = 0.001

EVENT_TYPE_SEND = 'S'
EVENT_TYPE_ACK = 'A'

BYTES_PER_PACKET = 1500

LATENCY_PENALTY = 1.0
LOSS_PENALTY = 1.0

USE_LATENCY_NOISE = False
MAX_LATENCY_NOISE = 1.1

USE_CWND = True


BLOCK_SIZE = 15000
PACKAGE_NUM = int(np.ceil(BLOCK_SIZE / BYTES_PER_PACKET))


class Link():

    def __init__(self, trace_list, queue_size):
        '''
        :param trace_list: [[time, bandwith, loss_rate, delay] ...]
        :param queue_size:
        '''
        self.trace_list = trace_list
        if len(trace_list) == 0:
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


    def update_trace(self, event_time):

        while len(self.trace_list) > 0 and \
                event_time > self.trace_list[0][0]:
            self.trace_list.pop(0)


    def send_delay(self, event_time):

        rest_block_size = 1
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


class Network():

    def __init__(self, senders, links):
        self.q = []
        self.cur_time = 0.0
        self.senders = senders
        self.links = links
        self.queue_initial_packets()

        self.fir_log = True
        self.log_package_file = "output/pcc_emulator_package.log"


    def queue_initial_packets(self):
        for sender in self.senders:
            sender.register_network(self)
            sender.reset_obs()
            package = sender.new_block(1.0 / sender.rate)
            heapq.heappush(self.q, (1.0 / sender.rate, sender, package))


    def reset(self):
        self.cur_time = 0.0
        self.q = []
        [link.reset() for link in self.links]
        [sender.reset() for sender in self.senders]
        self.queue_initial_packets()


    def get_cur_time(self):
        return self.cur_time


    def run_for_dur(self, dur):
        end_time = self.cur_time + dur
        for sender in self.senders:
            sender.reset_obs()

        while self.cur_time < end_time:
            event_time, sender, package = heapq.heappop(self.q)
            self.log_package(package)

            event_type, next_hop, cur_latency, dropped, life, package_id = package.parse()
            # print("Got event %s, to link %d, latency %f at time %f" % (event_type, next_hop, cur_latency, event_time))
            self.cur_time = event_time
            new_event_time = event_time
            new_event_type = event_type
            new_next_hop = next_hop
            new_latency = cur_latency
            new_dropped = dropped
            push_new_event = False

            if event_type == EVENT_TYPE_ACK:
                # got ack in source or destination
                if next_hop == len(sender.path):
                    if dropped:
                        sender.on_packet_lost()
                        # print("Packet lost at time %f" % self.cur_time)
                    else:
                        sender.on_packet_acked(cur_latency)
                        # print("Packet acked at time %f" % self.cur_time)
                # ack back to source
                else:
                    new_next_hop = next_hop + 1
                    link_latency = sender.path[next_hop].get_cur_latency(self.cur_time)
                    if USE_LATENCY_NOISE:
                        link_latency *= random.uniform(1.0, MAX_LATENCY_NOISE)
                    new_latency += link_latency
                    new_event_time += link_latency
                    push_new_event = True
            if event_type == EVENT_TYPE_SEND:
                if next_hop == 0:
                    # print("Packet sent at time %f" % self.cur_time)
                    if sender.can_send_packet():
                        sender.on_packet_sent()
                        push_new_event = True
                    _package = sender.new_block(self.cur_time + (1.0 / sender.rate))
                    heapq.heappush(self.q, (self.cur_time + (1.0 / sender.rate), sender, _package))

                else:
                    push_new_event = True

                if next_hop == sender.dest:
                    new_event_type = EVENT_TYPE_ACK
                new_next_hop = next_hop + 1

                link_latency = sender.path[next_hop].get_cur_latency(self.cur_time)
                if USE_LATENCY_NOISE:
                    link_latency *= random.uniform(1.0, MAX_LATENCY_NOISE)
                new_latency += link_latency
                new_event_time += link_latency
                new_dropped = not sender.path[next_hop].packet_enters_link(self.cur_time)
                life += link_latency + sender.path[next_hop].extra_delay

            if push_new_event:
                package.next_hop = new_next_hop
                package.package_type = new_event_type
                package.queue_delay = new_latency
                package.drop = new_dropped
                heapq.heappush(self.q, (new_event_time, sender, package))

        sender_mi = self.senders[0].get_run_data()
        throughput = sender_mi.get("recv rate")
        latency = sender_mi.get("avg latency")
        loss = sender_mi.get("loss ratio")
        bw_cutoff = self.links[0].bw * 0.8
        lat_cutoff = 2.0 * self.links[0].dl * 1.5
        loss_cutoff = 2.0 * self.links[0].lr * 1.5
        # print("thpt %f, bw %f" % (throughput, bw_cutoff))
        # reward = 0 if (loss > 0.1 or throughput < bw_cutoff or latency > lat_cutoff or loss > loss_cutoff) else 1 #

        # Super high throughput
        # reward = REWARD_SCALE * (20.0 * throughput / RATE_OBS_SCALE - 1e3 * latency / LAT_OBS_SCALE - 2e3 * loss)

        # Very high thpt
        reward = (10.0 * throughput / (8 * BYTES_PER_PACKET) - 1e3 * latency - 2e3 * loss)

        # High thpt
        # reward = REWARD_SCALE * (5.0 * throughput / RATE_OBS_SCALE - 1e3 * latency / LAT_OBS_SCALE - 2e3 * loss)

        # Low latency
        # reward = REWARD_SCALE * (2.0 * throughput / RATE_OBS_SCALE - 1e3 * latency / LAT_OBS_SCALE - 2e3 * loss)
        # if reward > 857:
        # print("Reward = %f, thpt = %f, lat = %f, loss = %f" % (reward, throughput, latency, loss))

        # reward = (throughput / RATE_OBS_SCALE) * np.exp(-1 * (LATENCY_PENALTY * latency / LAT_OBS_SCALE + LOSS_PENALTY * loss))
        return reward * REWARD_SCALE


    def log_package(self, package):
        '''
        package is tuple of (event_time, sender, event_type, next_hop, cur_latency, dropped, package_id, life)
        :param package: tuple
        :return: package
        '''

        if self.fir_log:
            self.fir_log = False
            with open(self.log_package_file, "w") as f:
                pass

        with open(self.log_package_file, "a") as f:

            f.write(str(package)+"\n")

        return package


class Sender():

    def __init__(self, rate, path, dest, features, cwnd=25, history_len=10):
        self.id = Sender._get_next_id()
        self.starting_rate = rate
        self.rate = rate
        self.sent = 0
        self.acked = 0
        self.lost = 0
        self.bytes_in_flight = 0
        self.min_latency = None
        self.rtt_samples = []
        self.sample_time = []
        self.net = None
        self.path = path
        self.dest = dest
        self.history_len = history_len
        self.features = features
        self.history = sender_obs.SenderHistory(self.history_len,
                                                self.features, self.id)
        self.cwnd = cwnd


    _next_id = 1
    _package_id = 1
    _block_id = 1

    @classmethod
    def _get_next_package(cls):
        result = Sender._package_id
        Sender._package_id += 1
        return result


    @classmethod
    def _get_next_id(cls):
        result = Sender._next_id
        Sender._next_id += 1
        return result


    def new_block(self, cur_time):
        package_id = Sender._get_next_package()
        package = Package(create_time=cur_time,
                          next_hop=0,
                          block_id=package_id // PACKAGE_NUM,
                          package_id=package_id % PACKAGE_NUM,
                          send_delay=1 / self.rate
                          )
        return package


    def apply_rate_delta(self, delta):
        delta *= DELTA_SCALE
        # print("Applying delta %f" % delta)
        if delta >= 0.0:
            self.set_rate(self.rate * (1.0 + delta))
        else:
            self.set_rate(self.rate / (1.0 - delta))


    def apply_cwnd_delta(self, delta):
        delta *= DELTA_SCALE
        # print("Applying delta %f" % delta)
        if delta >= 0.0:
            self.set_cwnd(self.cwnd * (1.0 + delta))
        else:
            self.set_cwnd(self.cwnd / (1.0 - delta))


    def can_send_packet(self):
        if USE_CWND:
            return int(self.bytes_in_flight) / BYTES_PER_PACKET < self.cwnd
        else:
            return True


    def register_network(self, net):
        self.net = net


    def on_packet_sent(self):
        self.sent += 1
        self.bytes_in_flight += BYTES_PER_PACKET


    def on_packet_acked(self, rtt):
        self.acked += 1
        self.rtt_samples.append(rtt)
        if (self.min_latency is None) or (rtt < self.min_latency):
            self.min_latency = rtt
        self.bytes_in_flight -= BYTES_PER_PACKET


    def on_packet_lost(self):
        self.lost += 1
        self.bytes_in_flight -= BYTES_PER_PACKET


    def set_rate(self, new_rate):
        self.rate = new_rate
        # print("Attempt to set new rate to %f (min %f, max %f)" % (new_rate, MIN_RATE, MAX_RATE))
        if self.rate > MAX_RATE:
            self.rate = MAX_RATE
        if self.rate < MIN_RATE:
            self.rate = MIN_RATE


    def set_cwnd(self, new_cwnd):
        self.cwnd = int(new_cwnd)
        # print("Attempt to set new rate to %f (min %f, max %f)" % (new_rate, MIN_RATE, MAX_RATE))
        if self.cwnd > MAX_CWND:
            self.cwnd = MAX_CWND
        if self.cwnd < MIN_CWND:
            self.cwnd = MIN_CWND


    def record_run(self):
        smi = self.get_run_data()
        self.history.step(smi)


    def get_obs(self):
        return self.history.as_array()


    def get_run_data(self):
        obs_end_time = self.net.get_cur_time()

        # obs_dur = obs_end_time - self.obs_start_time
        # print("Got %d acks in %f seconds" % (self.acked, obs_dur))
        # print("Sent %d packets in %f seconds" % (self.sent, obs_dur))
        # print("self.rate = %f" % self.rate)
        # print(self.rtt_samples)
        return sender_obs.SenderMonitorInterval(
            self.id,
            bytes_sent=self.sent * BYTES_PER_PACKET,
            bytes_acked=self.acked * BYTES_PER_PACKET,
            bytes_lost=self.lost * BYTES_PER_PACKET,
            send_start=self.obs_start_time,
            send_end=obs_end_time,
            recv_start=self.obs_start_time,
            recv_end=obs_end_time,
            rtt_samples=self.rtt_samples,
            packet_size=BYTES_PER_PACKET
        )


    def reset_obs(self):
        self.sent = 0
        self.acked = 0
        self.lost = 0
        self.rtt_samples = []
        self.obs_start_time = self.net.get_cur_time()


    def print_debug(self):
        print("Sender:")
        print("Obs: %s" % str(self.get_obs()))
        print("Rate: %f" % self.rate)
        print("Sent: %d" % self.sent)
        print("Acked: %d" % self.acked)
        print("Lost: %d" % self.lost)
        print("Min Latency: %s" % str(self.min_latency))


    def reset(self):
        # print("Resetting sender!")
        self.rate = self.starting_rate
        self.bytes_in_flight = 0
        self.min_latency = None
        self.reset_obs()
        self.history = sender_obs.SenderHistory(self.history_len,
                                                self.features, self.id)


class PccEmulator(object):

    def __init__(self,
                 block_file=None,
                 trace_file=None,
                 queue_range=None):

        self.trace_cols = ("time", "bandwith", "loss_rate", "delay")
        self.queue_range = queue_range if queue_range else (10, 20)
        self.trace_file = trace_file
        self.event_record = { "Events" : [] }

        # unkown params
        self.features = [] # ["send rate", "recv rate"]
        self.history_len = 1
        self.steps_taken = 0

        self.links = None
        self.senders = None
        self.create_new_links_and_senders()
        self.net = Network(self.senders, self.links)


    def get_trace(self):

        trace_list = []
        with open(self.trace_file, "r") as f:
            for line in f.readlines():
                trace_list.append(list(
                    map(lambda x: float(x), line.split(","))
                ))
                if len(trace_list[-1]) != len(self.trace_cols):
                    raise ValueError("Trace file error!\nPlease check its format like : {0}".format(self.trace_cols))

        if len(trace_list) == 0:
            raise ValueError("Trace file error!\nThere is no data in the file!")

        return trace_list


    def create_new_links_and_senders(self):

        self.trace_list = self.get_trace()
        # queue = 1 + int(np.exp(random.uniform(*self.queue_range)))
        # print("queue size : %d" % queue)
        # bw = self.trace_list[0][1]
        bw    = 705 # true bw is bw*BYTES_PER_PACKAGE
        lat   = 0.03
        queue = 5
        loss  = 0.00
        self.links = [Link(self.trace_list, queue)] # , Link(self.trace_list, queue)]
        #self.senders = [Sender(0.3 * bw, [self.links[0], self.links[1]], 0, self.history_len)]
        #self.senders = [Sender(random.uniform(0.2, 0.7) * bw, [self.links[0], self.links[1]], 0, self.history_len)]
        self.senders = [Sender(random.uniform(0.99, 1) * bw, [self.links[0]],
                               0, self.features, history_len=self.history_len, cwnd=25)]


    def run_for_dur(self, during_time):

        # action = [0.9, 0.9]
        # for i in range(len(self.senders)):
        #     self.senders[i].apply_rate_delta(action[0])
        #     if USE_CWND:
        #         self.senders[i].apply_cwnd_delta(action[1])

        reward = self.net.run_for_dur(during_time)
        for sender in self.senders:
            sender.record_run()

        sender_obs = self._get_all_sender_obs()
        sender_mi = self.senders[0].get_run_data()
        event = {}
        event["Name"] = "Step"
        event["Time"] = self.steps_taken
        event["Reward"] = reward
        # event["Target Rate"] = sender_mi.target_rate
        event["Send Rate"] = sender_mi.get("send rate")
        event["Throughput"] = sender_mi.get("recv rate")
        event["Latency"] = sender_mi.get("avg latency")
        event["Loss Rate"] = sender_mi.get("loss ratio")
        event["Latency Inflation"] = sender_mi.get("sent latency inflation")
        event["Latency Ratio"] = sender_mi.get("latency ratio")
        event["Send Ratio"] = sender_mi.get("send ratio")
        # event["Cwnd"] = sender_mi.cwnd
        # event["Cwnd Used"] = sender_mi.cwnd_used
        self.event_record["Events"].append(event)
        if event["Latency"] > 0.0:
            self.run_dur = 0.5 * sender_mi.get("avg latency")

        return event, sender_obs


    def print_debug(self):
        print("---Link Debug---")
        for link in self.links:
            link.print_debug()
        print("---Sender Debug---")
        for sender in self.senders:
            sender.print_debug()


    def reset(self):
        self.steps_taken = 0
        self.net.reset()
        self.create_new_links_and_senders()
        self.net = Network(self.senders, self.links)
        self.episodes_run += 1
        if self.episodes_run > 0 and self.episodes_run % 100 == 0:
            self.dump_events_to_file("pcc_env_log_run_%d.json" % self.episodes_run)
        self.event_record = {"Events": []}
        self.net.run_for_dur(self.run_dur)
        self.net.run_for_dur(self.run_dur)
        self.reward_ewma *= 0.99
        self.reward_ewma += 0.01 * self.reward_sum
        print("Reward: %0.2f, Ewma Reward: %0.2f" % (self.reward_sum, self.reward_ewma))
        self.reward_sum = 0.0
        return self._get_all_sender_obs()


    def close(self):
        if self.viewer:
            self.viewer.close()
            self.viewer = None


    def dump_events_to_file(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.event_record, f, indent=4)


    def _get_all_sender_obs(self):
        sender_obs = self.senders[0].get_obs()
        sender_obs = np.array(sender_obs).reshape(-1, )
        # print(sender_obs)
        return sender_obs


if __name__ == '__main__':

    block_file = "config/block.txt"
    trace_file = "config/trace.txt"
    log_file = "output/pcc_emulator.log"
    log_package_file = "output/pcc_emulator_package.log"

    emulator = PccEmulator(
        block_file=block_file,
        trace_file=trace_file
    )

    print(emulator.run_for_dur(0.5))
    emulator.dump_events_to_file(log_file)
    emulator.print_debug()
    print(emulator.senders[0].rtt_samples)
    analyze_pcc_emulator(log_package_file, trace_file)