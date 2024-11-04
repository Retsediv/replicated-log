# Replicated Log

## How to run the code

```bash
# build
docker compose build

# run (change .env file with the number of clients you want to run)
source .env
for i in $(seq 1 $NUM_CLIENTS); do CLIENT_INDEX=$i docker compose up --scale client=$i --no-recreate -d; done

# get hostnames
for i in $(docker ps --format  '{{ .Names }}'); do
echo -n "$i: "; docker inspect --type container $i | jq -r '.[].Config.Hostname'
done
```

## API

Note: Substitute 6000 port with the port of the master/client you want to interact with.

1. Submit a new message with the write concern (1 by default)

   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"message": "Hello World", "write_concern": 1}' http://localhost:6000/messages
   ```

2. Get the log (from the master or any client)
   ```bash
   curl localhost:6000/messages
   ```
