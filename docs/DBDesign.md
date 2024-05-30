## 不具备自动化撮合交易的数字货币交易系统开发设计
## 1. 模块设计
### 用户信息服务
- 用户基本信息表（user）：用于存储用户基本信息，包括用户名、密码、邮箱、手机号码等。
- 
| 字段名       | 类型           | 说明         |
|-----------|--------------|------------|
| user_id   | int(11)      | 用户ID，主键，自增 |
| username  | varchar(255) | 用户名，唯一索引   |
| password  | varchar(255) | 密码，加密存储    |
| email     | varchar(255) | 邮箱，唯一索引    |
| phone     | varchar(255) | 手机号码，唯一索引  |
| join_date | datetime     | 注册日期       |
| last_seen | datetime     | 最后登录时间     |

- 用户身份验证表（user_authentication）：用来存储用户的登录方法和相关的的安全设置

| 字段名       | 类型           | 说明                   |
|-----------|--------------|----------------------|
| auth_id   | int(11)      | 主键，自增                |
| user_id   | int(11)      | 外键，关联user表           |
| auth_type | varchar(255) | 登录方式，如：邮箱、手机号、第三方登录等 |
| auth_key  | varchar(255) | 用于生成一次性密码或其他认证数据的密钥  |
| enabled   | tinyint(1)   | 指示是否启用该认证方法          |

- 用户安全设置表（user_security_settings）：用于存储用户的安全相关设置，比如IP白名单、交易限额

| 字段名           | 类型                                        | 说明                  |
|---------------|-------------------------------------------|---------------------|
| setting_id    | int(11)                                   | 主键，自增               |
| user_id       | int(11)                                   | 外键，关联user表          |
| setting_type  | enum('IP_whitelist', 'transaction_limit') | 设置类型，如：IP白名单、交易限额等  |
| setting_value | varchar(255)                              | 设置值，如：IP白名单列表、交易限额等 |

- 用户活动日志表（user_activity_logs）：用于记录用户的关键活动和交易，有助于审计和安全监控

| 字段名              | 类型           | 说明                |
|------------------|--------------|-------------------|
| log_id           | int(11)      | 主键，自增             |
| user_id          | int(11)      | 外键，关联user表        |
| activity_type    | varchar(255) | 活动类型，如：登录、交易等     |
| activity_details | varchar(255) | 活动描述，如：登录IP、交易金额等 |
| activity_time    | datetime     | 活动时间戳             |

- 用户API密钥表（api_keys）：对接第三方API的密钥管理

| 字段名        | 类型           | 说明          |
|------------|--------------|-------------|
| key_id     | int(11)      | 主键，自增       |
| user_id    | int(11)      | 外键，关联user表  |
| api_key    | varchar(255) | API密钥，加密存储  |
| api_secret | varchar(255) | 密钥的密文，加密存储  |
| permission | varchar(255) | 权限，如：读写、只读等 |
| created_at | datetime     | 创建时间        |

### 钱包服务
- 用户钱包表（wallets）：管理用户的加密货币余额与交易，可能需要多个钱包表

| 字段名            | 类型            | 说明                              |
|----------------|---------------|---------------------------------|
| wallet_id      | int(11)       | 主键，自增                           |
| user_id        | int(11)       | 外键，关联user表                      |
| currency       | varchar(255)  | 币种，如：BTC、ETH、USDT等              |
| balance        | decimal(18,8) | 用户在该币种下的余额，精确到小数点后8位            |
| frozen_balance | decimal(18,8) | 交易过程中锁定的金额（未完成的交易或提款），精确到小数点后8位 |

- 钱包操作日志表（wallet_operations）：记录钱包的所有操作活动，如充值、提款等

| 字段名            | 类型            | 说明             |
|----------------|---------------|----------------|
| operation_id   | int(11)       | 主键，自增          |
| wallet_id      | int(11)       | 外键，关联wallets表  |
| operation_type | varchar(255)  | 操作类型，如：充值、提款等  |
| amount         | decimal(18,8) | 操作金额，精确到小数点后8位 |
| status         | varchar(255)  | 操作状态，如：成功、失败等  |
| operation_time | datetime      | 操作时间戳          |

- 钱包事件日志表（wallet_event_logs）：用户记录与钱包相关的所有重要安全事件，如登陆尝试、非法操作尝试、重要设置修改等

| 字段名           | 类型           | 说明                             |
|---------------|--------------|--------------------------------|
| event_id      | int(11)      | 主键，自增                          |
| wallet_id     | int(11)      | 外键，关联wallets表                  |
| event_type    | varchar(255) | 事件类型，如：登陆尝试、非法操作尝试等            |
| description   | varchar(255) | 事件描述，如：登陆IP、操作金额等              |
| event_time    | datetime     | 事件时间戳                          |
| ip_address    | varchar(255) | 事件发生时的IP地址，用于审计和防止恶意行为         |
| user_agent    | varchar(255) | 事件发生时的User-Agent信息，用于审计和防止恶意行为 |
| is_suspicious | tinyint(1)   | 是否为可疑事件，如：IP地址不在白名单内、操作金额超过限制等 |

- 安全策列表（security_policies）：用户定义和管理钱包的安全策略，如每日提款限额、交易确认等

| 字段名            | 类型                                                         | 说明                              |
|----------------|------------------------------------------------------------|---------------------------------|
| policy_id      | int(11)                                                    | 主键，自增                           |
| wallet_id      | int(11)                                                    | 外键，关联wallets表                   |
| policy_type    | enum('daily_withdrawal_limit', 'transaction_confirmation') | 策略类型，如：每日提款限额、交易确认等             |
| policy_details | varchar(255)                                               | 策略内容，如：每日提款限额为1000元，交易确认方式为人工审核 |
| enabled        | tinyint(1)                                                 | 指示是否启用该策略                       |
| created_at     | datetime                                                   | 创建时间                            |

### 法币交易服务、撮合引擎交易
- 充值与提现记录表（deposits_withdrawals）：管理用户的法币和数字货币的存款和提款操作

| 字段名              | 类型                                   | 说明               |
|------------------|--------------------------------------|------------------|
| record_id        | int(11)                              | 主键，自增            |
| user_id          | int(11)                              | 外键，关联user表       |
| transaction_type | enum('deposit','withdrawal')         | 充值或提现类型，如：充值、提现  |
| currency         | varchar(255)                         | 币种，如：CNY、USD等    |
| amount           | decimal(18,8)                        | 金额，精确到小数点后8位     |
| status           | enum('pending','completed','failed') | 状态，如：待处理、已完成、失败  |
| transaction_id   | varchar(255)                         | 交易ID，用于关联第三方支付平台 |
| created_at       | datetime                             | 创建时间             |
| updated_at       | datetime                             | 更新时间             |

- 订单表（orders）：用于存储用户提交的买卖订单交易

| 字段名        | 类型                                | 说明                     |
|------------|-----------------------------------|------------------------|
| order_id   | int(11)                           | 主键，自增                  |
| user_id    | int(11)                           | 外键，关联user表             |
| order_type | enum('buy','sell')                | 订单类型，如：买入、卖出           |
| symbol     | varchar(255)                      | 交易对，如：BTC/CNY、ETH/USD等 |
| status     | enum('open','filled','cancelled') | 订单状态，如：打开、已填充、已取消      |
| price      | decimal(18,8)                     | 订单价格，精确到小数点后8位         |
| quantity   | decimal(18,8)                     | 订单数量，精确到小数点后8位         |
| created_at | datetime                          | 订单创建时间                 |
| updated_at | datetime                          | 订单更新时间                 |

- 交易记录表（transactions）：记录所有完成的交易，包括买卖双方的订单匹配结果

| 字段名             | 类型            | 说明             |
|-----------------|---------------|----------------|
| transaction_id  | int(11)       | 主键，自增          |
| buyer_order_id  | int(11)       | 外键，关联orders表   |
| seller_order_id | int(11)       | 外键，关联orders表   |
| amount          | decimal(18,8) | 交易金额，精确到小数点后8位 |
| price           | decimal(18,8) | 交易价格，精确到小数点后8位 |
| create_at       | datetime      | 交易时间戳          |
### 行情服务

## 2.用户管理：管理不同级别用户的访问权限
- 角色表（roles）：管理不同级别用户的访问权限

| 字段名         | 类型           | 说明             |
|-------------|--------------|----------------|
| role_id     | int(11)      | 主键，自增          |
| role_name   | varchar(255) | 角色名称           |
| permissions | text         | 角色权限，以JSON格式存储 |

- 用户角色关联表（uesr_roles）

| 字段名          | 类型      | 说明          |
|--------------|---------|-------------|
| user_role_id | int(11) | 主键，自增       |
| user_id      | int(11) | 外键，关联user表  |
| role_id      | int(11) | 外键，关联roles表 |

- 审计与合规表（compliance）：用于管理和跟踪合规性审核，特别是处理大额交易和敏感操作时

| 字段名          | 类型                                                      | 说明                   |
|--------------|---------------------------------------------------------|----------------------|
| audit_id     | int(11)                                                 | 主键，自增                |
| user_id      | int(11)                                                 | 外键，关联user表           |
| audit_type   | emum('large_transaction_review','account_verification') | 审核类型，如：大额交易审核、账户验证审核 |
| audit_status | enum('pending','approved','rejected                     | 审核状态，如：待审核、通过、拒绝     |
| details      | text                                                    | 审核详情，以JSON格式存储       |
| created_at   | datetime                                                | 审核创建时间               |
