# Jaeger Tracing — Distributed Tracing for Microservices

A setup for distributed tracing using Jaeger and OpenTelemetry, demonstrating how to instrument Node.js services for observability across microservice boundaries.

![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)
![Jaeger](https://img.shields.io/badge/Jaeger-66CFE3?logoColor=white)

## What This Does

Instruments Node.js services with Jaeger tracing to visualize request flows across service boundaries. Traces capture timing, dependencies, and error propagation across distributed systems.

## Tech Stack

JavaScript, Node.js, Jaeger, OpenTelemetry

## Running

```bash
npm install
# Start Jaeger (Docker)
docker run -d -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one
# Run instrumented service
npm start
# View traces at http://localhost:16686
```
