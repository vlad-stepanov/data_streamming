# Create news topic
docker exec -it kafka kafka-topics.sh --create --topic news --bootstrap-server kafka:9092 --partitions 3 --replication-factor 1

docker exec -it kafka kafka-topics.sh --list --bootstrap-server kafka:9092

# Check PostgreSQL is up
docker exec -it postgres psql -U news_user -d news_db
