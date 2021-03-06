from config.constant import *
from common import sender_obs
from utils import check_solution_format
from objects.application import Appication_Layer


class Sender():

    def __init__(self, path, dest, features, history_len=10, solution=None):
        self.id = Sender._get_next_id()
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

        self.solution = solution
        ret = check_solution_format(self.solution.make_decision())
        self.rate = ret["send_rate"]
        self.cwnd = ret["cwnd"]
        self.starting_rate = self.rate

        self.application = None


    _next_id = 1

    @classmethod
    def _get_next_id(cls):
        result = Sender._next_id
        Sender._next_id += 1
        return result


    def init_application(self, block_file):
        self.application = Appication_Layer(block_file, BYTES_PER_PACKET)


    def new_packet(self, cur_time):
        packet = self.application.get_next_packet(cur_time)
        if packet:
            packet.send_delay = 1 / self.rate

        return packet


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
            ret = self.solution.make_decision()
            self.rate, self.cwnd = ret["send_rate"], ret["cwnd"]
            return int(self.bytes_in_flight) / BYTES_PER_PACKET < self.cwnd
        else:
            return True


    def register_network(self, net):
        self.net = net


    def on_packet_sent(self):
        self.sent += 1
        self.bytes_in_flight += BYTES_PER_PACKET


    def on_packet_acked(self, rtt, packet):
        self.acked += 1
        self.rtt_samples.append(rtt)
        if (self.min_latency is None) or (rtt < self.min_latency):
            self.min_latency = rtt
        self.bytes_in_flight -= BYTES_PER_PACKET
        self.application.update_block_status(packet)


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