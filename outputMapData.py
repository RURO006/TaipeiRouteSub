
from someTool import writeToFile, readFile
import json
import re
from Line import MyLine
from Point import Point


def getPointList(pointListStr):
    regex = '(?:(?P<x>[^, ]+) (?P<y>[^, ]+)),?'
    matchs = re.finditer(regex, pointListStr)
    OUT = []
    for m in matchs:
        # print("{},{}".format(m.group('x'), m.group('y')))
        OUT.append({
            "x": float(m.group('x')),
            "y": float(m.group('y'))
        })
    return OUT


def getCsv(geometryText):
    regex = '\((?P<oneLine>[^()]*)\)'
    matchs = re.finditer(regex, geometryText)
    OUT = []
    # while match != None:
    for m in matchs:
        points = getPointList(m.group('oneLine'))
        OUT.extend(points)
    return OUT


# 輸出Shap資料
# TaipeiShap = json.loads(readFile("data/TaipeiShap.json"))
# for item in TaipeiShap:
#     if item["RouteID"] == '10241':
#         POINTS = getCsv(item['Geometry'])
# heads = "WKT,名稱,說明\n"
# pointsCsv = "\n".join("POINT({} {}),{},".format(
#     poi['x'], poi['y'], idx+1) for idx, poi in enumerate(POINTS))
# lineStringCsv = "\"LINESTRING({})\",藍36,".format(
#     ",".join("{} {}".format(
#         poi['x'], poi['y']) for poi in POINTS)
# )
# writeToFile("data/藍36-point.csv", heads+pointsCsv)

# writeToFile("data/藍36-lineString.csv", heads+lineStringCsv)


# # 輸出StopOfRoute672
# StopOfRoute = json.loads(readFile("data/StopOfRoute672.json"))
# route672 = filter(lambda a: a['RouteID'] == '10785', StopOfRoute)
# route672_2 = [a for a in StopOfRoute if a['RouteID'] == '10785']

# for route in route672_2:
#     dir = route['Direction']
#     heads = "WKT,名稱,說明\n"
#     pointsCsv = "\n".join("POINT({} {}),{},".format(
#         poi['StopPosition']['PositionLon'], poi['StopPosition']['PositionLat'], poi['StopName']['Zh_tw']) for idx, poi in enumerate(route['Stops']))
#     writeToFile("data/StopOfRoute672-{}-point.csv".format(dir),
#                 heads+pointsCsv)

# 輸出錯誤的路線，Geometry不是LINESTRING的路線
errorRoute = []
cityShap = json.loads(readFile("data/TaipeiShap.json"))
for item in cityShap:
    if not item["Geometry"].startswith("LINESTRING"):
        name = item["RouteName"]["Zh_tw"]
        routeUID = item["RouteUID"]
        errorRoute.append({"NameZh": name, "RouteUID": routeUID})
        print(name)

writeToFile("data/ErrorRouteShap.json", errorRoute)

# 輸出錯誤的路線，沒有Shap
errorRoute = []
cityShap = json.loads(readFile("data/TaipeiShap.json"))
cityStopOfRoute = json.loads(readFile("data/TaipeiStopOfRoute.json"))
for item in cityStopOfRoute:
    if item["RouteUID"] not in [s["RouteUID"] for s in cityShap]:
        name = item["RouteName"]["Zh_tw"]
        routeUID = item["RouteUID"]
        errorRoute.append({"NameZh": name, "RouteUID": routeUID})
        print(name)

writeToFile("data/ErrorRouteNoShap.json", errorRoute)

# 輸出Route線型的Map檔
errorShap = json.loads(readFile("data/ErrorRouteShap.json"))
cityShap = json.loads(readFile("data/TaipeiShap.json"))
cityStopOfRoute = json.loads(readFile("data/TaipeiStopOfRoute.json"))
# 排除錯誤路線
cityShap = [s for s in cityShap if s["RouteUID"]
            not in [e["RouteUID"] for e in errorShap]]
cityShapMap = {}
for item in cityShap:
    if (item["RouteUID"] in cityShapMap):
        print(item["RouteUID"])
        print(item["RouteName"]["Zh_tw"])
    else:
        print(item["RouteUID"])
        cityShapMap[item["RouteUID"]] = getCsv(item["Geometry"])
writeToFile("data/TaipeiShapMap.json", cityShapMap)


# 輸出錯誤路線
cityShapMap = json.loads(readFile("data/TaipeiShapMap.json"))
cityStopOfRoute = json.loads(readFile("data/TaipeiStopOfRoute.json"))
errorShap = json.loads(readFile("data/ErrorRouteShap.json"))
errorRoute2 = json.loads(readFile("data/ErrorRouteNoShap.json"))
noErrorCityStopOfRoute = []
for item in cityStopOfRoute:
    if (item["RouteUID"] not in cityShapMap and (item["RouteUID"] in [s["RouteUID"] for s in errorShap] or item["RouteUID"] in [s["RouteUID"] for s in errorRoute2])):
        continue
    if (item["RouteUID"] not in cityShapMap):
        print(item["RouteUID"])
        continue
    item["Shap"] = cityShapMap[item["RouteUID"]]
    noErrorCityStopOfRoute.append(item)

# TODO: 計算車站跟路線是否有正確前進
errorStopIdx = []
count = 0
preProccess = ""
for item in noErrorCityStopOfRoute:
    points = [Point(p['x'], p['y']) for p in item['Shap']]
    prePointIdx = -1
    for stop in item['Stops']:
        x = stop['StopPosition']['PositionLon']
        y = stop['StopPosition']['PositionLat']
        neaerP = MyLine.getNearestPointFromPoints(Point(x, y), points)
        if (prePointIdx > neaerP.index):
            errorStopIdx.append({
                "RouteUID": item["RouteUID"],
                "dir": item["Direction"]
            })
            break
        prePointIdx = neaerP.index
        stop['PointOfRoute'] = {
            "point": {
                "x": neaerP.point.x,
                "y": neaerP.point.y
            },
            "index": neaerP.index
        }
    # 顯示進度
    count += 1
    nowProccess = "{:3.0f}%".format(count/len(noErrorCityStopOfRoute)*100)
    if (nowProccess != preProccess):
        print(nowProccess)
        preProccess = nowProccess
writeToFile("data/errorStopIdxOfRoute.json", errorStopIdx)
writeToFile("data/noErrorCityStopOfRoute.json", noErrorCityStopOfRoute)


# 計算所有路線每站到下一站的距離(公尺)
noErrorCityStopOfRoute = json.loads(
    readFile("data/noErrorCityStopOfRoute.json"))
for item in noErrorCityStopOfRoute:
    points = [Point(p['x'], p['y']) for p in item['Shap']]
    for i in range(0, len(item['Stops'])-1):
        stop = item['Stops'][i]
        stopPOR = item['Stops'][i]["PointOfRoute"]
        nextStopPOR = item['Stops'][i+1]["PointOfRoute"]
        totalDis = 0
        # 如果兩站的點在同一條線上，直接取直線距離
        if (stopPOR['index'] == nextStopPOR['index']):
            totalDis = Point.Dis(stopPOR["point"]['x'], stopPOR["point"]['y'],
                                 nextStopPOR["point"]['x'], nextStopPOR["point"]['y'])
        else:
            # Stop起點到Shap終點的距離
            totalDis += Point.Dis(stopPOR["point"]['x'], stopPOR["point"]['y'],
                                  item["Shap"][stopPOR['index']+1]["x"], item["Shap"][stopPOR['index']+1]["y"])
            # Stop終點到Shap起點的距離
            totalDis += Point.Dis(nextStopPOR["point"]['x'], nextStopPOR["point"]['y'],
                                  item["Shap"][nextStopPOR['index']]["x"], item["Shap"][nextStopPOR['index']]["y"])

            # Shap中間的線
            for i in range(stopPOR['index']+1, nextStopPOR['index']):
                newDis = Point.Dis(item["Shap"][i]["x"], item["Shap"][i]["y"],
                                   item["Shap"][i+1]["x"], item["Shap"][i+1]["y"])
                totalDis += newDis
        stop["nextStopDis"] = totalDis

writeToFile("data/noErrorCityStopOfRoute2.json", noErrorCityStopOfRoute)
