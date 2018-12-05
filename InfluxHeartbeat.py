from influxdb import InfluxDBClient
import datetime

class InfluxHeartbeat:
    def __init__(self, config, service_name):

        self.db_name = config['INFLUXDB_SERVICE']['db_name']

        pi = config['INFLUXDB_SERVICE']['pi']

        ip = config['PI_ADDRESSES'][str(config['DEFAULT']['cluster_id'])
                                    + str(pi)]

        # todo implement ssl?
        self.influx_client = InfluxDBClient(
            ip,
            config['INFLUXDB_SERVICE']['port'],
            config['INFLUXDB_SERVICE']['user'],
            config['INFLUXDB_SERVICE']['pass'],
            self.db_name
        )

        self.influx_client.create_database(self.db_name)

        self.service_name = service_name

    def heartbeat_pulse(self):

        cur_time = datetime.datetime.now()

        json_body = [
            {
                "measurement": self.service_name + '_heartbeat',
                "time": cur_time,
                "fields": {
                    "value": 1
                }
            }

        ]

        self.influx_client.write_points(json_body)