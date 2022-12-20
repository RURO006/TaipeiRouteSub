import threading
import time
from api import TdxApi
from datetime import datetime, timezone
from someTool import getSetting, readFile, sendEmail
import json

TaipeiStopOfRoute = json.loads(readFile("data/TaipeiStopOfRoute.json"))


class BusData:
    PlateNumb: str
    Lon: float
    Lat: float
    StopNameZh: str
    StopUID: str
    StopSeq: int
    RouteUID: str
    A2EventType: int
    '''進站離站 : [0:'離站',1:'進站']'''
    RouteNameZh: str
    Direction: int
    GPSTime: str
    BusStatus: int
    '''行車狀況 : [0:'正常',1:'車禍',2:'故障',3:'塞車',4:'緊急求援',5:'加油',90:'不明',91:'去回不明',98:'偏移路線',99:'非營運狀態',100:'客滿',101:'包車出租',255:'未知']'''
    DutyStatus: int
    '''勤務狀態 : [0:'正常',1:'開始',2:'結束']'''


class Subscriber:
    email: str
    routeName: str
    routeDir: int
    stopName: str
    busPlateNumb: str | None
    remindSecond: int = 300
    '''公車小於300秒觸發提醒'''
    remindStopCount: int = 5
    '''公車小於5站觸發提醒'''
    __busPlateNumbDict: dict[str:datetime] = {}
    __plateNumbExpiredSec = 3600
    '''車牌過期時間，當提醒過後會記錄下來不會再次提醒，但超過這個時間會清除，重新提醒
    以防有車牌重新發車'''

    def __init__(self, email: str, routeName: str, routeDir: int, stopName: str, busPlateNumb: str | None):
        self.email = email
        self.routeName = routeName
        self.routeDir = routeDir
        self.stopName = stopName
        self.busPlateNumb = busPlateNumb

    def hasPlateNumb(self, PlateNumb: str) -> bool:
        return PlateNumb in self.__busPlateNumbDict

    def addPlateNumb(self, PlateNumb: str):
        self.__busPlateNumbDict[PlateNumb] = datetime.now(
            timezone.utc).astimezone()

    def clearPlateNumb(self):
        '''超過一定時間，清除已經提醒過的車牌，車牌可能會重新上路，故要清除'''
        now = datetime.now(
            timezone.utc).astimezone()
        for key in self.__busPlateNumbDict:
            if (now-self.__busPlateNumbDict[key]).seconds >= self.__plateNumbExpiredSec:
                del self.__busPlateNumbDict[key]

    def __getRemindMsg(self, busPlateNumb, BusList) -> tuple[int, str]:
        '''取得提醒訊息

        Return
        -------
        [bool, str]:
            [是否有提醒[0:沒動作, 1:觸發提醒, 2:公車已經離開或車站不存在, 3:BusList不包含busPlateNumb], 訊息]
        '''
        if busPlateNumb not in BusList:
            return 3, "找不到公車資料:{}，可能已經停駛、離開路線".format(busPlateNumb)
        filterStop = None
        filterStop = [(i, stop) for i, stop in enumerate(BusList[busPlateNumb])
                      if stop["StopNameZh"] == self.stopName]
        if (len(filterStop) > 0):
            (i, stop) = filterStop[0]
            if (stop["TotalRunTime"] <= self.remindSecond):
                msg = "公車({})即將抵達，大約{:.1f}分鐘後".format(
                    busPlateNumb, stop["TotalRunTime"]/60)
                return 1, msg
            elif i <= self.remindStopCount:
                msg = "公車({})即將抵達，距離這裡還有{}站".format(
                    busPlateNumb, i)
                return 1, msg
            else:
                # 還不需要提醒
                return 0, None
        else:
            msg = "找不到公車對應的車站資料，公車:{} 車站:{}，可能已經離開，或車站不存在".format(
                self.busPlateNumb, self.stopName)
            return 2, msg

    def checkRemind(self, BusList) -> tuple[bool, str, bool]:
        '''檢查是否需要提醒

        Return
        -------
        [bool, str, bool]:
            [是否需要寄信, 訊息, 是否需要刪除]
        '''
        # 特定公車提醒
        if self.busPlateNumb is not None:
            (code, msg) = self.__getRemindMsg(self.busPlateNumb, BusList)
            if code == 1 or code == 2 or code == 3:
                return True, "{}，將會刪除此訂閱".format(msg), True
            else:
                return False, None, False

        # 所有公車提醒
        else:
            for plateNumb in BusList.keys():
                # 已經記錄提醒過就不需要再提醒
                if self.hasPlateNumb(plateNumb):
                    continue

                (code, msg) = self.__getRemindMsg(plateNumb, BusList)
                if code == 1:
                    # 紀錄已經提醒過的車號
                    self.addPlateNumb(plateNumb)
                    return True, "{}".format(msg), False
        return False, None, False


class BusServiceThread(threading.Thread):
    """每隔5秒撈一次資料"""
    perSec: int = 5
    routeList: list
    '''路線所有資料'''

    EstimatedTimeOfArrival: list
    '''預估到站，用不到'''
    RealTimeByFrequency: list
    '''公車即時位置'''
    RealTimeNearStop: list
    '''公車即時所在站牌'''
    RouteToS2STravelTimeMap: dict[str:list] = {}
    '''雜湊表 路線>旅行時間'''

    RouteToBusMap: dict
    '''雜湊表 路線>公車'''

    listSubscriber: list[Subscriber] = []
    '''訂閱的使用者'''

    def __init__(self, ar="defaultName", name=None):
        super().__init__(name=name)
        self.ar = ar
        self.isStop = False
        setting = getSetting()
        app_id = setting['ptxAppId']
        app_key = setting['ptxAppKey']
        self.api = TdxApi(app_id, app_key)
        self.routeList = json.loads(
            readFile("data/noErrorCityStopOfRoute2.json"))

    def run(self):
        # 開始前先執行一次
        self.__work()
        stime = time.time()
        while self.isStop == False:
            # 過了perSec秒之後，執行動作
            if (time.time()-stime >= self.perSec):
                stime += self.perSec
                self.__work()
            time.sleep(0.1)

    def __work(self):
        dateTime = datetime.now(timezone.utc).astimezone()
        print(dateTime.strftime("%Y%m%d%H%M"))
        print("----目前訂閱者: {}人----".format(len(self.listSubscriber)))
        for item in self.listSubscriber:
            print("routeName:{}, dir:{}, stopName:{}, busPlateNumb:{}, email:{}".format(
                item.routeName, item.routeDir, item.stopName, item.busPlateNumb, item.email))
        # print(dateTime.isoformat())
        self.updateData()
        self.__checkSubscriberAndSendEmail()

    def updateData(self):
        '''更新即時公車資料RouteToBusMap'''
        #  到站時間資料，用不到
        # self.EstimatedTimeOfArrival = self.api.getApi(
        #     'https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/Taipei?$format=JSON')
        self.RealTimeByFrequency = self.api.getApi(
            'https://tdx.transportdata.tw/api/basic/v2/Bus/RealTimeByFrequency/City/Taipei?$format=JSON')
        self.RealTimeNearStop = self.api.getApi(
            'https://tdx.transportdata.tw/api/basic/v2/Bus/RealTimeNearStop/City/Taipei?$format=JSON')

        self.RouteToBusMap = {}

        for item in self.RealTimeByFrequency:
            routeNameZh = item["RouteName"]["Zh_tw"]
            if routeNameZh not in self.RouteToBusMap:
                self.RouteToBusMap[routeNameZh] = []
            busData = BusData()
            busData.PlateNumb = item["PlateNumb"]
            busData.RouteUID = item["RouteUID"]
            busData.Direction = item["Direction"]
            busData.DutyStatus = item["DutyStatus"]
            busData.BusStatus = item["BusStatus"]
            busData.Lon = item["BusPosition"]["PositionLon"]
            busData.Lat = item["BusPosition"]["PositionLat"]
            busData.GPSTime = item["GPSTime"]
            busData.RouteNameZh = item["RouteName"]["Zh_tw"]
            # BUG#001 公車明明還活著，狀態也正確，卻不存在RealTimeByFrequency裡面
            busRtns = [rtns for rtns in self.RealTimeNearStop if rtns["PlateNumb"]
                       == busData.PlateNumb]
            if (len(busRtns) == 1):
                busData.StopNameZh = busRtns[0]["StopName"]["Zh_tw"]
                busData.StopUID = busRtns[0]["StopUID"]
                busData.StopSeq = busRtns[0]["StopSequence"]
                busData.A2EventType = busRtns[0]["A2EventType"]
            elif (len(busRtns) > 1):
                raise Exception(
                    "PlateNumb:'{}'，不可能發生，公車同時出現在兩個站，量子公車？".format(busData.PlateNumb))
            else:
                # 略過不存在的公車
                continue

            self.RouteToBusMap[routeNameZh].append({
                "PlateNumb": busData.PlateNumb,
                "Lon": busData.Lon,
                "Lat": busData.Lat,
                "StopNameZh": busData.StopNameZh,
                "StopUID": busData.StopUID,
                "StopSeq": busData.StopSeq,
                "A2EventType": busData.A2EventType,
                "RouteUID": busData.RouteUID,
                "RouteNameZh": busData.RouteNameZh,
                "Direction": busData.Direction,
                "GPSTime": busData.GPSTime,
                "BusStatus": busData.BusStatus,
                "DutyStatus": busData.DutyStatus,
            })

    def __checkSubscriberAndSendEmail(self):
        '''檢查所有訂閱者，如果有到站提醒則寄信，如果有錯誤資料則清除'''
        # 暫存旅行時間(整理過)，同一條路線不需要再處理
        routeNameToBusTT = {}
        # 儲存無效訂閱者
        deleteListSubscriber = []
        for item in self.listSubscriber:
            key = "{}_{}".format(item.routeName, item.routeDir)
            if (key in routeNameToBusTT):
                busTravelTime = routeNameToBusTT[key]
            else:
                busTravelTime = routeNameToBusTT[key] = self.getBusTravelTime(
                    item.routeName, item.routeDir)
            (needRemind, msg, needDelete) = item.checkRemind(
                busTravelTime["BusList"])

            if needRemind:
                print("email:{}".format(item.email))
                print("msg:{}".format(msg))
                sendEmail(item.email, msg)
            if needDelete:
                # 儲存到無效訂閱者，成功寄信，
                deleteListSubscriber.append(item)

            item.clearPlateNumb()

        try:
            # 刪除無效的Subscriber
            for item in deleteListSubscriber:
                self.listSubscriber.remove(item)
        except:
            pass

    def __getBusList(self, routeName, Dir) -> list[dict]:
        '''取得公車資料'''
        if (routeName in self.RouteToBusMap):
            return [bus for bus in self.RouteToBusMap[routeName] if bus["Direction"] == Dir]
        else:
            return None

    def __getTravelTimes(self, RouteID, Dir):
        '''取得旅行時間，一條路線只會去API抓一次，之後會存在記憶體'''
        if RouteID in self.RouteToS2STravelTimeMap:
            S2STravelTime = self.RouteToS2STravelTimeMap[RouteID]
        else:
            S2STravelTime = self.RouteToS2STravelTimeMap[RouteID] = self.api.getApi(
                "https://tdx.transportdata.tw/api/basic/v2/Bus/S2STravelTime/City/Taipei/{}?$format=JSON&".format(RouteID))

        filterS2STT = [item for item in S2STravelTime if item["Direction"]
                       == 2 or item["Direction"] == Dir]

        if len(filterS2STT) > 0:
            dateTime = datetime.now(timezone.utc).astimezone()
            hour = dateTime.hour
            weekday = (dateTime.weekday() + 1) % 7
            S2STravelTime = filterS2STT[0]
            filterTT = [item for item in S2STravelTime["TravelTimes"] if item["Weekday"] ==
                        weekday and hour >= item["StartHour"] and hour < item["EndHour"]]
            if len(filterTT) > 0:
                return filterTT[0]
            else:
                return None
        else:
            return None

    def getBusTravelTime(self, routeName, dir):
        '''取得公車旅行時間，整理過後的資料

        Return
        ------
        {
            公車清單
            BusList: dict
            {
                "公車車牌": [
                    {
                        站牌ID
                        "StopID": str,

                        站牌中文名
                        "StopNameZh": str,

                        站序
                        "StopSeq": int, 

                        預估到達時間(秒)
                        "TotalRunTime": int 
                    }
                ]
            }

        }
        '''
        global TaipeiStopOfRoute
        findRoutes = [r for r in TaipeiStopOfRoute if r["RouteName"]
                      ["Zh_tw"] == routeName and r["Direction"] == dir]
        nowTime = datetime.now(timezone.utc).astimezone()
        Route = None
        busList = None
        TravelTimes = None
        if (len(findRoutes) > 0):
            Route = findRoutes[0]
            busList: list[dict] = self.__getBusList(routeName, dir)
            TravelTimes = self.__getTravelTimes(Route["RouteID"], dir)
        else:
            return {"Msg": "找不到路線", "DateTime": nowTime.isoformat()}, 404

        if (busList is None or len(busList) == 0):
            return {"Msg": "該路線沒有公車", "DateTime": nowTime.isoformat()}, 404
        if (TravelTimes is None or len(TravelTimes) == 0):
            return {"Msg": "該路線沒有旅行時間", "DateTime": nowTime.isoformat()}, 404

        OUT = {}
        OUT["BusList"] = {}
        nowTime = datetime.now(timezone.utc).astimezone()
        for busData in busList:
            OUT["BusList"][busData["PlateNumb"]] = []
        for i in range(0, len(Route["Stops"])-1):
            stop = Route["Stops"][i]
            nextStop = Route["Stops"][i+1]
            for busData in busList:
                PlateNumb = busData["PlateNumb"]
                oneBus = OUT["BusList"][PlateNumb]
                busGpsTime = datetime.fromisoformat(busData["GPSTime"])
                offTime = nowTime-busGpsTime
                if busData["StopSeq"] < nextStop["StopSequence"]:
                    filterTT = [tt for tt in TravelTimes["S2STimes"] if tt["FromStopID"] == stop["StopID"]
                                and tt["ToStopID"] == nextStop["StopID"]]
                    if (len(filterTT) > 0):
                        RunTime = filterTT[0]["RunTime"]
                        totalTime = 0
                        if (len(oneBus) > 0):
                            totalTime = oneBus[-1]["TotalRunTime"]

                        oneBus.append({
                            "StopID": nextStop["StopID"],
                            "StopNameZh": nextStop["StopName"]["Zh_tw"],
                            "StopSeq": nextStop["StopSequence"],
                            "TotalRunTime": totalTime+RunTime-offTime.seconds
                        })
                    else:
                        return {"Msg": "找不到旅行時間表: FromStopID:{}, ToStopID:{}".format(stop["StopID"], nextStop["StopID"]), "DateTime": nowTime.isoformat()}, 404
        return OUT

    def addSubscriber(self, subscriber: Subscriber):
        '''新增訂閱者'''
        self.listSubscriber.append(subscriber)

    def hasSubscriber(self, email: str) -> bool:
        '''訂閱者是否存在'''
        return len([item for item in self.listSubscriber if item.email == email]) > 0

    def removeSubscriber(self, email: str):
        '''刪除訂閱者'''
        self.listSubscriber = [
            item for item in self.listSubscriber if item.email != email]

    def close2(self):
        '''關閉迴圈'''
        self.isStop = True


if __name__ == '__main__':
    thread1 = BusServiceThread()
    thread1.start()
    try:
        a = input("輸入離開")
    except Exception as e:
        print("{}".format(e))
    except KeyboardInterrupt:
        print("使用者中止")
    finally:
        thread1.close2()
        print("finally")
