class Solution(object):

    def __init__(self):
        self.input_list = []
        self.call_nums = 0

    def make_decision(self):
        self.call_nums += 1
        output = {
            "cwnd" : 10,
            "send_rate" : 700
        }

        if self.call_nums <= 3:
            print(self.input_list)

        return output