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

from utils import (
    analyze_pcc_emulator, get_emulator_info
)
from objects.sender import Sender
from objects.link import Link

from congestion_control_algorithm import Solution
from config.constant import *

class Engine():

    def __init__(self, senders, links):
        self.q = []
        self.cur_time = 0.0
        self.senders = senders
        self.links = links
        self.queue_initial_packets()

        self.fir_log = True
        self.log_packet_file = "output/pcc_emulator_packet.log"


    def queue_initial_packets(self):
        for sender in self.senders:
            sender.register_network(self)
            sender.reset_obs()
            packet = sender.new_packet(1.0 / sender.rate)
            if packet:
                heapq.heappush(self.q, (1.0 / sender.rate, sender, packet))


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
            queue_item = heapq.heappop(self.q)
            if queue_item is None:
                print("There is no packet from application~")
                exit(0)

            event_time, sender, packet = queue_item
            self.log_packet(event_time, packet)
            self.append_cc_input(*queue_item)

            event_type, next_hop, cur_latency, dropped, life, packet_id = packet.parse()
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
                        sender.on_packet_acked(cur_latency, packet)
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
                    _packet = sender.new_packet(self.cur_time + (1.0 / sender.rate))
                    if _packet:
                        heapq.heappush(self.q, (self.cur_time + (1.0 / sender.rate), sender, _packet))

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
                packet.next_hop = new_next_hop
                packet.packet_type = new_event_type
                packet.queue_delay = new_latency
                packet.drop = new_dropped
                heapq.heappush(self.q, (new_event_time, sender, packet))

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


    def log_packet(self, event_time, packet):
        '''
        packet is tuple of (event_time, sender, event_type, next_hop, cur_latency, dropped, packet_id, life)
        :param packet: tuple
        :return: Packet
        '''

        if self.fir_log:
            self.fir_log = False
            with open(self.log_packet_file, "w") as f:
                pass

        log_data = { "Time" : event_time }
        log_data.update(packet.trans2dict())

        with open(self.log_packet_file, "a") as f:
            f.write(str(log_data)+"\n")

        return packet


    def append_cc_input(self, event_time, sender, packet, event_type="packet"):

        if event_type == "packet":
            data = {
                "event_time" : event_time,
                "link_rate" : -1 if packet.next_hop == 0 else sender.path[packet.next_hop-1].bw,
                "send_rate" : sender.rate,
                "packet" : packet.trans2dict()
            }
        elif event_type == "system":
            data = {

            }

        sender.solution.input_list.append(data)


class PccEmulator(object):

    def __init__(self,
                 block_file=None,
                 trace_file=None,
                 queue_range=None):

        self.trace_cols = ("time", "bandwith", "loss_rate", "delay")
        self.queue_range = queue_range if queue_range else (10, 20)
        self.trace_file = trace_file
        self.block_file = block_file
        self.event_record = { "Events" : [] }

        # unkown params
        self.features = [] # ["send rate", "recv rate"]
        self.history_len = 1
        self.steps_taken = 0

        self.links = None
        self.senders = None
        self.create_new_links_and_senders()
        self.net = Engine(self.senders, self.links)

        # for player
        self.solution = Solution()


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
        bw    = 705 # true bw is bw*BYTES_PER_PACKET
        lat   = 0.03
        queue = 5
        loss  = 0.00
        self.links = [Link(self.trace_list, queue) , Link(self.trace_list, queue)]
        #self.senders = [Sender(0.3 * bw, [self.links[0], self.links[1]], 0, self.history_len)]
        #self.senders = [Sender(random.uniform(0.2, 0.7) * bw, [self.links[0], self.links[1]], 0, self.history_len)]
        self.senders = [Sender([self.links[0], self.links[1] ], 0, self.features,
                               history_len=self.history_len, solution=Solution())]
        for item in self.senders:
            item.init_application(self.block_file)


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
        event = get_emulator_info(sender_mi)
        event["reward"] = reward
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
        self.net = Engine(self.senders, self.links)
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
    log_packet_file = "output/pcc_emulator_packet.log"

    emulator = PccEmulator(
        block_file=block_file,
        trace_file=trace_file
    )

    print(emulator.run_for_dur(0.5))
    emulator.dump_events_to_file(log_file)
    emulator.print_debug()
    print(emulator.senders[0].rtt_samples)
    print(emulator.senders[0].application.ack_blocks)
    analyze_pcc_emulator(log_packet_file, trace_file)