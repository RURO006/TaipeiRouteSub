from flask import Flask
from BusService import BusServiceThread, Subscriber


app = Flask(__name__)


busService = BusServiceThread()
busService.start()


@app.route("/getTravelTime/<routeName>/<dir>")
def getTravelTime(routeName, dir):
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
    dir = int(dir)
    print("routeName:{}, dir:{}".format(routeName, dir))
    OUT = busService.getBusTravelTime(routeName, dir)
    if type(OUT).__name__ == "dict":
        print("Good")
    else:
        print("Bad")
    return OUT


@app.route("/subscribe/<routeName>/<int:dir>/<stopName>/<email>", methods=['GET'])
@app.route("/subscribe/<routeName>/<int:dir>/<stopName>/<email>/<busPlateNumb>", methods=['GET'])
def addSubscribe(routeName, dir, stopName, email, busPlateNumb=None):
    dir = int(dir)
    busService.addSubscriber(Subscriber(
        email, routeName, dir, stopName, busPlateNumb))
    return ('', 204)


@app.route("/subscribe/<email>", methods=['DELETE'])
def removeSubscribe(email):
    if not busService.hasSubscriber(email):
        return {"Msg": "找不到訂閱者"}, 404
    busService.removeSubscriber(email)
    return ('', 204)


try:
    app.run(host="0.0.0.0")
except Exception as e:
    print("error: {}".format(e))
busService.close2()
