# CoinExchange-Flask

## 撮合交易引擎
### 接受订单
撮合引擎受限需要接受来自市场参与者的买卖订单，这些订单包含了价格、数量、订单类型（如市价单、限价单等）、订单ID、订单状态、订单时间戳等信息。
### 订单验证
接收到订单后，撮合引擎需要验证订单的有效性，包括检查订单的格式是否正确、订单价格是否合理、订单数量是否合理、确保账户余额足够、验证订单的合法性等。
### 订单簿管理
有效的订单将被添加到撮合引擎的订单簿中，撮合引擎会根据订单的价格和数量进行撮合，生成成交记录。订单簿按照价格优先级和时间优先级来排序订单。买单按照价格从高到低排序，卖单从低到高排序。
### 撮合过程
撮合引擎遍历订单簿中的订单，按照价格优先级和数量优先级进行撮合。撮合引擎会根据订单的价格和数量，如果找到匹配的订单（即买单价格等于或高于卖单价格），则执行交易
### 执行交易
一旦订单被匹配，撮合引擎会执行交易，生成成交记录，并更新订单簿中的订单状态。这涉及到更新订单的状态，记录交易详情，以及更新双方的账户余额。
### 处理部分成交
有些订单可能无法一次性成交，需要处理部分成交的情况。撮合引擎需要记录订单的剩余数量和成交数量，直到找到新的匹配订单或被撤销。
### 订单撤销和修改
撮合引擎需要处理订单的撤销和修改。订单的撤销需要将订单从订单簿中移除，修改需要更新订单的价格、数量等。
### 数据广播
撮合引擎需要将撮合结果广播给所有客户端，包括撮合引擎本身、交易撮合服务、行情服务、用户信息服务等。
## 法币交易服务

## 行情服务

## 用户信息服务

## 钱包服务
