# Feedback notification adapter: agent guide

Read the [service instructions](../../../AGENTS.md), [maintenance guide](../../../docs/TECHNICAL_DOCUMENTATION.md) and send_email.py before editing. This module publishes to RabbitMQ; it does not itself deliver mail to a recipient.

Broker credentials come from RABBITMQ_URL. MS_AUTH_USER/MS_AUTH_PASSWORD are separate downstream auth fields embedded in the JSON envelope. Preserve the pattern=send, data.auth/data.data shape, queue routing and message DTO unless coordinating a contract change with the consumer. Do not print those credentials or full payloads.

Negative-feedback notifications are best effort after DynamoDB persistence. The outer service ignores the boolean result and logs can imply success on failure; changing retry/rollback/delivery behavior is a feature change, not a docs correction. Templates can include identity, comments, context and full AI output.

For offline validation replace pika connection/channel/properties before calling, use fictional data and prevent network. Check durable queue declaration, default exchange, routing key, delivery_mode 2 and JSON structure without queueing a real message. Fake publish success cannot validate broker confirms, downstream authentication or final delivery. Do not contact recipients or send messages unless explicitly authorized.
