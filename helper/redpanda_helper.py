from confluent_kafka import Producer
import msgpack


producer_config = {
    "bootstrap.servers": "localhost:9092",  
}
producer = Producer(producer_config)

def send_user_summary(topic, data):
    """
    Mengirimkan data summary ke Redpanda dengan MessagePack.
    """
    try:
        packed_data = msgpack.packb(data)
        print(f"Serialized data (packed_data): {packed_data}")
        
        producer.produce(topic, packed_data)
        producer.flush()
        print(f"Data sent to topic {topic}: {data}")
    except Exception as e:
        raise Exception(f"Error sending data to Redpanda: {str(e)}")

