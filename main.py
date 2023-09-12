import hashlib
import json
import os.path
from datetime import datetime
from typing import Callable
from urllib import parse

import requests
from fastapi import FastAPI
from fastapi import Form
from fastapi.encoders import jsonable_encoder
from pytz import timezone
from starlette.responses import HTMLResponse, JSONResponse

app = FastAPI()

'''
[테스트 계정 정보]
테스트 MID : INIpayTest
용도 : 일반결제
signkey    : SU5JTElURV9UUklQTEVERVNfS0VZU1RS
INIAPI key : ItEQKi3rY7uvDS8l
INIAPI iv   : HYb3yQ4f65QL89==
모바일 hashkey : 3CB8183A4BE283555ACC8363C0360223
'''
signkey = "SU5JTElURV9UUklQTEVERVNfS0VZU1RS"
INIAPIKey= "ItEQKi3rY7uvDS8l"

current_milli_time: Callable[[], int] = lambda: int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)
sha256_hash: Callable[[str], str] = lambda data: hashlib.sha256(data.encode()).hexdigest()
sha512_hash: Callable[[str], str] = lambda data: hashlib.sha512(data.encode()).hexdigest()

@app.get("/")
async def root():
    with open(os.path.join(os.path.dirname(__file__), "root.html"), 'r', encoding='UTF8') as f:
        html = f.read()
    return HTMLResponse(content=html, status_code=200)


@app.post("/pay")
async def _(price: str = Form(...),
            goodname: str = Form(...),
            buyername: str = Form(...),
            buyertel: str = Form(...),
            buyeremail: str = Form(...)):
    with open(os.path.join(os.path.dirname(__file__), "pay.html"), 'r', encoding='UTF8') as f:
        html = (f.read()
                .replace("priceInput", price)
                .replace("goodnameInput", goodname)
                .replace("buyernameInput", buyername)
                .replace("buyertelInput", buyertel)
                .replace("buyeremailInput", buyeremail))
    return HTMLResponse(content=html, status_code=200)


@app.post(path="/return")
async def _(resultCode: str = Form(None),
            resultMsg: str = Form(None),
            mid: str = Form(None),
            orderNumber: str = Form(None),
            authToken: str = Form(None),
            idc_name: str = Form(None),
            authUrl: str = Form(None),
            netCancelUrl: str = Form(None),
            charset: str = Form(None),
            merchantData: str = Form(None), ):
    if resultCode != "0000":
        return JSONResponse(status_code=200, content=jsonable_encoder(dict(인증결과="실패")))
    timestamp = current_milli_time()

    response = requests.post(
        url=authUrl,
        headers={"Content-type": "application/x-www-form-urlencoded", "charset": "utf-8"},
        data=dict(
            mid=mid,
            authToken=authToken,
            timestamp=timestamp,
            signature=sha256_hash(f"authToken={authToken}&timestamp={timestamp}"),
            verification=sha256_hash(f"authToken={authToken}&signKey={signkey}&timestamp={timestamp}"),
            charset="UTF-8",
            format="JSON",
        )
    )
    confirm_data = json.loads(response.text)

    data = dict(
        auth_resultCode=resultCode,
        auth_resultMsg=resultMsg,
        auth_mid=mid,
        auth_orderNumber=orderNumber,
        auth_authToken=authToken,
        auth_idc_name=idc_name,
        auth_authUrl=authUrl,
        auth_netCancelUrl=netCancelUrl,
        auth_charset=charset,
        auth_merchantData=merchantData,

        confirm_resultCode=confirm_data.get("resultCode"),
        confirm_resultMsg=confirm_data.get("resultMsg"),
        confirm_tid=confirm_data.get("tid"),
        confirm_mid=confirm_data.get("mid"),
        confirm_MOID=confirm_data.get("MOID"),
        confirm_TotPrice=confirm_data.get("TotPrice"),
        confirm_goodName=confirm_data.get("goodName"),
        confirm_payMethod=confirm_data.get("payMethod"),
        confirm_applDate=confirm_data.get("applDate"),
        confirm_applTime=confirm_data.get("applTime"),
        confirm_EventCode=confirm_data.get("EventCode"),
        confirm_buyerName=confirm_data.get("buyerName"),
        confirm_buyerTel=confirm_data.get("buyerTel"),
        confirm_buyerEmail=confirm_data.get("buyerEmail"),
        confirm_custEmail=confirm_data.get("custEmail"),
    )
    with open(os.path.join(os.path.dirname(__file__), "return.html"), 'r', encoding='UTF8') as f:
        html = f.read().format(**data)
    return HTMLResponse(content=html, status_code=200)


@app.get(path="/close")
async def _():
    return JSONResponse(status_code=200, content=jsonable_encoder(dict(msg="결제 중단")))


@app.post(path="/net-cancel")
async def _(netCancelUrl: str = Form(...),
            mid: str = Form(...),
            authToken: str = Form(...), ):
    timestamp = current_milli_time()
    response = requests.post(
        url=netCancelUrl,
        headers={"Content-type": "application/x-www-form-urlencoded", "charset": "utf-8"},
        data=dict(
            mid=mid,
            authToken=authToken,
            timestamp=timestamp,
            signature=sha256_hash(f"authToken={authToken}&timestamp={timestamp}"),
            verification=sha256_hash(f"authToken={authToken}&signKey={signkey}&timestamp={timestamp}"),
            charset="UTF-8",
            format="JSON",
        )
    )
    net_cancel_data = json.loads(response.text)
    return JSONResponse(status_code=200, content=jsonable_encoder(net_cancel_data))


@app.post(path="/all-cancel")
async def _(mid: str = Form(...),
            tid: str = Form(...),
            msg: str = Form(...),):
    type = "Refund"
    paymethod = "Card"
    timestamp = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d%H%M%S")
    clientIp = "127.0.0.1:8000"
    data = dict(
        type=type,
        paymethod=paymethod,
        timestamp=timestamp,
        clientIp=clientIp,
        mid=mid,
        tid=tid,
        msg=msg,
        hashData=sha512_hash(f"{INIAPIKey}{type}{paymethod}{timestamp}{clientIp}{mid}{tid}")
    )
    encoded_data = parse.urlencode(data)
    response = requests.post(
        url="https://iniapi.inicis.com/api/v1/refund",
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
        data=encoded_data,
    )
    net_cancel_data = json.loads(response.text)
    return JSONResponse(status_code=200, content=jsonable_encoder(net_cancel_data))