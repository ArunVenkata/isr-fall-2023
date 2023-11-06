# isr-fall-2023



Steps to Set up Backend:
- Python 3 Required
- Install [redis-server](https://redis.io/docs/install/install-redis/)
- Run `cd isr_project_be`
- Create a Virtual Environment using `virtualenv` in python
- Activate Virtual Envrionment
- Run `pip install -r requirements.txt`
- To Start Flask, Run `flask run`
- To Start Celery, open a new terminal and move to parent folder of 'isr_project_be' then run `celery -A isr_project_be.app.celery_app worker --loglevel INFO`
- To start Redis Server, open a new terminal and run `redis-server`

