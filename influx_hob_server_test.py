from influxdb import InfluxDBClient
import datetime
import time


    

db_name = 'gulch'

influx_client = InfluxDBClient(
    '10.190.15.157',
    '8086',
    'gulch',
    'MetroProject615',
    db_name,
    ssl=True
)

#influx_client.create_database(db_name)

service_name = 'test'

def heartbeat_pulse():

    cur_time = datetime.datetime.now()

    json_body = [
        {
            "measurement": service_name + '_heartbeat',
            "time": cur_time,
            "fields": {
                "value": 1
            }
        }

    ]

    influx_client.write_points(json_body)

while True:

    heartbeat_pulse()

    result = influx_client.query('select value from test_heartbeat;')

    print(result)

    time.sleep(3)
