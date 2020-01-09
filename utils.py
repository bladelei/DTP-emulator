#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : utils
# @Function : 
# @Author : azson
# @Time : 2020/1/8 15:59
'''

import time


def get_ms_time(rate=1000):

    return time.time()*rate


class Block(object):

    def __init__(self,
                 bytes_size=200000,
                 deadline=200,
                 timestamp=None):

        self.size = bytes_size
        self.deadline = deadline
        self.timestamp = timestamp if timestamp else get_ms_time()

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


def lower_bound(arr, x, key=None):

    if not key:
        key = lambda x : x

    left = 0
    right = len(arr)-1
    mid = -1
    if arr[left] > x :
        return mid

    while left <= right :
        mid = int(left + (right - left + 1) / 2)
        if left == right and right == mid or x == key(arr[mid]):
            return mid
        if x > key(arr[mid]):
            left = mid
        elif x < key(arr[mid]):
            right = mid - 1

    return mid



if __name__ == '__main__':

    obj = Block()

    print(obj)