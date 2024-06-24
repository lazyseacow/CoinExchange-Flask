# CoinExchange-Flask

### 注意
- **安装依赖说明**  
    `flask_script==2.0.6`与`Flask==3.0.3`存在不兼容问题，需要修改相关配置  
- 修改方式
1. ModuleNotFoundError: No module named 'flask._compat'  
解决方案：`flask_script/__init__.py`文件 15行 `from flask._compat import text_type` 书写有误。修改为`from flask_script._compat import text_type`
2. ImportError: cannot import name '_request_ctx_stack' from 'flask' (D:\pyproject\CoinExchange-Flask\venv\Lib\site-packages\flask\__init__.py)  
解决方案：将`flask_script/commands.py`文件 13行 `from flask import _request_ctx_stack` 书写有误。将其注释即可

### flask运行命令
* 数据库初始化:  
`python manage.py db init`
* 数据库迁移:  
`python manage.py db migrate`
* 数据库更新:  
`python manage.py db upgrade`
* 运行:  
`python manage.py runserver -h 192.168.1.10 -p 5000`

### Celery
* 启动:  
`celery -A app.tasks.task worker --loglevel=info --concurrency=10 --pool=eventlet`
* 执行:  
`python task.py`

### websocket
* 启动:  
`python wss_redis.py`