from objects.block import Block
from objects.packet import Packet
import numpy as np

class Appication_Layer(object):


    def __init__(self,
                 block_file,
                 bytes_per_packet=1500):
        self.block_file = block_file
        self.block_queue = []
        self.bytes_per_packet = bytes_per_packet

        self.block_nums = None
        self.split_nums = 0
        self.init_time = .0
        self.pass_time = .0
        self.fir_log = True

        self.now_block = None
        self.now_block_offset = 0
        self.head_per_packet = 20

        self.create_block_by_file()
        self.ack_blocks = {}


    def create_block_by_file(self, det=1):
        with open(self.block_file, "r") as f:
            self.block_nums = int(f.readline())

            pattern_cols = ["type", "size", "ddl"]
            pattern=[]
            for line in f.readlines():
                pattern.append(
                    { pattern_cols[idx]:item.strip() for idx, item in enumerate(line.split(',')) }
                )

            peroid = len(pattern)
            for idx in range(self.block_nums):
                ch = idx % peroid
                block = Block(bytes_size=float(pattern[ch]["size"]),
                              block_id=idx,
                              deadline=float(pattern[ch]["ddl"]),
                              timestamp=self.init_time+self.pass_time+idx*det,
                              priority=pattern[ch]["type"])
                self.block_queue.append(block)


    def select_block(self):

        def is_better(block):
            return (now_time - block.timestamp) * best_block.deadline > \
                    (now_time - best_block.timestamp) * block.deadline


        now_time = self.init_time + self.pass_time
        best_block = None
        ch = -1
        need_filter = []
        for idx, item in enumerate(self.block_queue):
            # if miss ddl in queue, clean and log
            if now_time > item.timestamp + item.deadline:
                self.block_queue[idx].miss_ddl = 1
                self.log_block(self.block_queue[idx])
                need_filter.append(idx)
                print(now_time, item.timestamp, item.deadline)

            elif best_block == None or is_better(item) :
                best_block = item
                ch = idx

        # filter block with missing ddl
        for idx in range(len(need_filter)-1, -1, -1):
            if ch != -1 and ch > idx:
                self.block_queue.pop(ch)
                ch = -1
            self.block_queue.pop(need_filter[idx])
        if ch != -1:
            self.block_queue.pop(ch)
        return best_block


    def get_retrans_packet(self):
        for key, val in self.ack_blocks.items():
            if len(val) == self.split_nums:
                continue
            for i in range(self.split_nums):
                if i not in val:
                    return i
        return None


    def get_next_packet(self, cur_time):
        self.pass_time = cur_time
        retrans_packet = None
        if self.now_block is None or self.now_block_offset == self.split_nums:
            # 1. the retransmisson time is bad, which may cause consistently loss packet
            # 2. the packet will be retransmission many times for a while
            retrans_packet = self.get_retrans_packet()
            if retrans_packet:
                self.now_block_offset = retrans_packet
            else:
                self.now_block = self.select_block()
                if self.now_block is None:
                    return None

                self.now_block_offset = 0
                self.split_nums = int(np.ceil(self.now_block.size / self.bytes_per_packet))

        payload = self.bytes_per_packet - self.head_per_packet
        if self.now_block.size % (self.bytes_per_packet - self.head_per_packet) and \
                self.now_block_offset == self.split_nums - 1:
            payload = self.now_block.size % (self.bytes_per_packet - self.head_per_packet)

        packet = Packet(create_time=cur_time,
                          next_hop=0,
                          block_id=self.now_block.block_id,
                          offset=self.now_block_offset,
                          packet_size=self.bytes_per_packet,
                          payload=payload
                          )
        if retrans_packet is None:
            self.now_block_offset += 1
        else:
            self.now_block_offset = self.split_nums

        return packet


    def update_block_status(self, packet):
        if packet.block_id not in self.ack_blocks:
            self.ack_blocks[packet.block_id] = [packet.offset]
        else:
            self.ack_blocks[packet.block_id].append(packet.offset)

    # todo : Adjust log time and content
    def log_block(self, block):

        if self.fir_log:
            self.fir_log = False
            with open("output/block.log", "w") as f:
                pass

        block.finish_timestamp = self.init_time + self.pass_time
        if block.get_cost_time() > block.deadline:
            block.miss_ddl = 1

        with open("output/block.log", "a") as f:
            f.write(str(block)+'\n')


    def analyze_application(self):
        pass