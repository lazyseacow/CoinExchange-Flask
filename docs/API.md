# CoinExchange-Flask API Statements

* [状态码说明](#状态码说明)
* [Base Url](#Base-Url)
* [注册](#注册)
* [登陆](#登录)
* [Token认证](#Token认证)
* [退出登录](#退出登录-需要授权)
* [修改密码](#修改密码-需要授权)
* [重置密码](#重置密码-需要授权)

--------------------------------------
## 状态码说明
| re_code |     msg     |
|:-------:|:-----------:|
|    0    |     成功      |
|  4001   |   数据库查询错误   |
|  4002   |    数据已存在    |
|  4003   |     无数据     |
|  4004   |    数据错误     |
|  4101   |    用户未登录    |
|  4102   |   用户登陆失败    |
|  4103   |    参数错误     |
|  4104   |  用户不存在或未激活  |
|  4105   |   用户身份错误    |
|  4106   |    密码错误     |
|  4201   | 非法请求或请求次数受限 |
|  4202   |    IP受限     |
|  4301   |   第三方系统错误   |
|  4302   |   文件读写错误    |
|  4500   |    内部错误     |
|  4501   |    未知错误     |
--------------------------------------
## Base Url
```
http://192.168.1.10:5000
```
--------------------------------------
## 注册
- ### 接口功能
    账号注册
- ## 请求方式
```
POST /register
```
- ### 请求参数
|    参数    | 参数说明 |   类型   | 是否必须 |
|:--------:|:----:|:------:|:----:|
| username | 用户名  | string |  是   |
|  email   |  邮箱  | string |  是   |
|  phone   | 手机号  | string |  是   |
| password |  密码  | string |  是   |

- ### 请求示例
```
{
    "username": "YourName",
    "email": "YourEmail@gmail.com",
    "phone": 12345678910,
    "password": "123456"
}
```
- ### 响应参数
|   参数    | 参数说明 |   类型   | 是否必须 |
|:-------:|:----:|:------:|:----:|
| re_code | 状态码  |  int   |  是   |
|   msg   | 状态信息 | string |  是   |
- ### 响应示例
```
{
    "errmsg": "手机号已注册",
    "re_code": 4003
}
```
--------------------------------------
## 登录
- ### 接口功能
    账户登录
- ## 请求方式
```
POST /login
```
- ### 请求参数
|    参数    | 参数说明 |   类型   | 是否必须 |
|:--------:|:----:|:------:|:----:|
|  phone   | 手机号  | string |  是   |
| password |  密码  | string |  是   |
- ### 请求示例
```
{
	"phone": 13437540086,
	"password": "123456"
}
```
- ### 响应参数
|      参数       | 参数说明  |   类型   | 是否必须 |                说明                 |
|:-------------:|:-----:|:------:|:----:|:---------------------------------:|
|    re_code    |  状态码  |  int   |  是   |                 无                 |
|      msg      | 状态信息  | string |  是   |                 无                 |
| access_token  | token | string |  是   |             登录成功自动生成              |
| refresh_token | token | string |  是   | 当access_token失效时，用于刷新access_token |
- ### 响应示例
```
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6dHJ1ZSwiaWF0IjoxNzE2MzQxNjk2LCJqdGkiOiJlMzE3ZDg3NC1iODVhLTQ3OTItYWVhZC02NjI4ODE3OGFiMzkiLCJ0eXBlIjoiYWNjZXNzIiwic3ViIjoiMTM0Mzc1NDAwODYiLCJuYmYiOjE3MTYzNDE2OTYsImNzcmYiOiI5NTEzZDZkYi0yZGU2LTQ2NGQtYjg4NS1hOGFmY2U0MWYzOTEiLCJleHAiOjE3MTYzNDE3MDZ9.7t9PMXuAld7XjGWPvu12JVzdRNSBu85CMuTQb11NqZA",
    "errmsg": "登录成功",
    "re_code": 0,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxNjM0MTY5NiwianRpIjoiNTI2ZDY1NjctOGMxMi00MDNlLTg1MmQtMmE1Y2RiZGMzODUyIiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiIxMzQzNzU0MDA4NiIsIm5iZiI6MTcxNjM0MTY5NiwiY3NyZiI6ImFjODhjOTU5LWFjYzMtNGZhOS1hNTA0LTRiMWFhNjA2ZTAxZiIsImV4cCI6MTcxODkzMzY5Nn0.5UQeYOi33KxsK3sAzs94osSVKG5WBJlObPvN03wsf-s"
}
```
- ### 详细说明
  用户登录成功生成access_token，当access_token失效时，通过refresh_token刷新access_token。

--------------------------------------
## Token认证
- ### 接口功能
    刷新access_token
- ### 请求方式
```
POST /token/refresh
```
- ### 请求头
```
Authorization: Bearer <refresh_token>
```
- ### 响应参数
|     参数      |  参数说明   |   类型   | 是否必须 | 说明 |
|:-----------:|:-------:|:------:|:----:|:--:|
|   re_code   |   状态码   |  int   |  是   | 无  |
|     msg     |  状态信息   | string |  是   | 无  |
| access_code | 访问token | string |  是   | 无  |
- ### 响应示例
```
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxNjc5MDQ5OSwianRpIjoiM2NiOWViODktNWYwYS00MjQxLThmMTgtOWY5MDFhMmRmOTA3IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjEzNDM3NTQwMDg2IiwibmJmIjoxNzE2NzkwNDk5LCJjc3JmIjoiNDM1YmZmYmItMDhkZS00ZDAwLTgwNTktODM4NjdlNzQ3MTAxIiwiZXhwIjoxNzE2NzkxMzk5fQ.6IQnXQvAwyXLnpIjb57hxGcmPE_r4R2vwqYJglwU0mM",
    "re_code": 0,
    "msg": "刷新成功"
}
```
--------------------------------------
## 退出登录-需要授权
- ### 接口功能
    退出登录
- ## 请求方式
```
  POST /logout
```
- ### 请求头
```
Authorization: Bearer <access_token>
```
- ### 响应参数
|   参数    | 参数说明 |   类型   | 是否必须 |
|:-------:|:----:|:------:|:----:|
| re_code | 状态码  |  int   |  是   |
|   msg   | 状态信息 | string |  是   |
- ### 响应示例
```
{
    "msg": "退出成功",
    re_code: "0"
}
```
--------------------------------------
## 修改密码-需要授权
- ### 接口功能
  修改密码（需提供原密码）
- ## 请求方式
```
POST /modifypassword
```
- ### 请求头
```
Authorization: Bearer <access_token>
```
- ### 请求参数
|        参数        | 参数说明 |   类型   | 是否必须 |
|:----------------:|:----:|:------:|:----:|
| current_password | 原密码  | string |  是   |
|   new_password   | 新密码  | string |  是   |
- ### 请求示例
```
{
    "current_password": "123456",
    "new_password": "12345"
}
```
- ### 响应参数
|   参数    | 参数说明 |   类型   | 是否必须 | 说明 |
|:-------:|:----:|:------:|:----:|:--:|
| re_code | 状态码  |  int   |  是   | 无  |
|   msg   | 状态信息 | string |  是   | 无  |
- ### 响应示例
```
{
    "msg": "密码修改成功",
    "re_code": 0
}
```
--------------------------------------
## 重置密码-需要授权
- ### 接口功能
  重置密码
- ## 请求方式
```
POST /resetpassword
```
- ### 请求头
```
Authorization: Bearer <access_token>
```
- ### 请求参数
|      参数      | 参数说明 |   类型   | 是否必须 |
|:------------:|:----:|:------:|:----:|
| new_password | 新密码  | string |  是   |

- ### 请求示例
```
{
    "new_password": "12345"
}
```

- ### 响应参数
|   参数    | 参数说明 |   类型   | 是否必须 | 说明 |
|:-------:|:----:|:------:|:----:|:--:|
| re_code | 状态码  |  int   |  是   | 无  |
|   msg   | 状态信息 | string |  是   | 无  |

- ### 响应示例
```
{
    "msg": "密码修改成功",
    "re_code": 0
}
```
--------------------------------------
## 获取历史klines-需要授权
- ### 接口功能
  从币安获取历史k线数据
- ### 请求方式
```
GET /klines
```
- ### 请求参数
|    参数     |   类型   | 是否必须 |            参数说明             |
|:---------:|:------:|:----:|:---------------------------:|
|  symbol   | string |  是   |             币对              | 
| interval  | string |  是   |            k线间隔             |
|   limit   |  int   |  否   |      数量（默认500，最大1000）       |
| startTime |  int   |  否   | 开始时间（默认当前时间90天前的毫秒级unix时间戳） |
|  endTime  |  int   |  否   |    结束时间（默认当前毫秒级unix时间戳）     |
| timeZone  | string |  否   |        时区（默认0：UTC，1）        |

- ### 响应参数
|   参数    |  类型   | 是否必须 | 参数说明 |
|:-------:|:-----:|:----:|:----:|
| re_code |  int  |  是   | 状态码  |
|  data   | array |  是   | k线数据 |
- ### 响应示例
```
{
    "data": [
        [
            1711324800000,          // 开盘时间
            "67210.00000000",       // 开盘价
            "71769.54000000",       // 最高价
            "66385.06000000",       // 最低价
            "71280.01000000",       // 收盘价（当前K线未结束的即为新价）
            "235409.95755000",      // 成交量
            1711929599999,          // K线收盘时间
            "16447219313.36233680", // 成交额
            12877311,               // 成交笔数
            "118629.51433000",      // 主动买入成交量
            "8288128238.68617310",  // 主动买入成交额
            "0"                     // 忽略
        ]
        ···
    ],
    "re_code": 0
}
```
