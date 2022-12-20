# INeed672

資料來源: [TDX](https://tdx.transportdata.tw/)

Python版本: 3.11

本專案只針對台北市區公車，並且排除了資料錯誤的路線

data/ErrorRouteShap.json
路線的線型有錯，例如包含多段的線 MULTILINESTRING，公車會穿越蟲洞

data/ErrorRouteNoShap.json
路線缺少線型資料

data/errorStopIdxOfRoute.json
站牌距離最近的線型的點如果有偏移並且導致站序錯誤的話，會被記錄到這

data/noErrorCityStopOfRoute.json
完整資料，包含 Shap、Stop、Stop.PointOfRoute

data/noErrorCityStopOfRoute2.json
完整資料，包含 Shap、Stop、Stop.PointOfRoute、Stop.nextStopDis

Stop.PointOfRoute: 紀錄站到線型的索引、座標

Stop.nextStopDis: 紀錄站到下一站的距離(公尺)，使用線型計算，非直線距離

## 執行

```
python ./Main.py
```

### 取得旅行時間

```bash
# routeName: 路線名稱(中文)
# dir: 0去程 1返程
GET http://localhost:5000/getTravelTime/{routeName}/{dir}

# 範例: 672去程的旅行時間
http://localhost:5000/getTravelTime/672/0
```

### 訂閱提醒，前 5 站會發出提醒，或是前 5 分鐘提醒

當訂閱包含車牌時，提醒過後不會再提醒!

```bash
# routeName: 路線名稱(中文)
# dir: 0去程 1返程
# stopName: 站牌名稱(中文)
# email: 信箱
# busPlateNumb: 公車車牌(可選)
GET http://localhost:5000/subscribe/{routeName}/{dir}/{stopName}/{email}/{busPlateNumb}

# 範例: 672去程的公車車牌"735-U3"到站牌"生社區活動中心"前5站提醒、或是前5分鐘提醒，會寄信到test@gmail.com
http://localhost:5000/subscribe/672/0/福和橋(永元路)/test@gmail.com/735-U3
```

### 取消訂閱

```bash
# email: 要取消訂閱的email
DELETE http://localhost:5000/subscribe/{email}

# 範例: test@gmail.com使用者取消訂閱
http://localhost:5000/subscribe/test@gmail.com
```
