from requests import request, post
import json
from someTool import getSetting


class TdxApi():

    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key
        auth_header = {
            'content-type': 'application/x-www-form-urlencoded',
            'grant_type': 'client_credentials',
            'client_id': self.app_id,
            'client_secret': self.app_key
        }
        self.auth_token = json.loads(post(
            "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token", auth_header).text)

    def get_auth_header(self):
        return {
            'Authorization': 'Bearer '+self.auth_token["access_token"],
            'Accept-Encoding': 'gzip'
        }

    def getApi(self, url):
        response = request('get', url, headers=self.get_auth_header())
        # print(response)
        return json.loads(response.content.decode("utf8"))


if __name__ == "__main__":
    setting = getSetting()
    app_id = setting['ptxAppId']
    app_key = setting['ptxAppKey']
    api = TdxApi(app_id, app_key)
    api.getApi(
        'https://tdx.transportdata.tw/api/basic/v2/Bus/RealTimeByFrequency/City/Taipei?$format=JSON')
