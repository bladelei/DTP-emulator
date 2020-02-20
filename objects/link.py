#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
# @ModuleName : link
# @Function : 
# @Author : azson
# @Time : 2020/2/19 14:17
'''



class Link(object):

    def __init__(self,
                 download_rate_MB=20,
                 upload_rate_MB=20,
                 loss_rate=.0,
                 propagation_rate=3*10**8):

        self.download_rate_MB = download_rate_MB
        self.upload_rate_MB = upload_rate_MB
        self.loss_rate = loss_rate
        self.propagation_rate = propagation_rate


if __name__ == '__main__':
    pass