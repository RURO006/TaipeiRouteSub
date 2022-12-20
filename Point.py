# class裡使用自己時，會無法辨識，需加這段
from __future__ import annotations

import math


class Point:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> None:
        '''點的座標

        Parameters
        ----------
        x: float
        y: float
        '''
        self.x = x
        self.y = y

    def disFromPoint(self, p: Point) -> float:
        '''兩點距離(公尺)'''
        return self.disFromXY(p.x, p.y)

    def disFromXY(self, x: float, y: float) -> float:
        '''兩點距離(公尺)'''
        dx = x - self.x
        dy = y - self.y
        return math.sqrt(dx * dx + dy * dy) * 111000

    @staticmethod
    def Dis(x1: float, y1: float, x2: float, y2: float) -> float:
        '''兩點距離(公尺)'''
        dx = x1 - x2
        dy = y1 - y2
        return math.sqrt(dx * dx + dy * dy) * 111000
