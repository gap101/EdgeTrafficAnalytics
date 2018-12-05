from influxdb import InfluxDBClient

client = InfluxDBClient('localhost', 8086, 'root', 'root', 'gulchtest')

client.create_database('gulchtest')

# client.delete_series(database='gulchtest', measurement='vehicles')
# client.delete_series(database='gulchtest', measurement='cam_device_service')
client.drop_database('gulchtest')

client.create_database('gulchtest')
