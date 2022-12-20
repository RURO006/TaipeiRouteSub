# class裡使用自己時，會無法辨識，需加這段
from __future__ import annotations

import math
from typing import TypedDict
from Point import Point
import sys


class MyLine:
    x1: float
    '''線的起始點x1'''
    y1: float
    '''線的起始點y1'''
    x2: float
    '''線的結束點x2'''
    y2: float
    '''線的結束點y2'''
    dx: float
    '''x向量'''
    dy: float
    '''y向量'''
    m: float
    '''斜率=dy/dx'''
    c: float
    '''常數=-m*x1+y1'''
    vM: float
    '''垂直線斜率'''
    vC1: float
    '''起始點的垂直線常數'''
    vC2: float
    '''結束點的垂直線常數'''
    rotation: float | None
    '''方向角'''
    dis: float
    '''距離(線的長度)(單位:公尺)'''

    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        '''直線上的兩點(x1,y1)->(x2,y2)

        Parameters
        ----------
        x1, y1 : float
            直線的起始點

        x2, y2 : float
            直線的結束點
        '''
        # 直線上的兩點(x1,y1)->(x2,y2)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        # x向量
        self.dx = x2 - x1
        # y向量
        self.dy = y2 - y1
        # 斜率=dy/dx
        # 等於0時，設定極小值
        if self.dx == 0:
            self.dx = 1e-8
        if self.dy == 0:
            self.dy = 1e-8
        self.m = self.dy / self.dx
        # 常數=-m*x1+y1
        self.c = -self.m * x1 + y1
        # 直線上兩端點的垂直線的斜率m跟常數c，isProjectedOnLine會用到
        # 垂直線斜率
        self.vM = self.dx / self.dy
        # 兩端點的垂直線常數vC1、vC2
        self.vC1 = self.vM * x1 + y1
        self.vC2 = self.vM * x2 + y2
        # 方向角 0~360
        self.rotation = 0
        # 距離
        self.dis = 0

    def lineFunction(self, x: float, y: float) -> float:
        '''將點(x,y)帶入直線方程式(-m*x+y-c)'''
        return -self.m * x + y - self.c

    def isProjectedOnLine(self, x: float, y: float) -> bool:
        '''將點(x,y)代入直線兩端的垂直線方程式後所得到的結果相乘，若小於等於0代表點在兩端中間，否則是在兩端外面，true:投影點在線上，false:投影點在線外

        Parameters
        ----------
        x, y : float
            座標系上的某個點

        Return
        ----------
        True: 投影點在線上

        False: 投影點在線外

        '''
        # ans1、ans2: 將點代入直線兩端的垂直線方程式後所得到的結果
        # 直線方程式結果的特性，0:在線上、正數:在某一邊、負數:在正數的另一邊
        # 所以ans1和ans2如果符號相反，就代表點在兩條垂直線中間
        # 代表點在的投影點可以在直線上
        func = self.vM * x + y
        ans1 = func - self.vC1
        ans2 = func - self.vC2
        return ans1 * ans2 <= 0

    def disOfPoint(self, x: float, y: float) -> float:
        '''點到線的距離(公尺)

        Parameters
        ----------
        x, y : float
            座標系上的某個點
        '''
        a = abs(self.lineFunction(x, y))
        b = math.sqrt(self.m * self.m + 1)
        # 經緯度轉公尺大約等於 111000*經緯度=公尺
        return a / b * 111000

    def projectedPoints(self, x: float, y: float) -> Point:
        '''最短距離的投影點'''
        # m*x-y+c=0
        a = self.m * self.m  # a*a
        b = 1  # b*b
        c = -self.m  # a*b
        d = self.c * self.m  # a*c
        e = -self.c  # b*c
        f = a + b  # a*a+b*b
        return Point((b * x - c * y - d) / f, (a * y - c * x - e) / f)

    def getRotation(self) -> float:
        '''取得直線方向角0~360'''
        if (self.rotation is None):
            self.rotation = (
                (((math.Atan2(self.dx, self.dy)) / math.PI * 180) + 360) % 360)
        return self.rotation

    def getDis(self) -> float:
        '''取得距離(公尺)'''
        if (self.dis is None):
            self.dis = Point.Dis(self.x1, self.y1, self.x2, self.y2)
        return self.dis

    def SubRotation(self, line: MyLine) -> float:
        '''角度相減:r1-r2'''
        dr = -1
        if (line is not None):
            dr = (360 + self.getRotation() - line.getRotation()) % 360
        return dr

    @staticmethod
    def getNearestPointFromPoints(p: Point, points: list[Point]) -> NearestPoint | None:
        '''從線段(points)找投影點

        Return
        ----------
        point: 投影點

        index: 投影點所在的points位置，紀錄頭的位置
        '''
        if (len(points) == 0):
            return None
        minDis: float = p.disFromPoint(points[0])
        minPoint: Point = points[0]
        minIdx = 0
        for i in range(0, len(points)-1):
            lng1 = points[i].x
            lat1 = points[i].y
            lng2 = points[i + 1].x
            lat2 = points[i + 1].y
            line = MyLine(lng1, lat1, lng2, lat2)
            dis: float
            point: Point | None = None
            # 投影點在線外就找求端點的距離
            if (not line.isProjectedOnLine(p.x, p.y)):
                dis = p.disFromXY(lng2, lat2)
                point = Point(lng2, lat2)
            else:
                dis = line.disOfPoint(p.x, p.y)
            if (minDis > dis):
                minDis = dis
                minIdx = i
                # 投影點在線外
                if (point is not None):
                    minPoint = point
                # 投影點在線上
                else:
                    minPoint = line.projectedPoints(p.x, p.y)
        return NearestPoint(minPoint, minIdx)

    @staticmethod
    def getNearestPointFromLines(p: Point, lines: list[MyLine]) -> NearestPoint | None:
        '''找最近的路線、投影點
        
        Return
        ----------
        lines: 投影點

        index: 投影點所在的points位置，紀錄頭的位置'''
        minDis = sys.float_info.max
        if (len(lines) == 0):
            return None
        minPoint = Point(lines[0].x1, lines[0].y1)
        minDis = p.disFromPoint(minPoint)
        for i in range(0, len(lines)-1):
            lng1 = lines[i].x1
            lat1 = lines[i].y1
            lng2 = lines[i].x2
            lat2 = lines[i].y2
            line = lines[i]
            dis: float
            point: Point | None = None
            # 投影點在線外就找求端點的距離
            if (not line.isProjectedOnLine(p.x, p.y)):
                dis = p.Dis(lng2, lat2)
                point = Point(lng2, lat2)
            else:
                dis = line.disOfPoint(p.x, p.y)
            if (minDis > dis):
                minDis = dis
                # 投影點在線外
                if (point is not None):
                    minPoint = point
                # 投影點在線上
                else:
                    minPoint = line.projectedPoints(p.x, p.y)
        return minPoint


class NearestPoint(dict):
    point: Point
    index: int

    def __init__(self, point, index):
        super().__init__()
        self.point = point
        self.index = index
