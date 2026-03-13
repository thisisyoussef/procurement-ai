# Kafka Tutorial — Producer & Consumer Examples in Java

Hands-on Apache Kafka examples demonstrating producer patterns (basic sends, async callbacks, key-based partitioning) and consumer patterns (polling, consumer groups) using the official Kafka Java client.

![Java](https://img.shields.io/badge/Java-ED8B00?logo=openjdk&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?logo=apachekafka&logoColor=white)

## What's Covered

- **ProducerDemo** — Basic message sending with bootstrap server config, string serializers, and flush/close lifecycle
- **ProducerDemoWithCallback** — Async producer with callback handlers for delivery confirmation, error handling, and metadata inspection (partition, offset, timestamp)
- **ProducerDemoKeys** — Key-based message partitioning ensuring messages with the same key always land on the same partition
- **ConsumerDemo** — Basic consumer with polling loop, deserialization config, and group management

## Running

Requires a running Kafka cluster (local or Docker).

```bash
# Build
mvn clean package

# Run producer examples
java -cp target/*.jar io.demos.kafka.ProducerDemo
java -cp target/*.jar io.demos.kafka.ProducerDemoWithCallback
java -cp target/*.jar io.demos.kafka.ProducerDemoKeys

# Run consumer
java -cp target/*.jar io.demos.kafka.ConsumerDemo
```

## Tech Stack

Java, Apache Kafka Clients, Maven
